import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './CategoryManager.css';

function TagManager({ apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagStats, setTagStats] = useState({});

  useEffect(() => {
    fetchExpensesAndTags();
  }, []);

  const fetchExpensesAndTags = async () => {
    try {
      setLoading(true);
      // Fetch all expenses to extract tags
      const response = await fetch(`${apiUrl}/api/expenses?skip=0&limit=1000`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) throw new Error('Failed to fetch expenses');

      const expenses = await response.json();

      // Extract unique tags and count their usage
      const tagCount = {};
      expenses.forEach(expense => {
        if (expense.tags && Array.isArray(expense.tags)) {
          expense.tags.forEach(tag => {
            if (tag && tag.trim()) {
              tagCount[tag] = (tagCount[tag] || 0) + 1;
            }
          });
        }
      });

      const uniqueTags = Object.keys(tagCount).sort();
      setTags(uniqueTags);
      setTagStats(tagCount);
      setError(null);
    } catch (err) {
      console.error('Error fetching tags:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="category-manager">
      <h2>Your Tags</h2>
      <p className="subtitle">Tags are automatically created from your expenses. You can add or change tags when editing an expense.</p>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="categories-list">
        {loading ? (
          <div className="loading-spinner"></div>
        ) : tags.length === 0 ? (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
            <p>No tags yet</p>
            <span>Add tags to your expenses to see them here</span>
          </div>
        ) : (
          <div className="category-grid">
            {tags.map((tag) => (
              <div key={tag} className="category-card">
                <div className="category-info">
                  <div className="category-name">{tag}</div>
                  <div className="category-count">{tagStats[tag]} expense{tagStats[tag] !== 1 ? 's' : ''}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default TagManager;
