import { useState } from 'react';
import { api } from '../api';

export default function LoginScreen({ onLogin }) {
  const [key, setKey] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!key.trim()) return;

    setLoading(true);
    setError(null);

    try {
      await api.health();
      await api.stats(key.trim());
      if (typeof onLogin === 'function') {
        onLogin(key.trim());
      } else {
        setError('Configuration error: Login handler missing');
      }
    } catch (err) {
      const msg = (err?.message || '').toString().toLowerCase();
      const isAuthError =
        msg.includes('401') ||
        msg.includes('unauthorized') ||
        msg.includes('forbidden') ||
        msg.includes('403');
      if (isAuthError) {
        setError('Invalid API key. Check your backend `RAG_API_KEY` value and what you entered.');
      } else {
        setError('Unable to connect to server. Ensure backend is running on port 8000.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-logo">Jio</div>
        <h1>Jio Support Agent</h1>
        <p>Enter your backend API key (`RAG_API_KEY`) to access the support dashboard</p>

        <div className="login-input-group">
          <label htmlFor="api-key-input">API key</label>
          <input
            id="api-key-input"
            className="login-input"
            type="password"
            placeholder="Paste your RAG_API_KEY…"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            disabled={loading}
            autoFocus
          />
        </div>

        <button
          id="login-submit"
          className="login-btn"
          type="submit"
          disabled={loading || !key.trim()}
        >
          {loading ? 'Connecting…' : 'Sign In'}
        </button>

        {error && <div className="login-error">{error}</div>}
      </form>
    </div>
  );
}
