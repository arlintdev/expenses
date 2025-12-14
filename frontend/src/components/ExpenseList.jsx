import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { MdDescription, MdPerson, MdBuild, MdAccessTime, MdLocalOffer } from 'react-icons/md';
import TagInput from './TagInput';
import './ExpenseList.css';

function ExpenseList({ apiUrl, onDelete }) {
  const { getAuthHeader } = useAuth();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedMonth, setSelectedMonth] = useState('all');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedTags, setSelectedTags] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const [editingExpenseId, setEditingExpenseId] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [availableTags, setAvailableTags] = useState([]);
  const observer = useRef();
  const scrollContainerRef = useRef();
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
    // Update tags whenever expenses change
    const allTags = new Set();
    expenses.forEach(expense => {
      if (expense.tags && Array.isArray(expense.tags)) {
        expense.tags.forEach(tag => {
          if (tag && tag.trim()) {
            allTags.add(tag.trim());
          }
        });
      }
    });
    setAvailableTags([...allTags].sort());
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

  const startEditing = (expense) => {
    setEditingExpenseId(expense.id);
    setEditFormData({
      description: expense.description || '',
      recipient: expense.recipient || '',
      materials: expense.materials || '',
      hours: expense.hours || '',
      tags: expense.tags || [],
      amount: expense.amount || '',
      date: expense.date || ''
    });
  };

  const cancelEditing = () => {
    setEditingExpenseId(null);
    setEditFormData({});
  };

  const saveExpense = async (expenseId) => {
    try {
      console.log('Saving expense with data:', editFormData);
      const response = await fetch(`${apiUrl}/api/expenses/${expenseId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify(editFormData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Backend error:', errorText);
        throw new Error(`Failed to update expense: ${response.status} ${errorText}`);
      }

      const updatedExpense = await response.json();
      console.log('Updated expense received:', updatedExpense);

      // Use functional update to avoid stale closure
      setExpenses(prevExpenses =>
        prevExpenses.map(e => e.id === expenseId ? updatedExpense : e)
      );
      setEditingExpenseId(null);
      setEditFormData({});
    } catch (error) {
      console.error('Error updating expense:', error);
      alert(`Failed to update expense: ${error.message}`);
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
    const headers = ['Date', 'Title/Description', 'Who It\'s For', 'Materials', 'Hours', 'Tags', 'Amount'];
    const csvData = expenses.map(expense => [
      formatDateForCSV(expense.date),
      expense.description,
      expense.recipient,
      expense.materials || '',
      expense.hours ? expense.hours.toFixed(2) : '',
      (expense.tags || []).join('; '),
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

  // Client-side filtering based on category and search text
  const filteredExpenses = expenses.filter(expense => {
    // Tag filter - check if expense has at least one of the selected tags
    if (selectedTags.length > 0) {
      const expenseTags = expense.tags || [];
      const hasMatchingTag = selectedTags.some(selectedTag =>
        expenseTags.includes(selectedTag)
      );
      if (!hasMatchingTag) {
        return false;
      }
    }

    // Search text filter (searches across description, recipient, materials, and tags)
    if (searchText.trim()) {
      const searchLower = searchText.toLowerCase();
      const matchesDescription = expense.description?.toLowerCase().includes(searchLower);
      const matchesRecipient = expense.recipient?.toLowerCase().includes(searchLower);
      const matchesMaterials = expense.materials?.toLowerCase().includes(searchLower);
      const matchesTags = expense.tags?.some(tag => tag.toLowerCase().includes(searchLower));

      if (!matchesDescription && !matchesRecipient && !matchesMaterials && !matchesTags) {
        return false;
      }
    }

    return true;
  });

  const totalAmount = filteredExpenses.reduce((sum, expense) => sum + expense.amount, 0);

  const handleClearFilters = () => {
    setSelectedMonth('all');
    setSelectedYear(new Date().getFullYear());
    setSelectedTags([]);
    setSearchText('');
  };

  const hasActiveFilters = selectedMonth !== 'all' ||
    selectedYear !== new Date().getFullYear() ||
    selectedTags.length > 0 ||
    searchText.trim() !== '';

  return (
    <div className="expense-list">
      <div className="filters">
        <div className="filters-row">
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="filter-select"
          >
            {months.map(month => (
              <option key={month.value} value={month.value}>{month.label}</option>
            ))}
          </select>

          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="filter-select"
          >
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>

          <div className="tag-filter-section">
            <label>Filter by tags:</label>
            <TagInput
              tags={selectedTags}
              onChange={setSelectedTags}
              availableTags={availableTags}
              placeholder="Select tags to filter..."
            />
          </div>
        </div>

        <div className="filters-row">
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search expenses..."
            className="search-input"
          />

          {hasActiveFilters && (
            <button onClick={handleClearFilters} className="clear-filters-button">
              Clear Filters
            </button>
          )}
        </div>
      </div>

      <div className="summary">
        <div className="total-amount">
          Total: {formatAmount(totalAmount)}
        </div>
        <button className="export-csv-button" onClick={handleExportCSV}>
          Export CSV
        </button>
      </div>

      {filteredExpenses.length === 0 && !loading ? (
        <div className="empty-state">
          <p>No expenses found{hasActiveFilters ? ' matching your filters' : ''}.</p>
        </div>
      ) : (
        <div className="expenses-scroll-wrapper">
          <div className="expenses-scroll" ref={scrollContainerRef}>
          {/* Desktop Table View */}
          <div className="expenses-table-wrapper">
            <table className="expenses-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Recipient</th>
                  <th>Materials</th>
                  <th>Hours</th>
                  <th>Tags</th>
                  <th>Amount</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredExpenses.map((expense, index) => {
                  const isLast = index === expenses.length - 1;
                  const isEditing = editingExpenseId === expense.id;

                  return (
                    <tr
                      key={expense.id}
                      ref={isLast ? lastExpenseRef : null}
                      className={isEditing ? 'editing' : ''}
                    >
                      <td className="table-date">
                        {isEditing ? (
                          <input
                            type="date"
                            value={editFormData.date ? new Date(editFormData.date).toISOString().split('T')[0] : ''}
                            onChange={(e) => setEditFormData({...editFormData, date: e.target.value})}
                            className="table-input"
                          />
                        ) : (
                          formatDate(expense.date)
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="text"
                            value={editFormData.description}
                            onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                            className="table-input"
                            placeholder="Description"
                          />
                        ) : (
                          expense.description || '—'
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="text"
                            value={editFormData.recipient}
                            onChange={(e) => setEditFormData({...editFormData, recipient: e.target.value})}
                            className="table-input"
                            placeholder="Recipient"
                          />
                        ) : (
                          expense.recipient || '—'
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="text"
                            value={editFormData.materials}
                            onChange={(e) => setEditFormData({...editFormData, materials: e.target.value})}
                            className="table-input"
                            placeholder="Materials"
                          />
                        ) : (
                          expense.materials || '—'
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.25"
                            value={editFormData.hours}
                            onChange={(e) => setEditFormData({...editFormData, hours: parseFloat(e.target.value) || ''})}
                            className="table-input"
                            placeholder="Hours"
                          />
                        ) : (
                          expense.hours ? expense.hours.toFixed(2) : '—'
                        )}
                      </td>
                      <td>
                        {isEditing ? (
                          <TagInput
                            tags={editFormData.tags}
                            onChange={(newTags) => setEditFormData({...editFormData, tags: newTags})}
                            availableTags={availableTags}
                            placeholder="Add tags..."
                          />
                        ) : (
                          <div className="tags-display">
                            {expense.tags && expense.tags.length > 0 ? (
                              expense.tags.map((tag, idx) => (
                                <span key={idx} className="tag-badge">{tag}</span>
                              ))
                            ) : (
                              '—'
                            )}
                          </div>
                        )}
                      </td>
                      <td className="table-amount">
                        {isEditing ? (
                          <input
                            type="number"
                            step="0.01"
                            value={editFormData.amount}
                            onChange={(e) => setEditFormData({...editFormData, amount: parseFloat(e.target.value) || 0})}
                            className="table-amount-input"
                          />
                        ) : (
                          formatAmount(expense.amount)
                        )}
                      </td>
                      <td>
                        <div className="table-actions">
                          {isEditing ? (
                            <>
                              <button onClick={() => saveExpense(expense.id)} className="save-button">
                                Save
                              </button>
                              <button onClick={cancelEditing} className="cancel-button">
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button onClick={() => startEditing(expense)} className="edit-button">
                                Edit
                              </button>
                              <button
                                className="delete-button"
                                onClick={() => handleDelete(expense.id)}
                                disabled={deletingId === expense.id}
                              >
                                {deletingId === expense.id ? 'Deleting...' : 'Delete'}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          {filteredExpenses.map((expense, index) => {
            const isLast = index === expenses.length - 1;
            const isEditing = editingExpenseId === expense.id;

            return (
              <div
                key={expense.id}
                ref={isLast ? lastExpenseRef : null}
                className={`expense-card ${isEditing ? 'editing' : ''}`}
              >
                <div className="expense-header">
                  <div className="expense-date">
                    {isEditing ? (
                      <input
                        type="date"
                        value={editFormData.date ? new Date(editFormData.date).toISOString().split('T')[0] : ''}
                        onChange={(e) => setEditFormData({...editFormData, date: e.target.value})}
                        className="date-input"
                      />
                    ) : (
                      formatDate(expense.date)
                    )}
                  </div>
                  <div className="expense-amount">
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.01"
                        value={editFormData.amount}
                        onChange={(e) => setEditFormData({...editFormData, amount: parseFloat(e.target.value) || 0})}
                        className="amount-input"
                      />
                    ) : (
                      formatAmount(expense.amount)
                    )}
                  </div>
                </div>

                {/* Title/Description */}
                <div className="expense-field">
                  <MdDescription className="field-icon" title="Title/Description" />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editFormData.description}
                      onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                      className="field-input"
                      placeholder="Description"
                    />
                  ) : (
                    <span className="field-value" title={expense.description}>
                      {expense.description && expense.description.length > 50
                        ? expense.description.substring(0, 50) + '...'
                        : expense.description || '—'}
                    </span>
                  )}
                </div>

                {/* Who it's for */}
                <div className="expense-field">
                  <MdPerson className="field-icon" title="Who it's for" />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editFormData.recipient}
                      onChange={(e) => setEditFormData({...editFormData, recipient: e.target.value})}
                      className="field-input"
                      placeholder="Recipient"
                    />
                  ) : (
                    <span className="field-value">{expense.recipient || '—'}</span>
                  )}
                </div>

                {/* Materials */}
                <div className="expense-field">
                  <MdBuild className="field-icon" title="Materials" />
                  {isEditing ? (
                    <input
                      type="text"
                      value={editFormData.materials}
                      onChange={(e) => setEditFormData({...editFormData, materials: e.target.value})}
                      className="field-input"
                      placeholder="Materials"
                    />
                  ) : (
                    <span className="field-value">{expense.materials || '—'}</span>
                  )}
                </div>

                {/* Hours */}
                <div className="expense-field">
                  <MdAccessTime className="field-icon" title="Hours" />
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.25"
                      value={editFormData.hours}
                      onChange={(e) => setEditFormData({...editFormData, hours: parseFloat(e.target.value) || ''})}
                      className="field-input"
                      placeholder="Hours"
                    />
                  ) : (
                    <span className="field-value">
                      {expense.hours ? expense.hours.toFixed(2) : '—'}
                    </span>
                  )}
                </div>

                {/* Tags */}
                <div className="expense-field">
                  <MdLocalOffer className="field-icon" title="Tags" />
                  {isEditing ? (
                    <TagInput
                      tags={editFormData.tags}
                      onChange={(newTags) => setEditFormData({...editFormData, tags: newTags})}
                      availableTags={availableTags}
                      placeholder="Add tags..."
                    />
                  ) : (
                    <div className="tags-display">
                      {expense.tags && expense.tags.length > 0 ? (
                        expense.tags.map((tag, idx) => (
                          <span key={idx} className="tag-badge">{tag}</span>
                        ))
                      ) : (
                        <span className="field-value">—</span>
                      )}
                    </div>
                  )}
                </div>

                <div className="expense-actions">
                  {isEditing ? (
                    <>
                      <button onClick={() => saveExpense(expense.id)} className="save-button">
                        Save
                      </button>
                      <button onClick={cancelEditing} className="cancel-button">
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button onClick={() => startEditing(expense)} className="edit-button">
                        Edit
                      </button>
                      <button
                        className="delete-button"
                        onClick={() => handleDelete(expense.id)}
                        disabled={deletingId === expense.id}
                      >
                        {deletingId === expense.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
          {loading && (
            <div className="loading-more">Loading more...</div>
          )}
          </div>
        </div>
      )}
    </div>
  );
}

export default ExpenseList;
