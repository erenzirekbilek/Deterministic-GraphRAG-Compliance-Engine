import React from 'react';

function StatsPanel({ stats = {} }) {
  const {
    documentsScanned = 0,
    ontologyNodes = 0,
    systemLatency = 0,
    relationshipsExtracted = 0
  } = stats;

  return (
    <div className="stats-panel">
      <h3>System Status</h3>
      
      <div className="stat-item">
        <span className="stat-label">Documents</span>
        <span className="stat-value">{documentsScanned}</span>
      </div>
      
      <div className="stat-item">
        <span className="stat-label">Nodes</span>
        <span className="stat-value">{ontologyNodes}</span>
      </div>
      
      <div className="stat-item">
        <span className="stat-label">Relations</span>
        <span className="stat-value">{relationshipsExtracted}</span>
      </div>
      
      <div className="stat-item">
        <span className="stat-label">Latency</span>
        <span className={`stat-value ${systemLatency > 500 ? 'warning' : ''}`}>
          {systemLatency}ms
        </span>
      </div>

      <h3>Provider</h3>
      <div className="stat-item">
        <span className="stat-label">LLM</span>
        <span className="stat-value success">Groq</span>
      </div>
    </div>
  );
}

export default StatsPanel;
