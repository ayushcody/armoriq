import { useState, useEffect, useRef } from 'react';
import { sendChat } from '../api';
import logo from '../assets/logo.png';

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  tokens?: { prompt: number; completion: number };
  tool_calls?: any[];
}

interface ChatProps {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  conversationId: string | undefined;
  setConversationId: React.Dispatch<React.SetStateAction<string | undefined>>;
}

export default function Chat({ messages, setMessages, loading, setLoading, conversationId, setConversationId }: ChatProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [messages, loading]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
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
        content: res.reply, 
        tokens: res.tokens,
        tool_calls: res.tool_calls 
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Error: Failed to communicate with the agent.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Live Agent Chat</h2>
        <p>Interact with the Guarded Agent and monitor policy enforcement in real-time.</p>
      </div>

      <div className="messages-list" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="empty-chat">
            <img src={logo} alt="ArmorIQ" style={{ width: '48px', height: '48px', opacity: 0.5, marginBottom: '16px' }} />
            <p>Ready to assist! Try asking "List our microservices" or "Search the web for Armoriq."</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message-bubble ${msg.role}`}>
            {msg.role === 'assistant' && (
              <img src={logo} alt="AI" className="agent-avatar" style={{ width: '24px', height: '24px', position: 'absolute', left: '-36px', top: '4px' }} />
            )}
            <div className="message-content">{msg.content}</div>
            
            {msg.tool_calls && msg.tool_calls.length > 0 && (
              <div className="tool-usage">
                {msg.tool_calls.map((tc, idx) => (
                  <div key={idx} className="tool-call-item">
                    <span className="tool-badge">Tool: {tc.tool_name}</span>
                    <span className={`server-badge ${tc.server_name}`}>Server: {tc.server_name}</span>
                    <span className={`decision-badge ${tc.policy_decision.toLowerCase()}`}>
                      {tc.policy_decision}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {msg.tokens && (
              <div className="token-usage">
                <span>Prompt: {msg.tokens.prompt}</span>
                <span style={{ marginLeft: 8 }}>Completion: {msg.tokens.completion}</span>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="message-bubble assistant loading">
            <img src={logo} alt="AI" className="agent-avatar" style={{ width: '24px', height: '24px', position: 'absolute', left: '-36px', top: '4px' }} />
            <div className="typing-indicator">
              <span></span><span></span><span></span>
            </div>
            <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Agent is thinking & discovering tools...
            </p>
          </div>
        )}
      </div>

      <form className="chat-input-area" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Type a command for the agent..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          {loading ? '...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
