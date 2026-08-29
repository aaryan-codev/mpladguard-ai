import { useEffect, useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';
import api, { ApiError } from '../services/api';
import { LoadingBlock, ErrorBanner } from '../components/StateBlocks';
import { RiskBadge } from '../components/Badges';

const RISK_COLOR = { LOW: '#16a34a', MEDIUM: '#f59e0b', HIGH: '#ef4444' };
const MAX_MARKERS = 150; // keep the demo responsive -- narrow with the state filter for more

export default function MapPage() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [riskById, setRiskById] = useState({});
  const [loading, setLoading] = useState(true);
  const [warmingRisk, setWarmingRisk] = useState(true);
  const [error, setError] = useState('');
  const [stateFilter, setStateFilter] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.listProjects({ limit: 500 });
      setProjects(data.projects.filter((p) => p.latitude && p.longitude));
      // Warm the backend's risk cache for all projects in one call, so the
      // per-marker GET /api/risk/{id} calls below are cheap cache hits
      // rather than 150 separate model inferences.
      await api.riskDistribution();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Unable to load the project map.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  const states = useMemo(() => [...new Set(projects.map((p) => p.state))].sort(), [projects]);

  const visible = useMemo(() => {
    const filtered = stateFilter ? projects.filter((p) => p.state === stateFilter) : projects;
    return filtered.slice(0, MAX_MARKERS);
  }, [projects, stateFilter]);

  useEffect(() => {
    if (loading || visible.length === 0) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWarmingRisk(true);
    Promise.all(
      visible.map((p) =>
        api
          .getRisk(p.project_id)
          .then((r) => [p.project_id, r])
          .catch(() => [p.project_id, null])
      )
    ).then((entries) => {
      if (cancelled) return;
      const map = {};
      for (const [id, r] of entries) if (r) map[id] = r;
      setRiskById(map);
      setWarmingRisk(false);
    });
    return () => {
      cancelled = true;
    };
  }, [visible, loading]);

  if (loading) return <div className="page-wrapper"><LoadingBlock label="Loading project locations…" /></div>;
  if (error) return <div className="page-wrapper"><ErrorBanner message={error} onRetry={load} /></div>;

  const center = visible.length > 0 ? [visible[0].latitude, visible[0].longitude] : [22.5, 79];

  return (
    <div className="page-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 14 }}>
        <div>
          <h2 style={{ color: 'var(--navy)' }}>Project Map</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>
            Showing {visible.length} of {projects.length} projects with coordinates
            {stateFilter ? ` in ${stateFilter}` : ''}. {warmingRisk ? 'Loading risk colors…' : ''}
          </p>
        </div>
        <select className="field-input" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All states (first {MAX_MARKERS})</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', gap: 14, marginBottom: 12, fontSize: 12 }}>
        <Legend color={RISK_COLOR.LOW} label="Low risk" />
        <Legend color={RISK_COLOR.MEDIUM} label="Medium risk" />
        <Legend color={RISK_COLOR.HIGH} label="High risk" />
        <Legend color="#94a3b8" label="Not yet analyzed" />
      </div>

      <div className="card" style={{ overflow: 'hidden' }}>
        <MapContainer center={center} zoom={5} style={{ height: 520, width: '100%' }}>
          <TileLayer
            attribution='&copy; OpenStreetMap contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {visible.map((p) => {
            const risk = riskById[p.project_id];
            const color = risk ? RISK_COLOR[risk.risk_level] : '#94a3b8';
            return (
              <CircleMarker
                key={p.project_id}
                center={[p.latitude, p.longitude]}
                radius={7}
                pathOptions={{ color, fillColor: color, fillOpacity: 0.75, weight: 1 }}
              >
                <Popup>
                  <div style={{ fontFamily: 'Poppins, sans-serif', minWidth: 160 }}>
                    <b>{p.project_id}</b>
                    <div style={{ fontSize: 12 }}>{p.domain_details.road_type} -- {p.district}, {p.state}</div>
                    {risk && (
                      <div style={{ margin: '6px 0' }}>
                        <RiskBadge level={risk.risk_level} />
                      </div>
                    )}
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '5px 10px', fontSize: 11, marginTop: 4 }}
                      onClick={() => navigate(`/projects/${p.project_id}`)}
                    >
                      View details
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

function Legend({ color, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block' }} />
      {label}
    </div>
  );
}
