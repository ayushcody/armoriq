import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Rules from './pages/Rules';
import Logs from './pages/Logs';
import Approvals from './pages/Approvals';
import Stats from './pages/Stats';
import { fetchHealth } from './api';
import './index.css';

function App() {
  const [health, setHealth] = useState<any>(null);
  const [showToolsModal, setShowToolsModal] = useState(false);

  useEffect(() => {
    const load = async () => {
      try { setHealth(await fetchHealth()); } catch {}
    };
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  const llmActive = health?.llm?.active;
  const toolCount = health?.mcp_tools ?? '—';

  return (
    <BrowserRouter>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>⛨ GuardedAgent</h1>
          <p>AI Agent Policy Dashboard</p>
        </div>

        {health && (
          <div className={`llm-badge ${llmActive === 'groq' ? 'fallback' : 'primary'}`}>
            <span className="dot" />
            {llmActive === 'groq' ? 'Groq' : 'LM Studio'} Active
          </div>
        )}

        <nav className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} id="nav-rules">
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
            <div className="modal-actions" style={{ marginTop: 16 }}>
              <button className="btn btn-primary" onClick={() => setShowToolsModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      <main className="main-content">
        <Routes>
          <Route path="/" element={<Rules />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/approvals" element={<Approvals />} />
          <Route path="/stats" element={<Stats />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;
