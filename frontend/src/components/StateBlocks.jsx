export function LoadingBlock({ label = 'Loading…' }) {
  return (
    <div className="state-block">
      <div className="spinner" />
      <div>{label}</div>
    </div>
  );
}

export function ErrorBanner({ message, onRetry }) {
  return (
    <div className="error-banner">
      <span>⚠️ {message || 'Unable to connect to the monitoring service.'}</span>
      {onRetry && (
        <button className="btn btn-ghost" onClick={onRetry} style={{ padding: '6px 14px', fontSize: 12 }}>
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyBlock({ title = 'Nothing to show', hint }) {
  return (
    <div className="state-block">
      <div className="state-title">{title}</div>
      {hint && <div>{hint}</div>}
    </div>
  );
}
