import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const RULE_TYPES = [
  'HAS_AUTHORITY',
  'IS_PROHIBITED',
  'MUST_FULFILL',
  'REQUIRES_PRECONDITION',
  'DEPENDS_ON',
  'APPLIES_TO',
];

const RULE_TYPE_COLORS = {
  HAS_AUTHORITY: '#22c55e',
  IS_PROHIBITED: '#ef4444',
  MUST_FULFILL: '#3b82f6',
  REQUIRES_PRECONDITION: '#f59e0b',
  DEPENDS_ON: '#8b5cf6',
  APPLIES_TO: '#06b6d4',
};

function RuleManager({ addLog, updateStats }) {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [rules, setRules] = useState([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0, rejected: 0, documents: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentDoc, setCurrentDoc] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [filter, setFilter] = useState('all');
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualRule, setManualRule] = useState({ rule_type: 'HAS_AUTHORITY', source_entity: '', target_entity: '', description: '', limit: '' });
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState(null);

  useEffect(() => {
    fetchPendingRules();
  }, []);

  const fetchPendingRules = async (docId = null) => {
    try {
      const url = docId
        ? `/api/v1/pending?document_id=${docId}`
        : '/api/v1/pending';
      const res = await fetch(url);
      const data = await res.json();
      setRules(data.rules || []);
      setStats(data.stats || {});
      if (data.document_id && data.document_id !== 'all') setCurrentDoc(data.document_id);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTextExtract = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setApplyResult(null);
    addLog('RULE_EXTRACT', 'Extracting rules from text...');

    try {
      const res = await fetch('/api/v1/rules/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, document_name: `text-${Date.now()}` }),
      });
      const data = await res.json();
      setRules(data.rules || []);
      setCurrentDoc(data.document_name);
      addLog('RULE_EXTRACT', `Extracted ${data.stats?.extracted || 0} rules`, 'success');
      fetchPendingRules();
    } catch (err) {
      setError(err.message);
      addLog('RULE_EXTRACT', `Failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleFileExtract = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setApplyResult(null);
    addLog('RULE_EXTRACT', `Extracting rules from ${file.name}...`);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/v1/extract/pdf', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (data.detail) {
        setError(data.detail);
      } else {
        setRules(data.rules || []);
        setCurrentDoc(data.document_name || data.filename);
        addLog('RULE_EXTRACT', `Extracted ${data.stats?.extracted || 0} rules from ${file.name}`, 'success');
        fetchPendingRules();
      }
    } catch (err) {
      setError(err.message);
      addLog('RULE_EXTRACT', `Failed: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (ruleId, status, edits = null) => {
    try {
      await fetch('/api/v1/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId, status, edits }),
      });
      fetchPendingRules();
      setEditingRule(null);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleBulkReview = async (status) => {
    const pendingRules = rules.filter(r => r.status === 'pending');
    if (pendingRules.length === 0) return;

    try {
      const reviews = pendingRules.map(r => ({ rule_id: r.id, status }));
      await fetch('/api/v1/review/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviews }),
      });
      fetchPendingRules();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleApplyRules = async () => {
    setApplying(true);
    setApplyResult(null);
    addLog('RULE_APPLY', 'Applying approved rules to Neo4j...');

    try {
      const res = await fetch('/api/v1/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentDoc ? { document_id: currentDoc } : {}),
      });
      const data = await res.json();
      setApplyResult(data);
      addLog('RULE_APPLY', `Applied ${data.applied} rules, ${data.errors?.length || 0} errors`, data.errors?.length === 0 ? 'success' : 'error');
      fetchPendingRules();
    } catch (err) {
      setError(err.message);
      addLog('RULE_APPLY', `Failed: ${err.message}`, 'error');
    } finally {
      setApplying(false);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    try {
      await fetch(`/api/v1/pending/${ruleId}`, { method: 'DELETE' });
      fetchPendingRules();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleManualCreate = async () => {
    if (!manualRule.source_entity || !manualRule.target_entity || !manualRule.description) return;
    try {
      await fetch('/api/v1/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...manualRule,
          limit: manualRule.limit ? parseFloat(manualRule.limit) : null,
        }),
      });
      setManualRule({ rule_type: 'HAS_AUTHORITY', source_entity: '', target_entity: '', description: '', limit: '' });
      setShowManualForm(false);
      fetchPendingRules();
    } catch (err) {
      setError(err.message);
    }
  };

  const filteredRules = filter === 'all' ? rules : rules.filter(r => r.status === filter);

  return (
    <div className="tab-content">
      <div className="rule-manager-layout">
        {/* Left: Input Panel */}
        <div className="rule-input-panel">
          <h3>Extract Rules from Document</h3>

          <div className="input-section">
            <h4>Paste Policy Text</h4>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste compliance policy, SOP, or regulatory text..."
              rows={6}
              disabled={loading}
            />
            <button onClick={handleTextExtract} disabled={loading || !text.trim()}>
              {loading ? 'Extracting...' : 'Extract Rules from Text'}
            </button>
          </div>

          <div className="input-section">
            <h4>Upload Document</h4>
            <input type="file" accept=".pdf,.txt,.md,.docx" onChange={(e) => setFile(e.target.files[0])} />
            <button onClick={handleFileExtract} disabled={loading || !file}>
              {loading ? 'Processing...' : 'Upload & Extract'}
            </button>
          </div>

          <div className="input-section">
            <h4>Manual Rule Entry</h4>
            <button className="secondary-btn" onClick={() => setShowManualForm(!showManualForm)}>
              {showManualForm ? 'Cancel' : '+ Add Rule Manually'}
            </button>
            {showManualForm && (
              <div className="manual-rule-form">
                <select value={manualRule.rule_type} onChange={(e) => setManualRule({ ...manualRule, rule_type: e.target.value })}>
                  {RULE_TYPES.map(rt => <option key={rt} value={rt}>{rt}</option>)}
                </select>
                <input
                  type="text"
                  placeholder="Source entity (e.g., manager)"
                  value={manualRule.source_entity}
                  onChange={(e) => setManualRule({ ...manualRule, source_entity: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Target entity (e.g., approve_expense)"
                  value={manualRule.target_entity}
                  onChange={(e) => setManualRule({ ...manualRule, target_entity: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="Description"
                  value={manualRule.description}
                  onChange={(e) => setManualRule({ ...manualRule, description: e.target.value })}
                />
                <input
                  type="number"
                  placeholder="Limit (optional, 0=unlimited)"
                  value={manualRule.limit}
                  onChange={(e) => setManualRule({ ...manualRule, limit: e.target.value })}
                />
                <button onClick={handleManualCreate}>Create Rule</button>
              </div>
            )}
          </div>
        </div>

        {/* Right: Review Panel */}
        <div className="rule-review-panel">
          <div className="review-header">
            <h3>Rule Review</h3>
            <div className="review-stats">
              <span className="stat-badge total">Total: {stats.total || rules.length}</span>
              <span className="stat-badge pending">Pending: {stats.pending || rules.filter(r => r.status === 'pending').length}</span>
              <span className="stat-badge approved">Approved: {stats.approved || rules.filter(r => r.status === 'approved').length}</span>
              <span className="stat-badge rejected">Rejected: {stats.rejected || rules.filter(r => r.status === 'rejected').length}</span>
            </div>
          </div>

          <div className="review-actions">
            <div className="filter-tabs">
              {['all', 'pending', 'approved', 'rejected'].map(f => (
                <button key={f} className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
            <div className="bulk-actions">
              <button className="approve-all-btn" onClick={() => handleBulkReview('approved')} disabled={rules.filter(r => r.status === 'pending').length === 0}>
                Approve All Pending
              </button>
              <button className="reject-all-btn" onClick={() => handleBulkReview('rejected')} disabled={rules.filter(r => r.status === 'pending').length === 0}>
                Reject All Pending
              </button>
              <button className="apply-btn" onClick={handleApplyRules} disabled={applying || (stats.approved || rules.filter(r => r.status === 'approved').length) === 0}>
                {applying ? 'Applying...' : `Apply to Neo4j (${stats.approved || rules.filter(r => r.status === 'approved').length})`}
              </button>
            </div>
          </div>

          {applyResult && (
            <div className={`apply-result ${applyResult.errors?.length > 0 ? 'error' : 'success'}`}>
              Applied {applyResult.applied} rules to Neo4j.
              {applyResult.errors?.length > 0 && (
                <ul>
                  {applyResult.errors.map((err, i) => <li key={i}>{err}</li>)}
                </ul>
              )}
            </div>
          )}

          {error && <div className="error">{error}</div>}

          <div className="rules-table-container">
            {filteredRules.length === 0 ? (
              <div className="empty-state">
                <p>No rules found. Upload a document or add rules manually.</p>
              </div>
            ) : (
              <table className="rules-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Limit</th>
                    <th>Confidence</th>
                    <th>Description</th>
                    <th>Source Text</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRules.map((rule) => (
                    <RuleRow
                      key={rule.id}
                      rule={rule}
                      editing={editingRule === rule.id}
                      onStartEdit={() => setEditingRule(rule.id)}
                      onCancelEdit={() => setEditingRule(null)}
                      onSave={(edits) => handleReview(rule.id, rule.status, edits)}
                      onApprove={() => handleReview(rule.id, 'approved')}
                      onReject={() => handleReview(rule.id, 'rejected')}
                      onDelete={() => handleDeleteRule(rule.id)}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function RuleRow({ rule, editing, onStartEdit, onCancelEdit, onSave, onApprove, onReject, onDelete }) {
  const [editFields, setEditFields] = useState({
    source_entity: rule.source_entity,
    target_entity: rule.target_entity,
    description: rule.description,
    limit: rule.limit ?? '',
  });

  const statusColor = rule.status === 'approved' ? '#22c55e' : rule.status === 'rejected' ? '#ef4444' : '#f59e0b';
  const typeColor = RULE_TYPE_COLORS[rule.rule_type] || '#888';

  if (editing) {
    return (
      <tr className="rule-row editing">
        <td><span className="status-dot" style={{ background: statusColor }}></span></td>
        <td>
          <select value={rule.rule_type} onChange={(e) => setEditFields({ ...editFields, rule_type: e.target.value })}>
            {RULE_TYPES.map(rt => <option key={rt} value={rt}>{rt}</option>)}
          </select>
        </td>
        <td><input value={editFields.source_entity} onChange={(e) => setEditFields({ ...editFields, source_entity: e.target.value })} /></td>
        <td><input value={editFields.target_entity} onChange={(e) => setEditFields({ ...editFields, target_entity: e.target.value })} /></td>
        <td><input type="number" value={editFields.limit} onChange={(e) => setEditFields({ ...editFields, limit: e.target.value })} /></td>
        <td>{rule.confidence}</td>
        <td><input value={editFields.description} onChange={(e) => setEditFields({ ...editFields, description: e.target.value })} /></td>
        <td className="source-text">{rule.source_text?.substring(0, 60)}...</td>
        <td>
          <button className="save-btn" onClick={() => onSave(editFields)}>Save</button>
          <button className="cancel-btn" onClick={onCancelEdit}>Cancel</button>
        </td>
      </tr>
    );
  }

  return (
    <tr className="rule-row">
      <td>
        <span className="status-badge" style={{ background: statusColor + '22', color: statusColor, borderColor: statusColor }}>
          {rule.status}
        </span>
      </td>
      <td>
        <span className="rule-type-badge" style={{ background: typeColor + '22', color: typeColor, borderColor: typeColor }}>
          {rule.rule_type}
        </span>
      </td>
      <td className="mono">{rule.source_entity}</td>
      <td className="mono">{rule.target_entity}</td>
      <td>{rule.limit !== null && rule.limit !== undefined ? `$${rule.limit}` : '-'}</td>
      <td>
        <span className={`confidence-badge ${rule.confidence >= 0.8 ? 'high' : rule.confidence >= 0.5 ? 'medium' : 'low'}`}>
          {(rule.confidence * 100).toFixed(0)}%
        </span>
      </td>
      <td className="desc-cell">{rule.description}</td>
      <td className="source-text" title={rule.source_text}>{rule.source_text?.substring(0, 50)}...</td>
      <td className="actions-cell">
        {rule.status === 'pending' && (
          <>
            <button className="approve-btn" onClick={onApprove}>✓</button>
            <button className="reject-btn" onClick={onReject}>✗</button>
            <button className="edit-btn" onClick={onStartEdit}>✎</button>
          </>
        )}
        <button className="delete-btn" onClick={onDelete}>🗑</button>
      </td>
    </tr>
  );
}

export default RuleManager;
