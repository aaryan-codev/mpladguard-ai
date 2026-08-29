import { useState } from 'react';
import api, { ApiError } from '../services/api';

const ROAD_TYPES = ['Village Road', 'District Road', 'Rural Link Road', 'Urban Internal Road', 'State Highway Link'];

const EMPTY = {
  project_id: '',
  state: '',
  district: '',
  parliamentary_constituency: '',
  implementing_agency: '',
  road_type: ROAD_TYPES[0],
  road_length_km: '',
  estimated_cost_lakh: '',
  actual_expenditure_lakh: '',
  planned_duration_days: '',
  actual_duration_days: '',
  project_start_date: '',
  project_completion_date: '',
  project_status: 'Ongoing',
};

export default function ProjectForm({ onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');

    if (!form.project_id.trim()) {
      setError('Project ID is required.');
      return;
    }

    const payload = {
      ...form,
      road_length_km: Number(form.road_length_km),
      estimated_cost_lakh: Number(form.estimated_cost_lakh),
      actual_expenditure_lakh: Number(form.actual_expenditure_lakh),
      planned_duration_days: Number(form.planned_duration_days),
      actual_duration_days: Number(form.actual_duration_days),
      project_completion_date: form.project_completion_date || null,
    };

    setSubmitting(true);
    try {
      const created = await api.createProject(payload);
      onCreated(created);
      setForm(EMPTY);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to create project.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card">
      <div className="card-head"><span>NEW ROAD PROJECT ENTRY</span></div>
      <div className="card-body">
        <form onSubmit={handleSubmit}>
          {error && <div className="error-banner">⚠️ {error}</div>}
          <div className="form-grid">
            <Field label="Project ID" value={form.project_id} onChange={(v) => update('project_id', v)} placeholder="MPLADS-RD-00501" />
            <Field label="State" value={form.state} onChange={(v) => update('state', v)} />
            <Field label="District" value={form.district} onChange={(v) => update('district', v)} />
            <Field label="Parliamentary constituency" value={form.parliamentary_constituency} onChange={(v) => update('parliamentary_constituency', v)} />
            <Field label="Implementing agency" value={form.implementing_agency} onChange={(v) => update('implementing_agency', v)} />
            <div>
              <label className="field-label">Road type</label>
              <select className="field-input" value={form.road_type} onChange={(e) => update('road_type', e.target.value)}>
                {ROAD_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <Field label="Road length (km)" type="number" step="0.01" value={form.road_length_km} onChange={(v) => update('road_length_km', v)} />
            <Field label="Estimated cost (₹ lakh)" type="number" step="0.01" value={form.estimated_cost_lakh} onChange={(v) => update('estimated_cost_lakh', v)} />
            <Field label="Actual expenditure (₹ lakh)" type="number" step="0.01" value={form.actual_expenditure_lakh} onChange={(v) => update('actual_expenditure_lakh', v)} />
            <Field label="Planned duration (days)" type="number" value={form.planned_duration_days} onChange={(v) => update('planned_duration_days', v)} />
            <Field label="Actual duration (days)" type="number" value={form.actual_duration_days} onChange={(v) => update('actual_duration_days', v)} />
            <Field label="Project start date" type="date" value={form.project_start_date} onChange={(v) => update('project_start_date', v)} />
            <Field label="Completion date (if any)" type="date" value={form.project_completion_date} onChange={(v) => update('project_completion_date', v)} />
            <div>
              <label className="field-label">Status</label>
              <select className="field-input" value={form.project_status} onChange={(e) => update('project_status', e.target.value)}>
                <option value="Ongoing">Ongoing</option>
                <option value="Completed">Completed</option>
                <option value="Delayed">Delayed</option>
              </select>
            </div>
          </div>
          <button className="btn" type="submit" disabled={submitting} style={{ marginTop: 16 }}>
            {submitting ? 'Saving…' : 'Save project'}
          </button>
          <p style={{ fontSize: 10.5, color: 'var(--text-faint)', marginTop: 8 }}>
            Saved in-memory for this backend session (hackathon MVP -- not persisted to the CSV).
            AI risk analysis is available immediately from the project's detail page.
          </p>
        </form>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', ...rest }) {
  return (
    <div>
      <label className="field-label">{label}</label>
      <input
        className="field-input"
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        {...rest}
      />
    </div>
  );
}
