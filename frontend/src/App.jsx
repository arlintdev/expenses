import { useState } from 'react';
import './App.css';
import ExpenseList from './components/ExpenseList';
import BottomNav from './components/BottomNav';
import RecordingModal from './components/RecordingModal';
import Login from './components/Login';
import TagManager from './components/CategoryManager';
import Settings from './components/Settings';
import { useAuth } from './context/AuthContext';

// Use relative URL when in production (served from same origin)
// Use VITE_API_URL for development
const API_URL = import.meta.env.VITE_API_URL || '';

function App() {
  const { user, loading, logout, getAuthHeader } = useAuth();
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('expenses');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);

  const handleExpenseAdded = (newExpense) => {
    setRefreshTrigger(prev => prev + 1);
    setActiveTab('expenses');
  };

  const handleExpenseDeleted = async (expenseId) => {
    try {
      const response = await fetch(`${API_URL}/api/expenses/${expenseId}`, {
        method: 'DELETE',
        headers: getAuthHeader(),
      });
      if (!response.ok) {
        throw new Error('Failed to delete expense');
      }
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Error deleting expense:', err);
      throw err;
    }
  };

  if (loading) {
    return (
      <div className="app loading-screen">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user) {
    return <Login />;
  }

  return (
    <div className="app">
      {/* Desktop Sidebar Navigation */}
      <aside className="desktop-sidebar">
        <div className="sidebar-header">
          <div className="app-logo">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
              <path d="M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
            </svg>
          </div>
          <h2>ExpenseTracker</h2>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-link ${activeTab === 'expenses' ? 'active' : ''}`}
            onClick={() => setActiveTab('expenses')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>Expenses</span>
          </button>

          <button
            className={`nav-link ${activeTab === 'categories' ? 'active' : ''}`}
            onClick={() => setActiveTab('categories')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            <span>Categories</span>
          </button>

          <button
            className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" />
            </svg>
            <span>Settings</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            {user.picture && <img src={user.picture} alt={user.name} className="user-avatar-sidebar" />}
            <div className="user-details">
              <div className="user-name">{user.name}</div>
              <div className="user-email">{user.email}</div>
            </div>
          </div>
          <button onClick={logout} className="logout-button-sidebar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
            Logout
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="app-header mobile-header">
        <div className="mobile-logo">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
            <path d="M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
          </svg>
          <h1>Expenses</h1>
        </div>
        <div className="user-menu">
          <button
            className="user-avatar-button"
            onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
          >
            {user.picture && <img src={user.picture} alt={user.name} className="user-avatar" />}
          </button>

          {isProfileMenuOpen && (
            <>
              <div
                className="profile-menu-overlay"
                onClick={() => setIsProfileMenuOpen(false)}
              />
              <div className="profile-menu">
                <div className="profile-menu-header">
                  {user.picture && <img src={user.picture} alt={user.name} className="profile-menu-avatar" />}
                  <div className="profile-menu-info">
                    <div className="profile-menu-name">{user.name}</div>
                    <div className="profile-menu-email">{user.email}</div>
                  </div>
                </div>
                <div className="profile-menu-divider" />
                <button
                  className="profile-menu-item"
                  onClick={() => {
                    setActiveTab('settings');
                    setIsProfileMenuOpen(false);
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" />
                  </svg>
                  <span>Settings</span>
                </button>
                <button
                  className="profile-menu-item logout"
                  onClick={() => {
                    logout();
                    setIsProfileMenuOpen(false);
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  <span>Logout</span>
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      <main className="app-main">
        {error && (
          <div className="error-banner">
            <span>Error: {error}</span>
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        <div className={`tab-content ${activeTab === 'expenses' ? 'active' : ''}`}>
          <ExpenseList
            onDelete={handleExpenseDeleted}
            apiUrl={API_URL}
            key={refreshTrigger}
          />
        </div>

        <div className={`tab-content ${activeTab === 'categories' ? 'active' : ''}`}>
          <TagManager apiUrl={API_URL} />
        </div>

        <div className={`tab-content ${activeTab === 'settings' ? 'active' : ''}`}>
          <Settings apiUrl={API_URL} />
        </div>
      </main>

      <BottomNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onMicClick={() => setIsModalOpen(true)}
      />

      <RecordingModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onExpenseAdded={handleExpenseAdded}
        apiUrl={API_URL}
      />

      <button
        className="floating-mic-button"
        onClick={() => setIsModalOpen(true)}
        aria-label="Add expense"
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      </button>
    </div>
  );
}

export default App;
