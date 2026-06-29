export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="panel"
      style={{
        borderColor: "var(--danger)",
        background: "rgba(239,68,68,0.08)",
      }}
    >
      <p style={{ margin: "0 0 12px", color: "var(--text-primary)" }}>{message}</p>
      {onRetry ? (
        <button type="button" className="btn" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
