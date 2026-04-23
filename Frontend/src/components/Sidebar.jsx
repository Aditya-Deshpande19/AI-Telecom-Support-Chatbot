export default function Sidebar({ conversations, activeConvId, onSelect, onNew, onDelete, isOpen }) {
  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">Jio</div>
          <span className="sidebar-brand-text">Support Agent</span>
        </div>
        <button id="new-conversation-btn" className="sidebar-new-btn" onClick={onNew}>
          <span>＋</span> New Conversation
        </button>
      </div>

      <div className="sidebar-list custom-scrollbar">
        {!Array.isArray(conversations) || conversations.length === 0 ? (
          <div className="sidebar-empty">
            No conversations yet.<br />Start a new one above!
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              role="button"
              tabIndex={0}
              aria-current={conv.id === activeConvId ? 'true' : undefined}
              className={`sidebar-item${conv.id === activeConvId ? ' active' : ''}`}
              onClick={() => onSelect(conv.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelect(conv.id);
                }
              }}
            >
              <span className="sidebar-item-icon">○</span>
              <span className="sidebar-item-label" title={conv.label || ''}>
                {conv.label ? (conv.label.length > 28 ? conv.label.slice(0, 28) + '…' : conv.label) : 'Untitled'}
              </span>
              <button
                className="sidebar-item-delete"
                title="Delete conversation"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
