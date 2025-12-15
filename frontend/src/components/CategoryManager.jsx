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
  const [newTagName, setNewTagName] = useState('');
  const [addingTag, setAddingTag] = useState(false);
  const [deletingTags, setDeletingTags] = useState(new Set());
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [tagToDelete, setTagToDelete] = useState(null);

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

  const addNewTag = async () => {
    const tagName = newTagName.trim();
    if (!tagName || tags.includes(tagName)) {
      return;
    }

    try {
      setAddingTag(true);
      setError(null);

      // Create a placeholder expense with just the tag to add it to the system
      const response = await fetch(`${apiUrl}/api/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          name: tagName,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create tag');
      }

      // Add the tag to our local state
      setTags(prev => [...prev, tagName].sort());
      setTagStats(prev => ({ ...prev, [tagName]: 0 }));
      setNewTagName('');
    } catch (err) {
      console.error('Error creating tag:', err);
      setError(err.message);
    } finally {
      setAddingTag(false);
    }
  };

  const openDeleteModal = (tagName) => {
    setTagToDelete(tagName);
    setShowDeleteModal(true);
  };

  const closeDeleteModal = () => {
    setShowDeleteModal(false);
    setTagToDelete(null);
  };

  const confirmDeleteTag = async () => {
    if (!tagToDelete) return;

    try {
      setDeletingTags(prev => new Set([...prev, tagToDelete]));
      setError(null);
      setShowDeleteModal(false);

      const response = await fetch(`${apiUrl}/api/tags/${encodeURIComponent(tagToDelete)}`, {
        method: 'DELETE',
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error('Failed to delete tag');
      }

      // Remove the tag from our local state
      setTags(prev => prev.filter(tag => tag !== tagToDelete));
      setTagStats(prev => {
        const newStats = { ...prev };
        delete newStats[tagToDelete];
        return newStats;
      });
    } catch (err) {
      console.error('Error deleting tag:', err);
      setError(err.message);
    } finally {
      setDeletingTags(prev => {
        const newSet = new Set(prev);
        newSet.delete(tagToDelete);
        return newSet;
      });
      setTagToDelete(null);
    }
  };

  const filteredTags = tags.filter(tag =>
    tag.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="category-manager">
      <h2>Your Tags</h2>
      <p className="subtitle">Manage your expense tags. Create new ones or delete existing tags.</p>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="add-category-form">
        <input
          type="text"
          placeholder="Enter new tag name..."
          value={newTagName}
          onChange={(e) => setNewTagName(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && addNewTag()}
          disabled={addingTag}
        />
        <button
          onClick={addNewTag}
          disabled={addingTag || !newTagName.trim() || tags.includes(newTagName.trim())}
        >
          {addingTag ? 'Adding...' : 'Add Tag'}
        </button>
      </div>

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
            <div className="empty-state-content">
              <h3>{tags.length === 0 ? 'No tags yet' : 'No tags found'}</h3>
              <p>{tags.length === 0 ? 'Create your first tag using the form above, or add tags to your expenses.' : 'Try a different search term to find your tags.'}</p>
              {tags.length === 0 && (
                <div className="empty-state-tips">
                  <h4>💡 Tips for using tags:</h4>
                  <ul>
                    <li>Organize expenses by category (food, travel, work)</li>
                    <li>Track different projects or clients</li>
                    <li>Group by location or property</li>
                  </ul>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="category-grid">
            {filteredTags.map((tag) => (
              <div
                key={tag}
                className="category-card"
              >
                <div
                  className="category-info clickable"
                  onClick={() => onTagClick && onTagClick(tag)}
                >
                  <div className="category-name">{tag}</div>
                  <div className="category-count">{tagStats[tag]} expense{tagStats[tag] !== 1 ? 's' : ''}</div>
                </div>
                <div className="category-actions">
                  <button
                    className="delete-tag-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      openDeleteModal(tag);
                    }}
                    disabled={deletingTags.has(tag)}
                    title="Delete tag"
                  >
                    {deletingTags.has(tag) ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10"></circle>
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3,6 5,6 21,6"></polyline>
                        <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Delete Tag</h3>
            </div>
            <div className="modal-body">
              <p>Are you sure you want to delete the tag <strong>"{tagToDelete}"</strong>?</p>
              <p className="modal-warning">This will remove it from all expenses and cannot be undone.</p>
            </div>
            <div className="modal-actions">
              <button
                className="modal-button secondary"
                onClick={closeDeleteModal}
                disabled={deletingTags.has(tagToDelete)}
              >
                Cancel
              </button>
              <button
                className="modal-button danger"
                onClick={confirmDeleteTag}
                disabled={deletingTags.has(tagToDelete)}
              >
                {deletingTags.has(tagToDelete) ? 'Deleting...' : 'Delete Tag'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TagManager;
