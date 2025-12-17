import { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Navigate, Link, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import DashboardRoute from './routes/DashboardRoute';
import ExpensesRoute from './routes/ExpensesRoute';
import ExpenseEditRoute from './routes/ExpenseEditRoute';
import TagsRoute from './routes/TagsRoute';
import VehiclesRoute from './routes/VehiclesRoute';
import MileageRoute from './routes/MileageRoute';
import SettingsRoute from './routes/SettingsRoute';
import AdminRoute from './routes/AdminRoute';
import BottomNav from './components/BottomNav';
import AddExpenseModal from './components/AddExpenseModal';
import AddMileageModal from './components/mileage/AddMileageModal';
import Login from './components/Login';
import { useAuth } from './context/AuthContext';
import { MdAttachMoney, MdDirectionsCar } from 'react-icons/md';

// Use relative URL when in production (served from same origin)
// Use VITE_API_URL for development
const API_URL = import.meta.env.VITE_API_URL || '';

function AppContent() {
  const { user, logout, getAuthHeader } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMileageModalOpen, setIsMileageModalOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [totalExpenses, setTotalExpenses] = useState(null);

  // Derive active tab from current route
  const activeTab = location.pathname.split('/')[1] || 'dashboard';

  useEffect(() => {
    // Fetch total expense count to show first expense prompt
    const fetchTotalCount = async () => {
      try {
        const response = await fetch(`${API_URL}/api/expenses?skip=0&limit=1`, {
          headers: getAuthHeader(),
        });
        if (response.ok) {
          const data = await response.json();
          setTotalExpenses(data.length);
        }
      } catch (err) {
        console.error('Error fetching expense count:', err);
      }
    };
    fetchTotalCount();
  }, [refreshTrigger, getAuthHeader]);

  const handleExpenseAdded = (newExpense) => {
    setIsModalOpen(false);
    setRefreshTrigger(prev => prev + 1);
    // Navigate to expenses if not already there
    if (!location.pathname.startsWith('/expenses')) {
      navigate('/expenses');
    }
  };

  const handleMileageAdded = (newLog) => {
    setIsMileageModalOpen(false);
    setRefreshTrigger(prev => prev + 1);
    // Navigate to mileage if not already there
    if (!location.pathname.startsWith('/mileage') && !location.pathname.startsWith('/vehicles')) {
      navigate('/mileage');
    }
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
          <Link
            to="/dashboard"
            className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span>Dashboard</span>
          </Link>

          <Link
            to="/expenses"
            className={`nav-link ${activeTab === 'expenses' ? 'active' : ''}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            <span>Expenses</span>
          </Link>

          <Link
            to="/tags"
            className={`nav-link ${activeTab === 'tags' ? 'active' : ''}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
            <span>Tags</span>
          </Link>

          <Link
            to="/vehicles"
            className={`nav-link ${activeTab === 'vehicles' ? 'active' : ''}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M5 17h14v-5l-3-3H8l-3 3v5z"/>
              <circle cx="7" cy="19" r="2"/>
              <circle cx="17" cy="19" r="2"/>
            </svg>
            <span>Vehicles</span>
          </Link>

          <Link
            to="/settings"
            className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24" />
            </svg>
            <span>Settings</span>
          </Link>

          {user?.is_admin && (
            <Link
              to="/admin"
              className={`nav-link ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => setActiveTab('admin')}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              <span>Admin</span>
            </Link>
          )}
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

        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardRoute apiUrl={API_URL} />} />
          <Route path="/expenses" element={<ExpensesRoute apiUrl={API_URL} onDelete={handleExpenseDeleted} refreshTrigger={refreshTrigger} />} />
          <Route path="/expenses/:id/edit" element={<ExpenseEditRoute apiUrl={API_URL} />} />
          <Route path="/tags" element={<TagsRoute apiUrl={API_URL} />} />
          <Route path="/categories" element={<Navigate to="/tags" replace />} />
          <Route path="/vehicles" element={<VehiclesRoute apiUrl={API_URL} />} />
          <Route path="/mileage" element={<MileageRoute apiUrl={API_URL} />} />
          <Route path="/settings" element={<SettingsRoute apiUrl={API_URL} />} />
          <Route path="/admin" element={<AdminRoute apiUrl={API_URL} />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>

      <BottomNav
        activeTab={activeTab}
        onExpenseClick={() => setIsModalOpen(true)}
        onMileageClick={() => setIsMileageModalOpen(true)}
      />

      <AddExpenseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onExpenseAdded={handleExpenseAdded}
        apiUrl={API_URL}
      />

      <AddMileageModal
        isOpen={isMileageModalOpen}
        onClose={() => setIsMileageModalOpen(false)}
        onMileageAdded={handleMileageAdded}
        apiUrl={API_URL}
      />

      {totalExpenses === 0 && (
        <div className="first-expense-prompt">
          Add your first expense here
        </div>
      )}

      <div className="floating-buttons-desktop">
        <button
          className="floating-action-button mileage-button"
          onClick={() => setIsMileageModalOpen(true)}
          aria-label="Add mileage"
          title="Add Mileage"
        >
          <MdDirectionsCar size={24} />
        </button>
        <button
          className={`floating-action-button expense-button ${totalExpenses === 0 ? 'pulse-animation' : ''}`}
          onClick={() => setIsModalOpen(true)}
          aria-label="Add expense"
          title="Add Expense"
        >
          <MdAttachMoney size={24} />
        </button>
      </div>
    </div>
  );
}

function App() {
  const { user, loading } = useAuth();

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
    <HashRouter>
      <AppContent />
    </HashRouter>
  );
}

export default App;
