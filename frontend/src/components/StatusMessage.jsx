// Presentational helper for loading / error / empty / success states, styled consistently across pages.

function StatusMessage({ kind = 'empty', children }) {
  const isAnnounced = kind === 'success' || kind === 'error';
  const liveProps = isAnnounced ? { role: 'status', 'aria-live': 'polite' } : {};
  return (
    <p className={`status-message status-message--${kind}`} {...liveProps}>
      {children}
    </p>
  );
}

export default StatusMessage;
