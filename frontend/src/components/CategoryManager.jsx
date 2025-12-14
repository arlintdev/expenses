import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import './CategoryManager.css';

function CategoryManager({ apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [categoryStats, setCategoryStats] = useState({});

  useEffect(() => {
    fetchExpensesAndCategories();
  }, []);

  const fetchExpensesAndCategories = async () => {
    try {
      setLoading(true);
      // Fetch all expenses to extract categories
      const response = await fetch(`${apiUrl}/api/expenses?skip=0&limit=1000`, {
        headers: getAuthHeader(),
      });

      if (!response.ok) throw new Error('Failed to fetch expenses');

      const expenses = await response.json();

      // Extract unique categories and count their usage
      const categoryCount = {};
      expenses.forEach(expense => {
        if (expense.category && expense.category.trim()) {
          categoryCount[expense.category] = (categoryCount[expense.category] || 0) + 1;
        }
      });

      const uniqueCategories = Object.keys(categoryCount).sort();
      setCategories(uniqueCategories);
      setCategoryStats(categoryCount);
      setError(null);
    } catch (err) {
      console.error('Error fetching categories:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="category-manager">
      <h2>Your Categories</h2>
      <p className="subtitle">Categories are automatically created from your expenses. Click on an expense to add or change its category.</p>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)}>&times;</button>
        </div>
      )}

      <div className="categories-list">
        {loading ? (
          <div className="loading-spinner"></div>
        ) : categories.length === 0 ? (
          <div className="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 7V5a2 2 0 0 1 2-2h2" />
              <path d="M17 3h2a2 2 0 0 1 2 2v2" />
              <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
              <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
              <rect x="7" y="7" width="10" height="10" rx="1" />
            </svg>
            <p>No categories yet</p>
            <span>Add categories to your expenses to see them here</span>
          </div>
        ) : (
          <div className="category-grid">
            {categories.map((category) => (
              <div key={category} className="category-card">
                <div className="category-info">
                  <div className="category-name">{category}</div>
                  <div className="category-count">{categoryStats[category]} expense{categoryStats[category] !== 1 ? 's' : ''}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default CategoryManager;
