import React, { useState } from 'react';
import './App.css';
import OntologyCanvas from './OntologyCanvas';

function App() {
  const [activeTab, setActiveTab] = useState('compliance');
  return (
    <div className="container">
      <header>
        <h1>Deterministic GraphRAG</h1>
        <p>Text-to-Ontology Extraction Engine</p>
      </header>
      
      <div className="tabs">
        <button 
          className={activeTab === 'compliance' ? 'active' : ''} 
          onClick={() => setActiveTab('compliance')}
        >
          Compliance Q&A
        </button>
        <button 
          className={activeTab === 'ontology' ? 'active' : ''} 
          onClick={() => setActiveTab('ontology')}
        >
          Text-to-Ontology
        </button>
        <button 
          className={activeTab === 'conflicts' ? 'active' : ''} 
          onClick={() => setActiveTab('conflicts')}
        >
          Conflict Detection
        </button>
      </div>

      {activeTab === 'compliance' && <ComplianceQA />}
      {activeTab === 'ontology' && <OntologyExtraction />}
      {activeTab === 'conflicts' && <ConflictDetection />}
    </div>
  );
}

function ComplianceQA() {
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

  const decision = response?.llm_raw_output?.decision || response?.llm_raw_output?.decision?.toUpperCase() || 'UNKNOWN';
  const isApproved = decision === 'APPROVED' || decision === 'approve';
  const finalAnswer = response?.llm_raw_output?.final_answer || response?.llm_raw_output?.reason || '';
  const validationLogic = response?.llm_raw_output?.validation_logic || [];
  const graphUpdates = response?.llm_raw_output?.graph_updates || {};
  const sourceCitation = response?.llm_raw_output?.source_citation || {};

  return (
    <div className="tab-content">
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
        <div className={`result ${isApproved ? 'approved' : 'rejected'}`}>
          <div className="status-badge">
            {isApproved ? '✓ APPROVED' : '✗ REJECTED'}
          </div>
          
          <div className="details">
            <h3>Question:</h3>
            <p>{response.question}</p>
            
            <h3>Final Answer:</h3>
            <p className="final-answer">{finalAnswer}</p>
            
            {validationLogic.length > 0 && (
              <div className="validation-section">
                <h3>Validation Steps:</h3>
                <div className="validation-steps">
                  {validationLogic.map((step, i) => (
                    <div 
                      key={i} 
                      className={`validation-step ${step.status?.toLowerCase() || 'passed'}`}
                      style={{ animationDelay: `${i * 0.15}s` }}
                    >
                      <span className="step-icon">
                        {step.status === 'PASSED' || step.status === 'passed' ? '✓' : '✗'}
                      </span>
                      <span className="step-name">{step.step}</span>
                      <span className="step-detail">{step.detail}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {(graphUpdates.highlight_nodes?.length > 0 || graphUpdates.highlight_edges?.length > 0) && (
              <div className="graph-highlights">
                <h3>Graph Highlights:</h3>
                <div className="highlight-tags">
                  {graphUpdates.highlight_nodes?.map((node, i) => (
                    <span key={`node-${i}`} className="highlight-node">{node}</span>
                  ))}
                  {graphUpdates.highlight_edges?.map((edge, i) => (
                    <span key={`edge-${i}`} className="highlight-edge">{edge}</span>
                  ))}
                  {graphUpdates.violation_edge && (
                    <span className="violation-edge">{graphUpdates.violation_edge}</span>
                  )}
                </div>
              </div>
            )}
            
            {(sourceCitation.file || sourceCitation.exact_quote) && (
              <div className="source-citation">
                <h3>Source Citation:</h3>
                {sourceCitation.file && <p className="citation-file">File: {sourceCitation.file}</p>}
                {sourceCitation.page && <p className="citation-page">Page: {sourceCitation.page}</p>}
                {sourceCitation.exact_quote && (
                  <blockquote className="citation-quote">"{sourceCitation.exact_quote}"</blockquote>
                )}
              </div>
            )}
            
            <h3>Rules Applied:</h3>
            <div className="rules-list">
              {response.graph_rules_applied?.map((rule, i) => (
                <span key={i} className="rule-tag">{rule}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function OntologyExtraction() {
  const [text, setText] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    await extractOntology({ text });
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    await extractOntology({ file });
  };

  const extractOntology = async (payload) => {
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      let res;
      const docId = `doc_${Date.now()}`;
      console.log('Extracting with document_id:', docId);
      console.log('Payload:', payload);
      
      if (payload.file) {
        const formData = new FormData();
        formData.append('file', payload.file);
        res = await fetch('http://localhost:8000/api/v1/extract/pdf', {
          method: 'POST',
          body: formData,
        });
      } else {
        res = await fetch('http://localhost:8000/api/v1/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: payload.text, document_id: docId }),
        });
      }
      console.log('Response status:', res.status);
      if (!res.ok) {
        const errData = await res.json();
        console.error('API Error:', errData);
        throw new Error(errData.detail || 'API Error');
      }
      const data = await res.json();
      console.log('API Response:', data);
      setResponse(data);
    } catch (err) {
      console.error('Extract error:', err);
      setError(err.message || 'Failed to extract ontology. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-content">
      <div className="section">
        <h2>Extract from Text</h2>
        <form onSubmit={handleTextSubmit} className="question-form">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Enter text to extract entities and relationships..."
            rows={4}
          />
          <button type="submit" disabled={loading || !text.trim()}>
            {loading ? 'Extracting...' : 'Extract Ontology'}
          </button>
        </form>
      </div>

      <div className="section">
        <h2>Extract from PDF</h2>
        <form onSubmit={handleFileUpload} className="question-form">
          <input type="file" accept=".pdf" onChange={handleFileChange} />
          <button type="submit" disabled={loading || !file}>
            {loading ? 'Processing PDF...' : 'Upload & Extract'}
          </button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}

      {response && (
        <div className="extraction-results">
          <div className={`status-banner ${response.status}`}>
            Status: {response.status?.toUpperCase() || 'UNKNOWN'}
          </div>

          <div className="canvas-section">
            <h3>Ontology Canvas</h3>
            <OntologyCanvas 
              entities={response.entities || []} 
              relationships={response.relationships || []} 
            />
          </div>

          <div className="entities-section">
            <h3>Extracted Entities ({response.entities?.length || 0})</h3>
            <div className="entities-grid">
              {response.entities?.map((entity, i) => (
                <div key={i} className="entity-card">
                  <span className="entity-type">{entity.entity_type}</span>
                  <span className="entity-name">{entity.name}</span>
                  <span className="entity-mention">"{entity.mention}"</span>
                  <span className="entity-confidence">Confidence: {entity.confidence}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="relationships-section">
            <h3>Extracted Relationships ({response.relationships?.length || 0})</h3>
            <div className="relationships-list">
              {response.relationships?.map((rel, i) => (
                <div key={i} className="relationship-card valid">
                  <span className="rel-source">{rel.source}</span>
                  <span className="rel-arrow">→</span>
                  <span className="rel-type">{rel.relationship}</span>
                  <span className="rel-arrow">→</span>
                  <span className="rel-target">{rel.target}</span>
                  <p className="rel-justification">"{rel.justification}"</p>
                </div>
              ))}
            </div>
          </div>

          {response.rejected?.length > 0 && (
            <div className="rejected-section">
              <h3>Rejected Extractions ({response.rejected.length})</h3>
              <div className="rejected-list">
                {response.rejected.map((item, i) => (
                  <div key={i} className="rejected-card">
                    <span className="rejected-type">{item.type}</span>
                    {item.source && <span className="rejected-source">{item.source}</span>}
                    {item.target && <span className="rejected-target">→ {item.target}</span>}
                    <span className="rejected-reason">⚠ {item.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

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
                  {conflict.severity?.toUpperCase() || 'UNKNOWN'}
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

export default App;
