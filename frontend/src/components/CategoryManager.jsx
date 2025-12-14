import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './CategoryManager.css';

function TagManager({ apiUrl, onTagClick }) {
  const { getAuthHeader } = useAuth();
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagStats, setTagStats] = useState({});
  const [searchTerm, setSearchTerm] = useState('');

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

  const filteredTags = tags.filter(tag =>
    tag.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="category-manager">
      <h2>Your Tags</h2>
      <p className="subtitle">Tags are automatically created from your expenses. Click a tag to view all expenses with that tag.</p>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="tag-search">
        <input
          type="text"
          placeholder="Search tags..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="tag-search-input"
        />
      </div>

      <div className="categories-list">
        {loading ? (
          <div className="loading-spinner"></div>
        ) : filteredTags.length === 0 ? (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
              <line x1="7" y1="7" x2="7.01" y2="7" />
            </svg>
            <p>{tags.length === 0 ? 'No tags yet' : 'No tags found'}</p>
            <span>{tags.length === 0 ? 'Add tags to your expenses to see them here' : 'Try a different search term'}</span>
          </div>
        ) : (
          <div className="category-grid">
            {filteredTags.map((tag) => (
              <div
                key={tag}
                className="category-card clickable"
                onClick={() => onTagClick && onTagClick(tag)}
              >
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
