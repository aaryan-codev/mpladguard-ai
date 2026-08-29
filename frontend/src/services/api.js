const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError('Unable to connect to the monitoring service.', 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body; keep default message */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return null;
  return response.json();
}

function qs(params = {}) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  if (entries.length === 0) return '';
  return '?' + new URLSearchParams(entries).toString();
}

export const api = {
  health: () => request('/api/health'),

  listProjects: ({ limit = 500, offset = 0 } = {}) =>
    request(`/api/projects${qs({ limit, offset })}`),

  getProject: (projectId) => request(`/api/projects/${encodeURIComponent(projectId)}`),

  createProject: (payload) =>
    request('/api/projects', { method: 'POST', body: JSON.stringify(payload) }),

  getRisk: (projectId) => request(`/api/risk/${encodeURIComponent(projectId)}`),

  analyzeRisk: (payload) =>
    request('/api/risk/analyze', { method: 'POST', body: JSON.stringify(payload) }),

  dashboardSummary: () => request('/api/dashboard/summary'),
  riskDistribution: () => request('/api/dashboard/risk-distribution'),
  financialSummary: () => request('/api/dashboard/financial-summary'),
  statusDistribution: () => request('/api/dashboard/status-distribution'),
  stateDistribution: () => request('/api/dashboard/state-distribution'),
};

export default api;
