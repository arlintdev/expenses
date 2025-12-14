import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import TagInput from './TagInput';
import './ExpenseEdit.css';

function ExpenseEdit({ apiUrl, expenseId, onSave, onCancel }) {
  const { getAuthHeader } = useAuth();
  const [expense, setExpense] = useState(null);
  const [formData, setFormData] = useState({
    description: '',
    recipient: '',
    materials: '',
    hours: '',
    tags: [],
    amount: '',
    date: ''
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [availableTags, setAvailableTags] = useState([]);

  useEffect(() => {
    fetchExpense();
    fetchAvailableTags();
  }, [expenseId]);

  const fetchExpense = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${apiUrl}/api/expenses/${expenseId}`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch expense');
      }

      const data = await response.json();
      setExpense(data);
      setFormData({
        description: data.description || '',
        recipient: data.recipient || '',
        materials: data.materials || '',
        hours: data.hours || '',
        tags: data.tags || [],
        amount: data.amount || '',
        date: data.date ? new Date(data.date).toISOString().split('T')[0] : ''
      });
    } catch (err) {
      console.error('Error fetching expense:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableTags = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/expenses?limit=1000`, {
        headers: getAuthHeader(),
      });
      const expenses = await response.json();
      const tags = new Set();
      expenses.forEach(e => e.tags?.forEach(t => tags.add(t)));
      setAvailableTags([...tags].sort());
    } catch (err) {
      console.error('Error fetching tags:', err);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const response = await fetch(`${apiUrl}/api/expenses/${expenseId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save expense');
      }

      onSave();
    } catch (err) {
      console.error('Error saving expense:', err);
      setError(err.message);
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="expense-edit-container">
        <div className="expense-edit-loading">
          <div className="spinner"></div>
          <p>Loading expense...</p>
        </div>
      </div>
    );
  }

  if (error && !expense) {
    return (
      <div className="expense-edit-container">
        <div className="expense-edit-error">
          <p>Error: {error}</p>
          <button onClick={onCancel} className="back-button">Go Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="expense-edit-container">
      <div className="expense-edit-header">
        <button onClick={onCancel} className="back-button">
          ← Back
        </button>
        <h2>Edit Expense</h2>
      </div>

      <div className="expense-edit-form">
        <div className="form-group">
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            value={formData.date}
            onChange={(e) => setFormData({ ...formData, date: e.target.value })}
            className="form-input"
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Description</label>
          <input
            id="description"
            type="text"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="form-input"
            placeholder="What is this expense for?"
          />
        </div>

        <div className="form-group">
          <label htmlFor="recipient">Recipient</label>
          <input
            id="recipient"
            type="text"
            value={formData.recipient}
            onChange={(e) => setFormData({ ...formData, recipient: e.target.value })}
            className="form-input"
            placeholder="Who is this for?"
          />
        </div>

        <div className="form-group">
          <label htmlFor="amount">Amount</label>
          <input
            id="amount"
            type="number"
            step="0.01"
            value={formData.amount}
            onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || '' })}
            className="form-input"
            placeholder="0.00"
          />
        </div>

        <div className="form-group">
          <label htmlFor="materials">Materials (Optional)</label>
          <input
            id="materials"
            type="text"
            value={formData.materials}
            onChange={(e) => setFormData({ ...formData, materials: e.target.value })}
            className="form-input"
            placeholder="Materials used"
          />
        </div>

        <div className="form-group">
          <label htmlFor="hours">Hours (Optional)</label>
          <input
            id="hours"
            type="number"
            step="0.25"
            value={formData.hours}
            onChange={(e) => setFormData({ ...formData, hours: parseFloat(e.target.value) || '' })}
            className="form-input"
            placeholder="0.00"
          />
        </div>

        <div className="form-group">
          <label htmlFor="tags">Tags</label>
          <TagInput
            tags={formData.tags}
            onChange={(newTags) => setFormData({ ...formData, tags: newTags })}
            availableTags={availableTags}
            placeholder="Add tags..."
          />
        </div>

        {error && (
          <div className="form-error">
            {error}
          </div>
        )}

        <div className="form-actions">
          <button
            onClick={onCancel}
            className="cancel-button"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="save-button"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ExpenseEdit;
