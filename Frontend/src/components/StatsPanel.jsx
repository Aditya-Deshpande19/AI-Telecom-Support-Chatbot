import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api';

export default function StatsPanel({ apiKey, isOpen }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const controllerRef = useRef(null);

  useEffect(() => {
    return () => {
      isMounted.current = false;
      if (controllerRef.current) controllerRef.current.abort();
    };
  }, []);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (controllerRef.current) controllerRef.current.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const data = await api.stats(apiKey, controller.signal);
      if (isMounted.current) setStats(data);
    } catch (err) {
      if (isMounted.current) {
        const msg = err.name === 'AbortError' 
          ? 'Backend unreachable' 
          : 'Failed to load stats';
        setError(msg);
        setStats(null);
      }
    } finally {
      clearTimeout(timeout);
      if (isMounted.current) setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return (
    <aside className={`stats-panel ${isOpen ? 'open' : ''}`}>
      <div className="stats-header">
        <h2>System Stats</h2>
        <button
          id="stats-refresh-btn"
          className={`stats-refresh-btn${loading ? ' spinning' : ''}`}
          onClick={fetchStats}
          disabled={loading}
          title="Refresh stats"
        >
          ↻
        </button>
      </div>

      <div className="stats-body custom-scrollbar">
        {loading && (
          <div className="stats-loading">
            <div className="spinner"></div>
            <span>Loading stats…</span>
          </div>
        )}

        {error && !loading && (
          <div className="stats-error">
            <p style={{ marginBottom: '12px' }}>{error}</p>
            <button 
              className="stats-refresh-btn" 
              onClick={fetchStats}
              title="Retry"
            >
              ↻
            </button>
          </div>
        )}

        {stats && !loading && (
          <>
            <div className="stats-card">
              <div className="stats-card-label">Total Vectors</div>
              <div className="stats-card-value">
                {stats.total_vectors?.toLocaleString() ?? '—'}
              </div>
            </div>

            <div className="stats-card">
              <div className="stats-card-label">Collection</div>
              <div className="stats-card-value small">
                {stats.collection || '—'}
              </div>
            </div>

            <div className="stats-card">
              <div className="stats-card-label">Database Path</div>
              <div className="stats-card-value small">
                {stats.db_path || '—'}
              </div>
            </div>
          </>
        )}

        <div className="stats-card">
          <div className="stats-card-label">Status</div>
          <div className="stats-card-value small">
            <span className={`status-dot ${error ? 'offline' : (loading ? '' : 'online')}`}></span>
            {loading ? 'Checking…' : (error ? 'Disconnected' : 'Connected')}
          </div>
        </div>
      </div>
    </aside>
  );
}
