import React, { useState } from 'react';
import './App.css';

function App() {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch('http://localhost:8000/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, topic: 'approval' }),
      });
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError('Failed to connect to backend. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header>
        <h1>GraphRAG Compliance Engine</h1>
        <p>Ask compliance questions and get deterministic validation</p>
      </header>

      <form onSubmit={handleSubmit} className="question-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., Can an intern approve a $500 expense?"
          rows={3}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Processing...' : 'Submit Question'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {response && (
        <div className={`result ${response.approved ? 'approved' : 'rejected'}`}>
          <div className="status-badge">
            {response.approved ? '✓ APPROVED' : '✗ REJECTED'}
          </div>
          
          <div className="details">
            <h3>Question:</h3>
            <p>{response.question}</p>
            
            <h3>LLM Output:</h3>
            <p>Decision: {response.llm_raw_output?.decision}</p>
            <p>Reason: {response.llm_raw_output?.reason}</p>
            
            <h3>Validation:</h3>
            <p className="validation-reason">{response.validation_reason}</p>
            
            <h3>Rules Applied:</h3>
            <div className="rules-list">
              {response.graph_rules_applied?.map((rule, i) => (
                <span key={i} className="rule-tag">{rule}</span>
              ))}
            </div>
            
            <p className="provider">LLM Provider: {response.llm_provider}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
