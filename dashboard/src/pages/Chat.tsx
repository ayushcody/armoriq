import { useState, useEffect, useRef } from 'react';
import { sendChat } from '../api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  tokens?: { prompt: number; completion: number };
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await sendChat(input, conversationId);
      setConversationId(res.conversation_id);
      const assistantMsg: Message = { 
        role: 'assistant', 
        content: res.reply || 'No response content.',
        tokens: res.tokens
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Could not connect to the agent.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container" style={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <div className="page-header">
        <h2>Live Agent Chat</h2>
        <p>Interact with the Guarded Agent and monitor policy enforcement in real-time</p>
      </div>

      <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: 0 }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.length === 0 && (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <div style={{ background: 'var(--bg-input)', padding: '20px', borderRadius: '12px', border: '1px dashed var(--border)', textAlign: 'center' }}>
                <p style={{ color: 'var(--text-secondary)' }}>Welcome to Armoriq Guarded Agent.</p>
                <p style={{ fontSize: '13px' }}>Try asking "List all services" or "Scale api-gateway to 3".</p>
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} style={{ 
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
              background: m.role === 'user' ? 'var(--accent)' : 'var(--bg-input)',
              color: m.role === 'user' ? '#000' : 'var(--text-primary)',
              padding: '12px 16px',
              borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              fontSize: '14px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              position: 'relative'
            }}>
              {m.content}
              {m.tokens && (
                <div style={{ fontSize: '10px', marginTop: '8px', opacity: 0.6, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '4px' }}>
                   Tokens: {m.tokens.prompt}P + {m.tokens.completion}C
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: 'flex-start', background: 'var(--bg-input)', padding: '12px 16px', borderRadius: '16px 16px 16px 4px', fontSize: '14px' }}>
              <span className="dot-flashing"></span>
            </div>
          )}
          <div ref={scrollRef} />
        </div>

        <div style={{ padding: '20px', borderTop: '1px solid var(--border)', display: 'flex', gap: '12px', background: 'rgba(255,255,255,0.02)' }}>
          <input 
            type="text" 
            placeholder="Type a command for the agent..." 
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--bg-dark)', color: '#fff' }}
          />
          <button className="btn btn-primary" onClick={handleSend} disabled={loading}>
            {loading ? 'Thinking...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
