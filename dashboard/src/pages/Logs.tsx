import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchLogs, getWSUrl } from '../api';

export default function Logs() {
  const [logs, setLogs] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [filter, setFilter] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchLogs({ limit: 100 });
      setLogs(data);
    } catch {}
  }, []);

  useEffect(() => {
    load();
    const ws = new WebSocket(getWSUrl());
    ws.onmessage = (ev) => {
      const entry = JSON.parse(ev.data);
      setLogs(prev => [entry, ...prev].slice(0, 200));
    };
    ws.onerror = () => {};
    wsRef.current = ws;
    return () => { ws.close(); };
  }, [load]);

  const badgeClass = (action: string) => {
    if (action === 'ALLOW') return 'badge allow';
    if (action === 'BLOCK') return 'badge block';
    if (action === 'APPROVED') return 'badge approved';
    if (action === 'DENIED') return 'badge denied';
    return 'badge pending';
  };

  const filtered = filter
    ? logs.filter(l => l.policy_decision === filter)
    : logs;

  return (
    <div>
      <div className="page-header">
        <h2><span className="live-dot" /> Live Logs</h2>
        <p>Real-time tool call log stream via WebSocket</p>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['', 'ALLOW', 'BLOCK', 'APPROVED', 'DENIED'].map(f => (
          <button
            key={f}
            id={`filter-${f || 'all'}`}
            className="btn btn-sm"
            style={{
              background: filter === f ? 'var(--accent)' : 'var(--bg-card)',
              color: filter === f ? 'white' : 'var(--text-secondary)',
              border: `1px solid ${filter === f ? 'var(--accent)' : 'var(--border)'}`,
            }}
            onClick={() => setFilter(f)}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Tool</th>
                <th>Action</th>
                <th>Reason</th>
                <th>Conversation</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={5}><div className="empty-state"><p>No logs yet. Send a chat message to see activity.</p></div></td></tr>
              ) : filtered.map((log, i) => (
                <>
                  <tr key={i} className="log-row" onClick={() => setExpanded(expanded === i ? null : i)}>
                    <td style={{ fontSize: 12, fontFamily: 'monospace' }}>{log.timestamp?.slice(0, 19)}</td>
                    <td style={{ fontWeight: 500, color: 'var(--cyan)' }}>{log.tool_name}</td>
                    <td><span className={badgeClass(log.policy_decision)}>{log.policy_decision}</span></td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.reason || '—'}</td>
                    <td style={{ fontSize: 11, fontFamily: 'monospace' }}>{log.conversation_id?.slice(0, 8)}</td>
                  </tr>
                  {expanded === i && (
                    <tr key={`${i}-expand`}>
                      <td colSpan={5}>
                        <div className="log-expand">
                          {JSON.stringify(typeof log.arguments === 'string' ? JSON.parse(log.arguments) : log.arguments, null, 2)}
                          {log.result_preview && <><br /><br />Result: {log.result_preview}</>}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
