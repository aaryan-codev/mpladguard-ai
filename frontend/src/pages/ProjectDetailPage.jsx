import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api, { ApiError } from '../services/api';
import { LoadingBlock, ErrorBanner } from '../components/StateBlocks';
import { RiskBadge, RiskScoreChip, StatusPill, DemoBadge } from '../components/Badges';

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [riskLoading, setRiskLoading] = useState(true);
  const [error, setError] = useState('');
  const [riskError, setRiskError] = useState('');

  async function loadProject() {
    setLoading(true);
    setError('');
    try {
      const data = await api.getProject(projectId);
      setProject(data);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Unable to load this project.');
    } finally {
      setLoading(false);
    }
  }

  async function loadRisk() {
    setRiskLoading(true);
    setRiskError('');
    try {
      const data = await api.getRisk(projectId);
      setRisk(data);
    } catch (e) {
      setRiskError(e instanceof ApiError ? e.message : 'Unable to run risk analysis for this project.');
    } finally {
      setRiskLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProject();
    loadRisk();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (loading) return <div className="page-wrapper"><LoadingBlock label="Loading project…" /></div>;
  if (error) return <div className="page-wrapper"><ErrorBanner message={error} onRetry={loadProject} /></div>;
  if (!project) return null;

  const { domain_details, financial, schedule, demo_enrichment } = project;

  return (
    <div className="page-wrapper">
      <button className="btn btn-ghost" onClick={() => navigate(-1)} style={{ marginBottom: 14 }}>
        ← Back
      </button>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
        <div>
          <h2 style={{ color: 'var(--navy)' }}>{project.project_name}</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 12.5 }}>{project.project_id} -- {project.constituency} constituency</p>
        </div>
        <StatusPill status={project.work_status} />
      </div>

      <div className="card">
        <div className="card-head"><span>PROJECT INFORMATION</span></div>
        <div className="card-body detail-grid">
          <Detail label="State" value={project.state} />
          <Detail label="District" value={project.district} />
          <Detail label="Constituency" value={project.constituency} />
          <Detail label="Implementing agency" value={project.implementing_agency} />
          <Detail label="Road type" value={domain_details.road_type} />
          <Detail label="Road length" value={`${domain_details.road_length_km} km`} />
        </div>
      </div>

      <div className="card">
        <div className="card-head"><span>FINANCIAL INFORMATION</span></div>
        <div className="card-body detail-grid">
          <Detail label="Estimated cost" value={`₹${financial.estimated_cost_lakh.toLocaleString('en-IN')} lakh`} />
          <Detail label="Actual expenditure" value={`₹${financial.actual_expenditure_lakh.toLocaleString('en-IN')} lakh`} />
          <Detail
            label="Cost deviation"
            value={financial.cost_deviation_pct !== null ? `${financial.cost_deviation_pct}%` : '—'}
          />
          <Detail
            label="Cost per km (actual)"
            value={`₹${(financial.actual_expenditure_lakh / domain_details.road_length_km).toFixed(2)} lakh/km`}
          />
        </div>
      </div>

      <div className="card">
        <div className="card-head"><span>SCHEDULE INFORMATION</span></div>
        <div className="card-body detail-grid">
          <Detail label="Start date" value={schedule.project_start_date} />
          <Detail label="Completion date" value={schedule.project_completion_date || 'In progress'} />
          <Detail label="Planned duration" value={`${schedule.planned_duration_days} days`} />
          <Detail label="Actual duration" value={`${schedule.actual_duration_days} days`} />
          <Detail label="Delay" value={`${schedule.delay_days} days (${schedule.delay_pct}%)`} />
        </div>
      </div>

      <div className="card">
        <div className="card-head"><span>AI RISK ANALYSIS</span></div>
        <div className="card-body">
          {riskLoading && <LoadingBlock label="Running anomaly detection…" />}
          {riskError && <ErrorBanner message={riskError} onRetry={loadRisk} />}
          {risk && !riskLoading && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
                <RiskScoreChip score={risk.risk_score} level={risk.risk_level} />
                <div>
                  <RiskBadge level={risk.risk_level} />
                  <div style={{ fontSize: 11, color: 'var(--text-faint)', marginTop: 3 }}>
                    Risk score {risk.risk_score.toFixed(1)} / 100 -- model {risk.model_version}
                  </div>
                </div>
                {risk.anomaly && (
                  <span style={{ fontSize: 12, color: 'var(--red-dark)', fontWeight: 600 }}>
                    Potential anomaly detected — requires investigation.
                  </span>
                )}
              </div>

              {risk.risk_factors.length > 0 ? (
                <>
                  <p style={{ fontSize: 12, fontWeight: 700, color: 'var(--navy)', marginBottom: 8 }}>
                    Potential risk indicators
                  </p>
                  {risk.risk_factors.map((f) => (
                    <div key={f.feature} className={`risk-factor ${f.severity}`}>
                      {f.explanation}
                    </div>
                  ))}
                </>
              ) : (
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  No engineered feature was statistically unusual enough to flag for this project.
                </p>
              )}

              {risk.warnings.length > 0 && (
                <div className="disclaimer-box">
                  {risk.warnings.map((w) => (
                    <div key={w}>ℹ️ {w}</div>
                  ))}
                </div>
              )}
              <div className="disclaimer-box">{risk.disclaimer}</div>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <span>PROJECT PROFILE (CONTRACTOR / TENDER / BENEFICIARIES)</span>
          <DemoBadge />
        </div>
        <div className="card-body">
          <p style={{ fontSize: 11, color: 'var(--text-faint)', marginBottom: 12 }}>
            {demo_enrichment.note}
          </p>
          <div className="detail-grid">
            <Detail label="Contractor" value={demo_enrichment.contractor_name} />
            <Detail label="Contractor ID" value={demo_enrichment.contractor_id} />
            <Detail label="Tender ID" value={demo_enrichment.tender_id} />
            <Detail label="Procurement method" value={demo_enrichment.procurement_method} />
            <Detail label="Bid count" value={demo_enrichment.bid_count} />
            <Detail label="Winning bid" value={`₹${demo_enrichment.winning_bid_lakh.toLocaleString('en-IN')} lakh`} />
            <Detail label="Second lowest bid" value={`₹${demo_enrichment.second_lowest_bid_lakh.toLocaleString('en-IN')} lakh`} />
            <Detail label="Estimated beneficiaries" value={demo_enrichment.estimated_beneficiaries.toLocaleString('en-IN')} />
            <Detail label="Population served" value={demo_enrichment.population_served.toLocaleString('en-IN')} />
          </div>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="detail-item">
      <div className="detail-label">{label}</div>
      <div className="detail-value">{value}</div>
    </div>
  );
}
