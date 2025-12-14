import { useState } from 'react';
import './App.css';
import ExpenseList from './components/ExpenseList';
import BottomNav from './components/BottomNav';
import RecordingModal from './components/RecordingModal';
import Login from './components/Login';
import CategoryManager from './components/CategoryManager';
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
      <header className="app-header">
        <h1>Expenses</h1>
        <div className="user-menu">
          {user.picture && <img src={user.picture} alt={user.name} className="user-avatar" />}
          <button onClick={logout} className="logout-button">Logout</button>
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
          <CategoryManager apiUrl={API_URL} />
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
