import { useState, useCallback, useRef } from 'react';
import './App.css';
import LoginScreen from './components/LoginScreen';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import StatsPanel from './components/StatsPanel';
import { api } from './api';

function App() {
  const [apiKey, setApiKey] = useState(null);              // null = not logged in
  const [conversations, setConversations] = useState([]);  // [{ id, label }]
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);             // [{ role, content }]
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);

  const latestRequestedConvRef = useRef(null);

  // Called by ChatWindow after a successful API response
  const onNewMessage = useCallback((humanMsg, aiMsg, convId) => {
    setConversations(prev => {
      const exists = prev.some(c => c.id === convId);
      if (!exists) {
        const label = `Conversation ${prev.length + 1}`;
        return [...prev, { id: convId, label }];
      }
      return prev;
    });
    
    // Guard against stale updates: don't append if the user already switched away
    if (activeConvId === null || activeConvId === convId) {
      setActiveConvId(convId);
      setMessages(prev => [...prev, humanMsg, aiMsg]);
    }
  }, [activeConvId]);

  // Start a new conversation
  const handleNewConversation = useCallback(() => {
    setActiveConvId(null);
    latestRequestedConvRef.current = null;
    setMessages([]);
    setSidebarOpen(false);
  }, []);

  // Select a conversation and load its history
  const handleSelectConversation = useCallback(async (id) => {
    setActiveConvId(id);
    latestRequestedConvRef.current = id;
    setSidebarOpen(false);
    try {
      const data = await api.getConversation(apiKey, id);
      // Only apply if the user hasn't switched to another conversation
      if (latestRequestedConvRef.current === id) {
        setMessages(data.messages || []);
      }
    } catch {
      if (latestRequestedConvRef.current === id) {
        setMessages([]);
      }
    }
  }, [apiKey]);

  // Delete a conversation (Pessimistic)
  const handleDeleteConversation = useCallback(async (id) => {
    try {
      await api.deleteConversation(apiKey, id);
      // Only mutate state if API succeeds
      setConversations(prev => prev.filter(c => c.id !== id));
      if (activeConvId === id) {
        setActiveConvId(null);
        latestRequestedConvRef.current = null;
        setMessages([]);
      }
    } catch {
      // API failed: show alert, don't remove from list
      alert("Failed to delete conversation. Please try again.");
    }
  }, [apiKey, activeConvId]);

  // Not logged in — show login screen
  if (!apiKey) {
    return <LoginScreen onLogin={setApiKey} />;
  }

  // Logged in — three-panel layout
  return (
    <div className="app-layout">
      {(sidebarOpen || statsOpen) && (
        <div 
          className="mobile-overlay" 
          onClick={() => { setSidebarOpen(false); setStatsOpen(false); }} 
        />
      )}
      <Sidebar
        isOpen={sidebarOpen}
        conversations={conversations}
        activeConvId={activeConvId}
        onSelect={handleSelectConversation}
        onNew={handleNewConversation}
        onDelete={handleDeleteConversation}
      />
      <ChatWindow
        apiKey={apiKey}
        conversationId={activeConvId}
        messages={messages}
        onNewMessage={onNewMessage}
        onToggleSidebar={() => setSidebarOpen(prev => !prev)}
        onToggleStats={() => setStatsOpen(prev => !prev)}
        sidebarOpen={sidebarOpen}
        statsOpen={statsOpen}
      />
      <StatsPanel apiKey={apiKey} isOpen={statsOpen} />
    </div>
  );
}

export default App;
