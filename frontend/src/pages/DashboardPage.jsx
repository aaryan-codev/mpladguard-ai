import { useEffect, useState } from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import api, { ApiError } from '../services/api';
import { LoadingBlock, ErrorBanner } from '../components/StateBlocks';
import { useSession } from '../context/SessionContext';

const RISK_COLORS = { LOW: '#16a34a', MEDIUM: '#f59e0b', HIGH: '#ef4444' };
const STATUS_COLORS = { Completed: '#16a34a', Ongoing: '#0d5dad', Delayed: '#f59e0b' };

export default function DashboardPage() {
  const { session } = useSession();
  const [summary, setSummary] = useState(null);
  const [riskDist, setRiskDist] = useState(null);
  const [statusDist, setStatusDist] = useState(null);
  const [stateDist, setStateDist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [s, r, st, sd] = await Promise.all([
        api.dashboardSummary(),
        api.riskDistribution(),
        api.statusDistribution(),
        api.stateDistribution(),
      ]);
      setSummary(s);
      setRiskDist(r);
      setStatusDist(st);
      setStateDist(sd);
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

  if (loading) return <div className="page-wrapper"><LoadingBlock label="Loading dashboard…" /></div>;
  if (error) return <div className="page-wrapper"><ErrorBanner message={error} onRetry={load} /></div>;

  const riskPieData = Object.entries(riskDist.distribution).map(([level, count]) => ({ name: level, value: count }));
  const statusBarData = Object.entries(statusDist.distribution).map(([status, count]) => ({ status, count }));
  const stateBarData = Object.entries(stateDist.distribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([state, count]) => ({ state, count }));

  const isOfficer = session.role === 'officer';

  return (
    <div className="page-wrapper">
      <h2 style={{ color: 'var(--navy)', marginBottom: 4 }}>
        {isOfficer ? 'Officer Dashboard' : 'Public Transparency Overview'}
      </h2>
      <p style={{ color: 'var(--text-muted)', fontSize: 12.5, marginBottom: 18 }}>
        Road projects under MPLADS -- {summary.total_projects} tracked, current MVP scope
      </p>

      <div className="stat-grid">
        <StatCard label="Total projects" value={summary.total_projects} />
        <StatCard label="Completed" value={summary.completed_projects} accent="green" />
        <StatCard label="Ongoing" value={summary.ongoing_projects} accent="amber" />
        <StatCard label="Delayed" value={summary.delayed_projects} accent="red" />
        <StatCard
          label="Est. cost (₹ lakh)"
          value={summary.total_estimated_cost_lakh.toLocaleString('en-IN')}
        />
        <StatCard
          label="Actual expenditure (₹ lakh)"
          value={summary.total_actual_expenditure_lakh.toLocaleString('en-IN')}
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 4 }}>
        <div className="card">
          <div className="card-head">
            <span>AI RISK DISTRIBUTION</span>
            <span>{riskDist.total_analyzed} analyzed</span>
          </div>
          <div className="card-body" style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskPieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={3}>
                  {riskPieData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="card-body" style={{ paddingTop: 0 }}>
            <p style={{ fontSize: 11, color: 'var(--text-faint)' }}>
              Anomaly indicators from the road Isolation Forest model -- flags projects for human review, not
              confirmed fraud.
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <span>PROJECT STATUS</span>
            <span>{statusDist.total} total</span>
          </div>
          <div className="card-body" style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusBarData}>
                <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {statusBarData.map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] || '#0d5dad'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span>TOP 10 STATES BY PROJECT COUNT</span>
        </div>
        <div className="card-body" style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={stateBarData} layout="vertical" margin={{ left: 40 }}>
              <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
              <YAxis type="category" dataKey="state" tick={{ fontSize: 11 }} width={110} />
              <Tooltip />
              <Bar dataKey="count" fill="#0e9e5a" radius={[0, 6, 6, 0]} fillOpacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div className={`stat-card ${accent ? `accent-${accent}` : ''}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
