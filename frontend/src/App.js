function ConflictDetection() {
  const [conflicts, setConflicts] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const detectConflicts = async () => {
    setLoading(true);
    setError(null);
    setConflicts(null);

    try {
      const res = await fetch('http://localhost:8000/api/v1/conflicts');
      const data = await res.json();
      setConflicts(data);
    } catch (err) {
      setError('Failed to detect conflicts. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-content">
      <div className="section">
        <h2>Conflict Detection</h2>
        <p style={{color: '#888', marginBottom: '15px'}}>
          Automatically detect conflicts among extracted entities and relationships from multiple documents.
        </p>
        <button onClick={detectConflicts} disabled={loading} className="question-form" style={{padding: '15px'}}>
          {loading ? 'Scanning for conflicts...' : 'Scan for Conflicts'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {conflicts && (
        <div className="extraction-results">
          <div className={`status-banner ${conflicts.total_conflicts > 0 ? 'rejected' : 'success'}`}>
            Total Conflicts: {conflicts.total_conflicts} 
            (Critical: {conflicts.critical}, Warning: {conflicts.warning})
          </div>

          {conflicts.conflicts?.length === 0 && (
            <div className="result approved">
              <div className="status-badge">✓ No Conflicts Detected</div>
              <p>Your database is conflict-free!</p>
            </div>
          )}

          {conflicts.conflicts?.map((conflict, i) => (
            <div key={i} className={`conflict-card ${conflict.severity}`}>
              <div className="conflict-header">
                <span className={`severity-badge ${conflict.severity}`}>
                  {conflict.severity.toUpperCase()}
                </span>
                <span className="conflict-type">{conflict.type}</span>
              </div>
              <p className="conflict-message">{conflict.message}</p>
              <details>
                <summary style={{color: '#666', cursor: 'pointer'}}>View Details</summary>
                <pre style={{color: '#888', fontSize: '0.8rem', marginTop: '10px'}}>
                  {JSON.stringify(conflict.details, null, 2)}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}