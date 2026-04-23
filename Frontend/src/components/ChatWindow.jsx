import { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import { api } from '../api';
import MessageBubble from './MessageBubble';

const isAuthError = (err) => {
  if (!err) return false;
  return err.status === 401 || 
         err.response?.status === 401 || 
         (err.message && /\b401\b/i.test(err.message)) || 
         (err.message && err.message.toLowerCase().includes('unauthorized'));
};

export default function ChatWindow({ 
  apiKey, 
  conversationId, 
  messages, 
  onNewMessage,
  onToggleSidebar = () => {},
  onToggleStats = () => {},
  sidebarOpen = false,
  statsOpen = false
}) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [optimisticMsgs, setOptimisticMsgs] = useState([]);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, optimisticMsgs]);

  // Reset optimistic msgs when conversation changes
  useEffect(() => {
    setOptimisticMsgs([]);
    setError(null);
    setInput('');
  }, [conversationId]);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);
    setInput('');

    // Optimistically append the human message
    const humanMsg = { role: 'human', content: trimmed, id: 'opt_' + Date.now() };
    setOptimisticMsgs([humanMsg]);

    try {
      const data = await api.chat(apiKey, trimmed, conversationId);

      // Success: build AI message and report upstream
      const aiMsg = { role: 'ai', content: data.answer, id: 'ai_' + Date.now() };
      setOptimisticMsgs([]);
      onNewMessage(humanMsg, aiMsg, data.conversation_id);
    } catch (err) {
      // Remove the optimistic human message
      setOptimisticMsgs([]);
      if (isAuthError(err)) {
        setError('Invalid API key');
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const allMessages = [...messages, ...optimisticMsgs];

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <button 
          className="mobile-toggle-btn"
          aria-label="Toggle Sidebar"
          aria-expanded={sidebarOpen}
          onClick={onToggleSidebar}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="chat-header-title">
            {conversationId ? 'Active Conversation' : 'Jio Support Chat'}
          </div>
          <div className="chat-header-subtitle">
            {conversationId
              ? `Session: ${conversationId.slice(0, 8)}…`
              : 'Ask anything about Jio services'}
          </div>
        </div>
        <button 
          className="mobile-toggle-btn"
          aria-label="Toggle Stats"
          aria-expanded={statsOpen}
          onClick={onToggleStats}
        >
          <svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="4" y1="14" x2="4" y2="8" /><line x1="9" y1="14" x2="9" y2="4" /><line x1="14" y1="14" x2="14" y2="10" />
          </svg>
        </button>
      </div>

      <div className="chat-messages custom-scrollbar">
        {allMessages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon" style={{ fontSize: '48px', opacity: 0.25, color: 'var(--jio-navy)' }}>?</div>
            <div className="chat-empty-text">Welcome to Jio Support</div>
            <div className="chat-empty-hint">
              Ask about JioFiber internet, Wi‑Fi/router setup, recharge/plan details, SIM/network issues, and more.
              <br /><br />
              Need a human agent? Call 7000570005 or 1800-896-9999, or email jiofibercare@jio.com.
              <br />
              Visit www.jio.com/fiber for more support.
            </div>
          </div>
        ) : (
          allMessages.map((msg, idx) => (
            <MessageBubble key={msg.id || idx} role={msg.role} content={msg.content} />
          ))
        )}

        {loading && (
          <div className="message-row ai" aria-live="polite" aria-atomic="true">
            <div className="message-bubble ai">
              <div className="message-label ai">Jio AI</div>
              <span className="sr-only">AI is generating a response...</span>
              <div className="loading-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        {error && <div className="chat-error" role="alert">{error}</div>}
        <div className="chat-input-row">
          <input
            id="chat-input"
            className="chat-input"
            type="text"
            aria-label="Message input"
            placeholder="Type your question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button
            id="chat-send-btn"
            className="chat-send-btn"
            onClick={handleSend}
            disabled={loading || !input.trim()}
            title="Send message"
            aria-label="Send message"
          >
            <span aria-hidden="true">➤</span>
          </button>
        </div>
      </div>
    </div>
  );
}

ChatWindow.propTypes = {
  apiKey: PropTypes.string.isRequired,
  conversationId: PropTypes.string,
  messages: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      role: PropTypes.oneOf(['human', 'ai']).isRequired,
      content: PropTypes.string.isRequired
    })
  ).isRequired,
  onNewMessage: PropTypes.func.isRequired,
  onToggleSidebar: PropTypes.func,
  onToggleStats: PropTypes.func,
  sidebarOpen: PropTypes.bool,
  statsOpen: PropTypes.bool
};
