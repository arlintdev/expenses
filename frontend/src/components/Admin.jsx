import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';
import './Admin.css';

function Admin({ apiUrl }) {
  const { getAuthHeader, user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total_users: 0, total_admins: 0 });
  const [elevating, setElevating] = useState(null);
  const [error, setError] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);

  // Redirect if not admin
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" />;
  }

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${apiUrl}/api/admin/users`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Admin access required');
        }
        throw new Error('Failed to fetch users');
      }

      const data = await response.json();
      setUsers(data.users);
      setStats({
        total_users: data.total_users,
        total_admins: data.total_admins
      });
    } catch (err) {
      setError(err.message);
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleElevateClick = (targetUser) => {
    setConfirmDialog(targetUser);
  };

  const confirmElevate = async () => {
    const targetUser = confirmDialog;
    setConfirmDialog(null);

    try {
      setElevating(targetUser.id);
      setError(null);

      const response = await fetch(`${apiUrl}/api/admin/users/${targetUser.id}/elevate`, {
        method: 'POST',
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to elevate user');
      }

      // Refresh user list
      await fetchUsers();
    } catch (err) {
      setError(err.message);
      console.error('Error elevating user:', err);
    } finally {
      setElevating(null);
    }
  };

  return (
    <div className="admin-container">
      <div className="admin-header">
        <h1>User Administration</h1>
        <p className="admin-subtitle">Manage users and administrator permissions</p>
      </div>

      {/* Stats Cards */}
      <div className="admin-stats">
        <div className="stat-card">
          <div className="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </div>
          <div className="stat-details">
            <div className="stat-value">{stats.total_users}</div>
            <div className="stat-label">Total Users</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon admin-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 15l-1.5 1.5L9 15l1.5-1.5L12 15z"/>
              <path d="M12 2a5 5 0 0 1 5 5c0 1.7-.85 3.2-2.15 4.1A9.96 9.96 0 0 1 22 20H2c0-4.42 2.87-8.17 6.85-9.5A5 5 0 0 1 7 7a5 5 0 0 1 5-5z"/>
            </svg>
          </div>
          <div className="stat-details">
            <div className="stat-value">{stats.total_admins}</div>
            <div className="stat-label">Administrators</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="admin-error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="admin-loading">
          <div className="spinner"></div>
          <p>Loading users...</p>
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="admin-table-container desktop-only">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Expenses</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="email-cell">{u.email}</td>
                    <td>{u.name || '—'}</td>
                    <td>
                      {u.is_admin ? (
                        <span className="role-badge admin">Administrator</span>
                      ) : (
                        <span className="role-badge user">User</span>
                      )}
                    </td>
                    <td className="count-cell">{u.expense_count}</td>
                    <td className="date-cell">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="actions-cell">
                      {!u.is_admin && u.id !== user.id && (
                        <button
                          onClick={() => handleElevateClick(u)}
                          disabled={elevating === u.id}
                          className="elevate-button"
                        >
                          {elevating === u.id ? 'Elevating...' : 'Make Admin'}
                        </button>
                      )}
                      {u.id === user.id && (
                        <span className="you-badge">You</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="admin-cards-container mobile-only">
            {users.map((u) => (
              <div key={u.id} className="user-card">
                <div className="user-card-header">
                  <div className="user-info">
                    <div className="user-email">{u.email}</div>
                    {u.name && <div className="user-name">{u.name}</div>}
                  </div>
                  {u.is_admin ? (
                    <span className="role-badge admin">Admin</span>
                  ) : (
                    <span className="role-badge user">User</span>
                  )}
                </div>

                <div className="user-card-stats">
                  <div className="user-stat">
                    <span className="stat-label">Expenses:</span>
                    <span className="stat-value">{u.expense_count}</span>
                  </div>
                  <div className="user-stat">
                    <span className="stat-label">Joined:</span>
                    <span className="stat-value">
                      {new Date(u.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {!u.is_admin && u.id !== user.id && (
                  <button
                    onClick={() => handleElevateClick(u)}
                    disabled={elevating === u.id}
                    className="elevate-button-mobile"
                  >
                    {elevating === u.id ? 'Elevating...' : 'Make Administrator'}
                  </button>
                )}
                {u.id === user.id && (
                  <div className="you-badge-mobile">This is you</div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Confirmation Dialog */}
      {confirmDialog && (
        <div className="modal-overlay" onClick={() => setConfirmDialog(null)}>
          <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Elevate User to Administrator?</h3>
            <p>
              You are about to grant administrator privileges to:
            </p>
            <div className="confirm-user-info">
              <strong>{confirmDialog.email}</strong>
              {confirmDialog.name && <span>{confirmDialog.name}</span>}
            </div>
            <p className="confirm-warning">
              Administrators can view all users and grant admin access to others.
              This action cannot be undone through the UI.
            </p>
            <div className="confirm-actions">
              <button
                onClick={() => setConfirmDialog(null)}
                className="cancel-button"
              >
                Cancel
              </button>
              <button
                onClick={confirmElevate}
                className="confirm-button"
              >
                Confirm Elevation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Admin;
