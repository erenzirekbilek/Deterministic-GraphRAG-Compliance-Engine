import React from 'react';

function ExecutionTrace({ logs = [] }) {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  return (
    <div className="execution-trace">
      <h3>Execution Trace</h3>
      
      {logs.length === 0 ? (
        <div className="trace-log">
          <div className="trace-entry">
            <span className="trace-time">--:--:--</span>
            <span className="trace-step">READY</span>
            <span className="trace-message">System ready. Waiting for input...</span>
          </div>
        </div>
      ) : (
        <div className="trace-log">
          {logs.map((log, index) => (
            <div 
              key={index} 
              className={`trace-entry ${log.status || ''}`}
            >
              <span className="trace-time">{formatTime(log.timestamp)}</span>
              <span className="trace-step">{log.step}</span>
              <span className="trace-message">{log.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ExecutionTrace;
