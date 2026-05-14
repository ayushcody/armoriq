import { useState, useEffect, useCallback } from 'react';
import { fetchStats } from '../api';

export default function Stats() {
  const [stats, setStats] = useState<any>(null);

  const load = useCallback(async () => {
    try { setStats(await fetchStats()); } catch {}
  }, []);

  useEffect(() => { load(); }, [load]);

  if (!stats) return <div className="empty-state"><p>Loading stats...</p></div>;

  const cards = [
    { label: 'Total Conversations', value: stats.total_conversations, color: 'var(--accent)' },
    { label: 'Total Tool Calls', value: stats.total_tool_calls, color: 'var(--cyan)' },
    { label: 'Blocked Calls', value: stats.blocked_calls, sub: `${stats.blocked_pct}% of total`, color: 'var(--red)' },
    { label: 'Prompt Tokens', value: stats.total_prompt_tokens?.toLocaleString(), color: 'var(--green)' },
    { label: 'Completion Tokens', value: stats.total_completion_tokens?.toLocaleString(), color: 'var(--amber)' },
    { label: 'Estimated Cost', value: `$${stats.estimated_cost}`, color: 'var(--cyan)' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Agent Statistics</h2>
        <p>Overview of agent activity, policy enforcement, and token usage</p>
      </div>

      <div className="stats-grid">
        {cards.map((c, i) => (
          <div key={i} className="stat-card">
            <div className="label">{c.label}</div>
            <div className="value" style={{ background: `linear-gradient(135deg, ${c.color}, var(--text-primary))`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {c.value}
            </div>
            {c.sub && <div className="sub">{c.sub}</div>}
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3 style={{ fontSize: 16, marginBottom: 16 }}>Policy Enforcement Rate</h3>
        <div style={{ background: 'var(--bg-input)', borderRadius: 8, height: 24, overflow: 'hidden' }}>
          <div style={{
            width: `${stats.blocked_pct}%`,
            height: '100%',
            background: 'linear-gradient(90deg, var(--red), #f97316)',
            borderRadius: 8,
            transition: 'width 0.5s ease',
            minWidth: stats.blocked_pct > 0 ? 20 : 0,
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
          <span>0%</span>
          <span style={{ color: 'var(--red)' }}>{stats.blocked_pct}% blocked</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  );
}
