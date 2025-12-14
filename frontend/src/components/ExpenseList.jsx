import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import './ExpenseList.css';

function ExpenseList({ apiUrl, onDelete }) {
  const { getAuthHeader } = useAuth();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [deletingId, setDeletingId] = useState(null);
  const [editingCategoryId, setEditingCategoryId] = useState(null);
  const [editCategoryValue, setEditCategoryValue] = useState('');
  const [availableCategories, setAvailableCategories] = useState([]);
  const observer = useRef();
  const lastExpenseRef = useCallback(node => {
    if (loading) return;
    if (observer.current) observer.current.disconnect();
    observer.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        setPage(prevPage => prevPage + 1);
      }
    });
    if (node) observer.current.observe(node);
  }, [loading, hasMore]);

  useEffect(() => {
    setExpenses([]);
    setPage(0);
    setHasMore(true);
  }, [selectedMonth, selectedYear]);

  useEffect(() => {
    fetchExpenses();
  }, [page, selectedMonth, selectedYear]);

  useEffect(() => {
    // Update categories whenever expenses change
    const uniqueCategories = [...new Set(
      expenses
        .map(e => e.category)
        .filter(cat => cat && cat.trim())
    )].sort();
    setAvailableCategories(uniqueCategories);
  }, [expenses]);

  const fetchExpenses = async () => {
    if (loading) return;

    try {
      setLoading(true);
      let url = `${apiUrl}/api/expenses?skip=${page * 20}&limit=20`;

      if (selectedMonth !== 'all') {
        url += `&month=${selectedMonth}&year=${selectedYear}`;
      }

      const response = await fetch(url, {
        headers: getAuthHeader(),
      });
      if (!response.ok) throw new Error('Failed to fetch expenses');

      const data = await response.json();

      if (data.length === 0) {
        setHasMore(false);
      } else {
        setExpenses(prev => page === 0 ? data : [...prev, ...data]);
      }
    } catch (error) {
      console.error('Error fetching expenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (expenseId) => {
    if (!window.confirm('Are you sure you want to delete this expense?')) {
      return;
    }

    setDeletingId(expenseId);
    await onDelete(expenseId);
    setExpenses(expenses.filter(e => e.id !== expenseId));
    setDeletingId(null);
  };

  const startEditingCategory = (expense) => {
    setEditingCategoryId(expense.id);
    setEditCategoryValue(expense.category || '');
  };

  const cancelEditingCategory = () => {
    setEditingCategoryId(null);
    setEditCategoryValue('');
  };

  const saveCategory = async (expenseId) => {
    try {
      const response = await fetch(`${apiUrl}/api/expenses/${expenseId}/category?category=${encodeURIComponent(editCategoryValue)}`, {
        method: 'PATCH',
        headers: getAuthHeader(),
      });

      if (!response.ok) {
        throw new Error('Failed to update category');
      }

      const updatedExpense = await response.json();
      setExpenses(expenses.map(e => e.id === expenseId ? updatedExpense : e));
      setEditingCategoryId(null);
      setEditCategoryValue('');
    } catch (error) {
      console.error('Error updating category:', error);
      alert('Failed to update category');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateForCSV = (dateString) => {
    const date = new Date(dateString);
    return date.toISOString().split('T')[0];
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const handleExportCSV = () => {
    const headers = ['Date', 'Title/Description', 'Who It\'s For', 'Materials', 'Hours', 'Category', 'Amount'];
    const csvData = expenses.map(expense => [
      formatDateForCSV(expense.date),
      expense.description,
      expense.recipient,
      expense.materials || '',
      expense.hours ? expense.hours.toFixed(2) : '',
      expense.category || '',
      expense.amount.toFixed(2)
    ]);

    const csvContent = [
      headers.join(','),
      ...csvData.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `expenses_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const months = [
    { value: 'all', label: 'All Months' },
    { value: '1', label: 'January' },
    { value: '2', label: 'February' },
    { value: '3', label: 'March' },
    { value: '4', label: 'April' },
    { value: '5', label: 'May' },
    { value: '6', label: 'June' },
    { value: '7', label: 'July' },
    { value: '8', label: 'August' },
    { value: '9', label: 'September' },
    { value: '10', label: 'October' },
    { value: '11', label: 'November' },
    { value: '12', label: 'December' },
  ];

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);

  const totalAmount = expenses.reduce((sum, expense) => sum + expense.amount, 0);

  return (
    <div className="expense-list">
      <div className="filters">
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
          className="month-filter"
        >
          {months.map(month => (
            <option key={month.value} value={month.value}>{month.label}</option>
          ))}
        </select>

        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(parseInt(e.target.value))}
          className="year-filter"
        >
          {years.map(year => (
            <option key={year} value={year}>{year}</option>
          ))}
        </select>
      </div>

      <div className="summary">
        <div className="total-amount">
          Total: {formatAmount(totalAmount)}
        </div>
        <button className="export-csv-button" onClick={handleExportCSV}>
          Export CSV
        </button>
      </div>

      {expenses.length === 0 && !loading ? (
        <div className="empty-state">
          <p>No expenses found.</p>
        </div>
      ) : (
        <div className="expenses-scroll">
          {expenses.map((expense, index) => {
            const isLast = index === expenses.length - 1;
            return (
              <div
                key={expense.id}
                ref={isLast ? lastExpenseRef : null}
                className="expense-card"
              >
                <div className="expense-header">
                  <div className="expense-date">{formatDate(expense.date)}</div>
                  <div className="expense-amount">{formatAmount(expense.amount)}</div>
                </div>
                <div className="expense-description">{expense.description}</div>
                <div className="expense-details">
                  <div className="detail-row">
                    <span className="detail-label">For:</span>
                    <span>{expense.recipient}</span>
                  </div>
                  {expense.materials && (
                    <div className="detail-row">
                      <span className="detail-label">Materials:</span>
                      <span>{expense.materials}</span>
                    </div>
                  )}
                  {expense.hours && (
                    <div className="detail-row">
                      <span className="detail-label">Hours:</span>
                      <span>{expense.hours.toFixed(2)}</span>
                    </div>
                  )}
                  <div className="detail-row category-row">
                    <span className="detail-label">Category:</span>
                    {editingCategoryId === expense.id ? (
                      <div className="category-edit">
                        <input
                          type="text"
                          value={editCategoryValue}
                          onChange={(e) => setEditCategoryValue(e.target.value)}
                          list={`categories-${expense.id}`}
                          placeholder="Enter category"
                          className="category-input"
                          autoFocus
                        />
                        <datalist id={`categories-${expense.id}`}>
                          {availableCategories.map((cat, idx) => (
                            <option key={idx} value={cat} />
                          ))}
                        </datalist>
                        <button onClick={() => saveCategory(expense.id)} className="save-btn">
                          ✓
                        </button>
                        <button onClick={cancelEditingCategory} className="cancel-btn">
                          ✕
                        </button>
                      </div>
                    ) : (
                      <span className="category-value" onClick={() => startEditingCategory(expense)}>
                        {expense.category || <span className="category-placeholder">Click to add</span>}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  className="delete-button"
                  onClick={() => handleDelete(expense.id)}
                  disabled={deletingId === expense.id}
                >
                  {deletingId === expense.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            );
          })}
          {loading && (
            <div className="loading-more">Loading more...</div>
          )}
        </div>
      )}
    </div>
  );
}

export default ExpenseList;
