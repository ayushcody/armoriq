import { useState, useEffect, useCallback } from 'react';
import { fetchRules, createRule, deleteRule, toggleRule, fetchHealth } from '../api';


export default function Rules() {
  const [rules, setRules] = useState<any[]>([]);
  const [availableTools, setAvailableTools] = useState<string[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [isCustom, setIsCustom] = useState(false);
  const [form, setForm] = useState({ name: '', type: 'BLOCK_TOOL' as string, tool_name: '', keywords: '', match_mode: 'any', field_path: '', rule: '', approval_timeout: 300, keywordCategory: 'custom' });

  const load = useCallback(async () => {
    try { 
      setRules(await fetchRules()); 
      const health = await fetchHealth();
      if (health?.mcp_tool_names) {
        setAvailableTools(health.mcp_tool_names.map((t: any) => t.name));
      }
    } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (id: string, enabled: boolean) => {
    await toggleRule(id, !enabled);
    load();
  };

  const handleDelete = async (id: string) => {
    await deleteRule(id);
    load();
  };

  const handleKeywordCategoryChange = (e: any) => {
    const val = e.target.value;
    let newKeywords = form.keywords;
    if (val === 'secrets') newKeywords = 'password, secret, api_key, token, credential';
    else if (val === 'pii') newKeywords = 'ssn, email, phone, credit_card, address';
    else if (val === 'custom') newKeywords = '';
    setForm({ ...form, keywordCategory: val, keywords: newKeywords });
  };

  const handleCreate = async () => {
    let config: any = {};
    if (form.type === 'BLOCK_TOOL' || form.type === 'REQUIRE_APPROVAL') {
      config.tool_name = form.tool_name;
      if (form.type === 'REQUIRE_APPROVAL') config.approval_timeout_seconds = form.approval_timeout;
    } else if (form.type === 'BLOCK_KEYWORD') {
      config.keywords = form.keywords.split(',').map(k => k.trim()).filter(Boolean);
      config.match_mode = form.match_mode;
    } else if (form.type === 'VALIDATE_INPUT') {
      config.tool_name = form.tool_name;
      config.field_path = form.field_path;
      config.rule = form.rule;
    }
    await createRule({ name: form.name, type: form.type, enabled: true, config });
    setShowModal(false);
    setForm({ name: '', type: 'BLOCK_TOOL', tool_name: '', keywords: '', match_mode: 'any', field_path: '', rule: '', approval_timeout: 300, keywordCategory: 'custom' });
    load();
  };

  const getTypeColor = (type: string) => {
    switch(type) {
      case 'BLOCK_TOOL': return { bg: 'rgba(255, 59, 48, 0.1)', text: '#ff3b30' };
      case 'REQUIRE_APPROVAL': return { bg: 'rgba(52, 199, 89, 0.1)', text: '#34c759' };
      case 'VALIDATE_INPUT': return { bg: 'rgba(0, 122, 255, 0.1)', text: '#007aff' };
      case 'BLOCK_KEYWORD': return { bg: 'rgba(255, 149, 0, 0.1)', text: '#ff9500' };
      default: return { bg: 'var(--accent-glow)', text: 'var(--accent)' };
    }
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Policy Rules</h2>
          <p>Create and manage guardrail rules that control agent behavior in real time</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button id="add-rule-btn" className="btn btn-primary" onClick={() => { setIsCustom(false); setShowModal(true); setForm({...form, type: 'BLOCK_TOOL', tool_name: availableTools[0] || '*'}); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14"/></svg>
            Add Tool Rule
          </button>
          <button className="btn" style={{ background: 'var(--bg-input)', color: 'var(--text-secondary)' }} onClick={() => { setIsCustom(true); setShowModal(true); setForm({...form, type: 'BLOCK_KEYWORD', tool_name: '*'}); }}>
            + Custom Rule
          </button>
        </div>
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Config</th>
                <th>Enabled</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.length === 0 ? (
                <tr><td colSpan={5}><div className="empty-state"><p>No rules configured. Add one to get started.</p></div></td></tr>
              ) : rules.map(r => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{r.name}</td>
                  <td><span className="badge" style={{ background: getTypeColor(r.type).bg, color: getTypeColor(r.type).text }}>{r.type}</span></td>
                  <td style={{ fontFamily: "'SF Mono', monospace", fontSize: 12 }}>{JSON.stringify(r.config)}</td>
                  <td>
                    <label className="toggle">
                      <input type="checkbox" checked={r.enabled} onChange={() => handleToggle(r.id, r.enabled)} />
                      <span className="slider" />
                    </label>
                  </td>
                  <td>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(r.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{isCustom ? 'Create Custom Rule' : 'Create Tool Rule'}</h3>
            
            <div className="form-group">
              <label>Rule Type</label>
              <select id="rule-type" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                {isCustom ? (
                  <>
                    <option value="BLOCK_KEYWORD">Block Keyword</option>
                    <option value="VALIDATE_INPUT">Validate Input</option>
                    <option value="BLOCK_TOOL">Block Tool Pattern</option>
                    <option value="REQUIRE_APPROVAL">Require Approval Pattern</option>
                  </>
                ) : (
                  <>
                    <option value="BLOCK_TOOL">Block Specific Tool</option>
                    <option value="REQUIRE_APPROVAL">Require Approval for Tool</option>
                  </>
                )}
              </select>
            </div>

            <div className="form-group">
              <label>Rule Name</label>
              <input type="text" id="rule-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="e.g. Stop specific action" />
            </div>

            {(form.type === 'BLOCK_TOOL' || form.type === 'REQUIRE_APPROVAL' || form.type === 'VALIDATE_INPUT') && (
              <div className="form-group">
                <label>Tool Name</label>
                {isCustom ? (
                  <input type="text" id="tool-name-pattern" value={form.tool_name} onChange={e => setForm({ ...form, tool_name: e.target.value })} placeholder="e.g. scale_service or run_*" />
                ) : (
                  <select id="tool-dropdown" value={form.tool_name} onChange={e => setForm({ ...form, tool_name: e.target.value })}>
                    <option value="*">All Tools (*)</option>
                    {availableTools.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                )}
              </div>
            )}

            {form.type === 'REQUIRE_APPROVAL' && (
              <div className="form-group">
                <label>Approval Timeout (seconds)</label>
                <input type="number" id="approval-timeout" value={form.approval_timeout} onChange={e => setForm({ ...form, approval_timeout: parseInt(e.target.value) || 300 })} />
              </div>
            )}

            {form.type === 'BLOCK_KEYWORD' && (
              <>
                <div className="form-group">
                  <label>Category Preset</label>
                  <select value={form.keywordCategory} onChange={handleKeywordCategoryChange}>
                    <option value="custom">Custom Keywords</option>
                    <option value="secrets">Secrets & Credentials</option>
                    <option value="pii">PII (Personal Data)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Keywords (comma separated)</label>
                  <input type="text" id="keywords" value={form.keywords} onChange={e => setForm({ ...form, keywords: e.target.value })} placeholder="e.g. password, secret, api_key" />
                </div>
                <div className="form-group">
                  <label>Match Mode</label>
                  <select id="match-mode" value={form.match_mode} onChange={e => setForm({ ...form, match_mode: e.target.value })}>
                    <option value="any">Any keyword</option>
                    <option value="all">All keywords</option>
                  </select>
                </div>
              </>
            )}

            {form.type === 'VALIDATE_INPUT' && (
              <>
                <div className="form-group">
                  <label>Field Path</label>
                  <input type="text" id="field-path" value={form.field_path} onChange={e => setForm({ ...form, field_path: e.target.value })} placeholder="e.g. replicas" />
                </div>
                <div className="form-group">
                  <label>Validation Rule</label>
                  <input type="text" id="validation-rule" value={form.rule} onChange={e => setForm({ ...form, rule: e.target.value })} placeholder='e.g. max_value:5 or allowlist:["a","b"]' />
                </div>
              </>
            )}

            <div className="modal-actions">
              <button className="btn" style={{ background: 'var(--bg-input)', color: 'var(--text-secondary)' }} onClick={() => setShowModal(false)}>Cancel</button>
              <button id="create-rule-submit" className="btn btn-primary" onClick={handleCreate} disabled={!form.name}>Create Rule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
