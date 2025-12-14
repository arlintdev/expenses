import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './Settings.css';

function Settings({ apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [expenseContext, setExpenseContext] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const MAX_CONTEXT_LENGTH = 400;

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/settings`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch settings');
      }

      const data = await response.json();
      setExpenseContext(data.expense_context || '');
    } catch (error) {
      console.error('Error fetching settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage('');

    // Validate character limit
    if (expenseContext.length > MAX_CONTEXT_LENGTH) {
      setSaveMessage(`Context exceeds ${MAX_CONTEXT_LENGTH} character limit`);
      setSaving(false);
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/settings`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          expense_context: expenseContext,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save settings');
      }

      setSaveMessage('Settings saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      console.error('Error saving settings:', error);
      setSaveMessage('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-container">
        <div className="settings-loading">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="settings-container">
      <div className="settings-header">
        <h2>Settings</h2>
        <p className="settings-subtitle">Customize how expenses are processed</p>
      </div>

      <div className="settings-section">
        <label htmlFor="expense-context" className="settings-label">
          Expense Generation Context
        </label>
        <p className="settings-description">
          Add custom instructions for how Claude should format and categorize your expenses.
          For example: "Make the expenses sound official" or "Categorize by apartment: 123 Main St, 456 Oak Ave, 789 Pine Rd"
        </p>
        <textarea
          id="expense-context"
          className="settings-textarea"
          value={expenseContext}
          onChange={(e) => setExpenseContext(e.target.value)}
          placeholder="Enter custom context for expense generation..."
          rows={6}
          maxLength={MAX_CONTEXT_LENGTH}
        />
        <div className="settings-char-count">
          {expenseContext.length} / {MAX_CONTEXT_LENGTH} characters
        </div>
      </div>

      <div className="settings-actions">
        <button
          className="settings-save-button"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        {saveMessage && (
          <div className={`settings-message ${saveMessage.includes('success') ? 'success' : 'error'}`}>
            {saveMessage}
          </div>
        )}
      </div>

      <div className="settings-examples">
        <h3>Example Instructions:</h3>
        <ul>
          <li>"Format all expense descriptions in a professional, formal tone"</li>
          <li>"Categorize by property: Sunset Apartments, Downtown Loft, Beachside Villa"</li>
          <li>"Always include the unit number in the recipient field if mentioned"</li>
          <li>"Use categories: Maintenance, Utilities, Repairs, Supplies, Labor"</li>
        </ul>
      </div>
    </div>
  );
}

export default Settings;
