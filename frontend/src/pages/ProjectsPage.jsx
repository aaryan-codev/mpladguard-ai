import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { ApiError } from '../services/api';
import { LoadingBlock, ErrorBanner, EmptyBlock } from '../components/StateBlocks';
import { StatusPill } from '../components/Badges';
import { useSession } from '../context/SessionContext';
import ProjectForm from '../components/ProjectForm';

export default function ProjectsPage() {
  const { session } = useSession();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('');
  const [roadTypeFilter, setRoadTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.listProjects({ limit: 500 });
      setProjects(data.projects);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Unable to connect to the monitoring service.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, []);

  const states = useMemo(() => [...new Set(projects.map((p) => p.state))].sort(), [projects]);
  const roadTypes = useMemo(
    () => [...new Set(projects.map((p) => p.domain_details.road_type))].sort(),
    [projects]
  );

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return projects.filter((p) => {
      if (stateFilter && p.state !== stateFilter) return false;
      if (roadTypeFilter && p.domain_details.road_type !== roadTypeFilter) return false;
      if (statusFilter && p.work_status !== statusFilter) return false;
      if (term) {
        const haystack = `${p.project_id} ${p.state} ${p.district} ${p.constituency}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  }, [projects, search, stateFilter, roadTypeFilter, statusFilter]);

  if (loading) return <div className="page-wrapper"><LoadingBlock label="Loading projects…" /></div>;
  if (error) return <div className="page-wrapper"><ErrorBanner message={error} onRetry={load} /></div>;

  return (
    <div className="page-wrapper">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
        <div>
          <h2 style={{ color: 'var(--navy)' }}>Road Projects</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{filtered.length} of {projects.length} projects</p>
        </div>
        {session.role === 'officer' && (
          <button className="btn" onClick={() => setShowForm((s) => !s)}>
            {showForm ? 'Close form' : '+ New Project'}
          </button>
        )}
      </div>

      {showForm && session.role === 'officer' && (
        <ProjectForm
          onCreated={(created) => {
            setProjects((prev) => [created, ...prev]);
            setShowForm(false);
          }}
        />
      )}

      <div className="toolbar">
        <input
          className="field-input search-input"
          placeholder="Search by project ID, state, district, constituency…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="field-input" value={stateFilter} onChange={(e) => setStateFilter(e.target.value)}>
          <option value="">All states</option>
          {states.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select className="field-input" value={roadTypeFilter} onChange={(e) => setRoadTypeFilter(e.target.value)}>
          <option value="">All road types</option>
          {roadTypes.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select className="field-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="Completed">Completed</option>
          <option value="Ongoing">Ongoing</option>
          <option value="Delayed">Delayed</option>
        </select>
      </div>

      <div className="card">
        {filtered.length === 0 ? (
          <EmptyBlock title="No matching projects" hint="Try clearing a filter or search term." />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project ID</th>
                  <th>Location</th>
                  <th>Road type</th>
                  <th>Length (km)</th>
                  <th>Est. cost (₹L)</th>
                  <th>Actual (₹L)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 200).map((p) => (
                  <tr key={p.project_id} className="clickable-row" onClick={() => navigate(`/projects/${p.project_id}`)}>
                    <td><b>{p.project_id}</b></td>
                    <td>{p.district}, {p.state}</td>
                    <td>{p.domain_details.road_type}</td>
                    <td>{p.domain_details.road_length_km}</td>
                    <td>{p.financial.estimated_cost_lakh.toLocaleString('en-IN')}</td>
                    <td>{p.financial.actual_expenditure_lakh.toLocaleString('en-IN')}</td>
                    <td><StatusPill status={p.work_status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 200 && (
              <p style={{ fontSize: 11, color: 'var(--text-faint)', padding: '10px 16px' }}>
                Showing first 200 of {filtered.length} matches. Narrow your search or filters to see more precisely.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
