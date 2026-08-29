const LEVEL_CLASS = { LOW: 'low', MEDIUM: 'medium', HIGH: 'high' };

export function RiskBadge({ level }) {
  const cls = LEVEL_CLASS[level] || 'low';
  return <span className={`badge badge-${cls}`}>{level}</span>;
}

export function RiskScoreChip({ score, level }) {
  const cls = LEVEL_CLASS[level] || 'low';
  return <span className={`score-chip score-${cls}`}>{Math.round(score)}</span>;
}

export function StatusPill({ status }) {
  const cls = status ? status.toLowerCase() : 'ongoing';
  return <span className={`status-pill status-${cls}`}>{status}</span>;
}

export function DemoBadge() {
  return <span className="demo-badge">Demo data</span>;
}
