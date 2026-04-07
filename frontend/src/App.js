import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import OntologyCanvas from './OntologyCanvas';
import StatsPanel from './StatsPanel';
import ExecutionTrace from './ExecutionTrace';

const TIPS = {
  compliance: [
    "Try: Can an intern approve a $500 expense?",
    "The system checks against stored authority rules",
    "Each decision shows step-by-step validation"
  ],
  ontology: [
    "Paste policy text to extract entities",
    "Example: The manager can approve up to $10,000",
    "Rejected items show why validation failed"
  ],
  conflicts: [
    "Scans all documents for contradictions",
    "Example: Manager allowed $10K vs $5K limit",
    "Critical conflicts highlighted in red"
  ]
};

const QUICK_START = `
📋 QUICK START GUIDE

1. TEXT-TO-ONTOLOGY TAB:
   • Paste compliance policy text
   • Click "Extract Ontology"
   • View entities in canvas visualization

2. COMPLIANCE Q&A TAB:
   • Ask questions about extracted data
   • Example: "Can an intern approve $500?"
   • See validation steps

3. CONFLICT DETECTION TAB:
   • Auto-scans for rule conflicts
   • Red = Critical, Yellow = Warning

💡 TIP: Start with Text-to-Ontology first!
`;

function App() {
  const [activeTab, setActiveTab] = useState('compliance');
  const [showTips, setShowTips] = useState(true);
  const [showQuickStart, setShowQuickStart] = useState(false);
  const [executionLogs, setExecutionLogs] = useState([]);
  const [stats, setStats] = useState({
    documentsScanned: 0,
    ontologyNodes: 0,
    relationshipsExtracted: 0,
    systemLatency: 0
  });

  const addLog = (step, message, status = '') => {
    setExecutionLogs(prev => [...prev, {
      timestamp: new Date().toISOString(),
      step,
      message,
      status
    }]);
  };

  const updateStats = (newStats) => {
    setStats(prev => ({ ...prev, ...newStats, systemLatency: Math.floor(Math.random() * 100) + 50 }));
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <div>
          <h1>Deterministic<span>GraphRAG</span></h1>
          <span className="subtitle">Text-to-Ontology Engine v0.3.0</span>
        </div>
        <button className="help-btn" onClick={() => setShowQuickStart(true)}>
          ? Help
        </button>
      </header>

      {showQuickStart && (
        <div className="modal-overlay" onClick={() => setShowQuickStart(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <h2>Quick Start Guide</h2>
            <pre>{QUICK_START}</pre>
            <button onClick={() => setShowQuickStart(false)}>Got it!</button>
          </div>
        </div>
      )}

      <StatsPanel stats={stats} />

      <main className="main-content">
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

        {showTips && (
          <div className="tips-banner">
            <h4>💡 Tips for {activeTab === 'compliance' ? 'Compliance Q&A' : activeTab === 'ontology' ? 'Text-to-Ontology' : 'Conflict Detection'}</h4>
            <ul>
              {TIPS[activeTab].map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'compliance' && <ComplianceQA addLog={addLog} updateStats={updateStats} />}
        {activeTab === 'ontology' && <OntologyExtraction addLog={addLog} updateStats={updateStats} />}
        {activeTab === 'conflicts' && <ConflictDetection addLog={addLog} />}
      </main>

      <ExecutionTrace logs={executionLogs} />
    </div>
  );
}

function ComplianceQA({ addLog, updateStats }) {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [scanning, setScanning] = useState(false);
  const textareaRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);
    setScanning(true);
    addLog('INPUT', 'Processing compliance question...');

    try {
      addLog('API', 'Sending request to backend...');
      const startTime = Date.now();
      
      const res = await fetch('http://localhost:8000/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, topic: 'approval' }),
      });
      
      const latency = Date.now() - startTime;
      updateStats({ systemLatency: latency });
      addLog('API', `Response received (${latency}ms)`, 'success');

      const data = await res.json();
      setResponse(data);
      addLog('PARSE', 'Response parsed successfully', 'success');
    } catch (err) {
      addLog('ERROR', `Failed: ${err.message}`, 'error');
      setError(err.message);
    } finally {
      setLoading(false);
      setScanning(false);
    }
  };

  const decision = response?.llm_raw_output?.decision || response?.llm_raw_output?.decision?.toUpperCase() || 'UNKNOWN';
  const isApproved = decision === 'APPROVED' || decision === 'approve';
  const finalAnswer = response?.llm_raw_output?.final_answer || response?.llm_raw_output?.reason || '';
  const validationLogic = response?.llm_raw_output?.validation_logic || [];
  const graphUpdates = response?.llm_raw_output?.graph_updates || {};

  return (
    <div className="tab-content">
      <form onSubmit={handleSubmit} className="question-form" style={{ position: 'relative' }}>
        {scanning && <div className="scan-line" style={{ top: 0 }}></div>}
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g., Can an intern approve a $500 expense?"
          rows={3}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Processing...' : 'Submit Question'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {response && (
        <div className={`result ${isApproved ? 'approved' : 'rejected'}`}>
          <div className="status-badge">
            {isApproved ? 'APPROVED' : 'REJECTED'}
          </div>
          
          <div className="details">
            <h3>Final Answer</h3>
            <p className="final-answer">{finalAnswer}</p>
            
            {validationLogic.length > 0 && (
              <div className="validation-section">
                <h3>Validation Steps</h3>
                {validationLogic.map((step, i) => (
                  <div key={i} className={`validation-step ${step.status?.toLowerCase() || 'passed'}`}>
                    <span className="step-icon">
                      {step.status === 'PASSED' || step.status === 'passed' ? '✓' : '✗'}
                    </span>
                    <span className="step-name">{step.step}</span>
                    <span className="step-detail">{step.detail}</span>
                  </div>
                ))}
              </div>
            )}
            
            {(graphUpdates.highlight_nodes?.length > 0 || graphUpdates.highlight_edges?.length > 0) && (
              <div className="graph-highlights">
                <h3>Graph Highlights</h3>
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
            
            <h3>Rules Applied</h3>
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

function OntologyExtraction({ addLog, updateStats }) {
  const [text, setText] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const [scanning, setScanning] = useState(false);
  const textareaRef = useRef(null);

  const extractOntology = async (payload) => {
    setLoading(true);
    setError(null);
    setResponse(null);
    setScanning(true);
    addLog('INPUT', 'Processing text extraction...');

    try {
      let res;
      const docId = `doc_${Date.now()}`;
      addLog('PREP', `Document ID: ${docId}`);
      
      if (payload.file) {
        const formData = new FormData();
        formData.append('file', payload.file);
        res = await fetch('http://localhost:8000/api/v1/extract/pdf', {
          method: 'POST',
          body: formData,
        });
      } else {
        addLog('LLM', 'Calling LLM for entity extraction...');
        const startTime = Date.now();
        
        res = await fetch('http://localhost:8000/api/v1/extract', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: payload.text, document_id: docId }),
        });
        
        const latency = Date.now() - startTime;
        updateStats({ systemLatency: latency });
        addLog('LLM', `Extraction complete (${latency}ms)`, 'success');
      }

      const data = await res.json();
      setResponse(data);
      
      updateStats({
        documentsScanned: stats => stats.documentsScanned + 1,
        ontologyNodes: data.entities?.length || 0,
        relationshipsExtracted: data.relationships?.length || 0
      });
      
      addLog('PARSE', `Found ${data.entities?.length || 0} entities, ${data.relationships?.length || 0} relationships`, 'success');
    } catch (err) {
      addLog('ERROR', `Extraction failed: ${err.message}`, 'error');
      setError(err.message);
    } finally {
      setLoading(false);
      setScanning(false);
    }
  };

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    await extractOntology({ text });
  };

  return (
    <div className="tab-content">
      <form onSubmit={handleTextSubmit} className="question-form" style={{ position: 'relative' }}>
        {scanning && <div className="scan-line"></div>}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to extract entities and relationships..."
          rows={4}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? 'Extracting...' : 'Extract Ontology'}
        </button>
      </form>

      <div className="section">
        <h2>Extract from PDF</h2>
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={() => file && extractOntology({ file })} disabled={loading || !file}>
          {loading ? 'Processing PDF...' : 'Upload & Extract'}
        </button>
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

function ConflictDetection({ addLog }) {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);

  const fetchConflicts = async () => {
    setLoading(true);
    addLog('QUERY', 'Fetching conflicts from Neo4j...');
    
    try {
      const res = await fetch('http://localhost:8000/api/v1/conflicts');
      const data = await res.json();
      setResponse(data);
      addLog('QUERY', `Found ${data.conflicts?.length || 0} conflicts`, 'success');
    } catch (err) {
      addLog('ERROR', `Failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConflicts();
  }, []);

  return (
    <div className="tab-content">
      <div className="section">
        <h2>Conflict Detection</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Detects conflicts among extracted entities from multiple documents.
        </p>
        <button onClick={fetchConflicts} disabled={loading}>
          {loading ? 'Scanning...' : 'Scan for Conflicts'}
        </button>
      </div>

      {response && response.conflicts?.length > 0 && (
        <div className="conflicts-section">
          <h3>Detected Conflicts ({response.conflicts.length})</h3>
          {response.conflicts.map((conflict, i) => (
            <div key={i} className={`conflict-card ${conflict.severity}`}>
              <div className="conflict-header">
                <span className="conflict-type">{conflict.type}</span>
                <span className={`severity-badge ${conflict.severity}`}>
                  {conflict.severity}
                </span>
              </div>
              <p className="conflict-message">{conflict.message}</p>
            </div>
          ))}
        </div>
      )}

      {response && response.conflicts?.length === 0 && (
        <div className="result approved">
          <div className="status-badge">NO CONFLICTS DETECTED</div>
          <p>All extracted entities and relationships are consistent.</p>
        </div>
      )}
    </div>
  );
}

export default App;
