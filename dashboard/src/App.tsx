import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Rules from './pages/Rules';
import Logs from './pages/Logs';
import Approvals from './pages/Approvals';
import Stats from './pages/Stats';
import Chat from './pages/Chat';
import type { Message } from './pages/Chat';
import { fetchHealth, getGroqConfig, setGroqConfig } from './api';
import './index.css';

function App() {
  const [health, setHealth] = useState<any>(null);
  const [showToolsModal, setShowToolsModal] = useState(false);
  const [groqConfigured, setGroqConfigured] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isConfiguring, setIsConfiguring] = useState(false);

  // Lifted Chat State
  const [chatMessages, setChatMessages] = useState<Message[]>(() => {
    const saved = sessionStorage.getItem('chat_messages');
    return saved ? JSON.parse(saved) : [];
  });
  const [chatLoading, setChatLoading] = useState(false);
  const [chatConversationId, setChatConversationId] = useState<string | undefined>(() => {
    return sessionStorage.getItem('chat_conversation_id') || undefined;
  });

  useEffect(() => {
    sessionStorage.setItem('chat_messages', JSON.stringify(chatMessages));
    if (chatConversationId) sessionStorage.setItem('chat_conversation_id', chatConversationId);
  }, [chatMessages, chatConversationId]);

  useEffect(() => {
    const load = async () => {
      try { 
        setHealth(await fetchHealth()); 
        const groqStatus = await getGroqConfig();
        setGroqConfigured(groqStatus.is_configured);
      } catch {}
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveGroqKey = async () => {
    try {
      const res = await setGroqConfig(apiKeyInput);
      setGroqConfigured(res.status === 'configured');
      setIsConfiguring(false);
      setApiKeyInput('');
    } catch (e) {
      console.error(e);
    }
  };

  const toolCount = health?.mcp_tools ?? '—';

  return (
    <BrowserRouter>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>⛨ GuardedAgent</h1>
          <p>AI Agent Policy Dashboard</p>
        </div>

        <div style={{ padding: '0 16px', marginBottom: '24px' }}>
          {!groqConfigured || isConfiguring ? (
            <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '8px', fontWeight: 600 }}>Configure Groq API</div>
              <input 
                type="password" 
                placeholder="gsk_..." 
                value={apiKeyInput}
                onChange={e => setApiKeyInput(e.target.value)}
                style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid var(--border)', background: 'var(--bg-dark)', color: '#fff', fontSize: '12px', marginBottom: '8px' }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary" onClick={handleSaveGroqKey} style={{ flex: 1, padding: '4px', fontSize: '12px' }}>Save Key</button>
                {isConfiguring && groqConfigured && (
                  <button className="btn btn-secondary" onClick={() => setIsConfiguring(false)} style={{ padding: '4px 8px', fontSize: '12px' }}>Cancel</button>
                )}
              </div>
            </div>
          ) : (
            <div className="llm-badge primary" style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: 'var(--cyan)', background: 'rgba(0, 255, 204, 0.05)' }} onClick={() => setIsConfiguring(true)}>
              <div><span className="dot" style={{ background: 'var(--cyan)' }} /> Groq Active</div>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </div>
          )}
        </div>

        <nav className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-chat">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            Agent Chat
          </NavLink>
          <NavLink to="/rules" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-rules">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Rules
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-logs">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>
            Logs
          </NavLink>
          <NavLink to="/approvals" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-approvals">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            Approvals
          </NavLink>
          <NavLink to="/stats" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-stats">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
            Stats
          </NavLink>
        </nav>

        <div className="api-reload-btn" onClick={async () => { try { await fetch('/api/mcp/reload', {method: 'POST'}); const h = await fetchHealth(); setHealth(h); } catch {} }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        </div>
        <div className="tool-count" onClick={() => setShowToolsModal(true)} style={{ cursor: 'pointer' }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
          {toolCount} MCP Tools
        </div>
      </aside>

      {showToolsModal && health?.mcp_tool_names && (
        <div className="modal-overlay" onClick={() => setShowToolsModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h3>Discovered MCP Tools</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 16 }}>Live from {health.mcp_servers} connected MCP server(s)</p>
            <div style={{ maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
              {health.mcp_tool_names.map((t: any, i: number) => (
                <div key={i} style={{ background: 'var(--bg-input)', padding: 12, borderRadius: 6 }}>
                  <div style={{ fontWeight: 600, color: 'var(--cyan)' }}>{t.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>{t.description}</div>
                </div>
              ))}
            </div>
            <div className="modal-actions" style={{ marginTop: 16, display: 'flex', gap: 12 }}>
              <button className="btn btn-secondary" onClick={async () => { try { await fetch('/api/mcp/reload', {method: 'POST'}); const h = await fetchHealth(); setHealth(h); } catch {} }}>Sync/Reload Servers</button>
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => setShowToolsModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Chat messages={chatMessages} setMessages={setChatMessages} loading={chatLoading} setLoading={setChatLoading} conversationId={chatConversationId} setConversationId={setChatConversationId} />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
