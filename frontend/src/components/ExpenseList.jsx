import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MdDescription, MdPerson, MdBuild, MdAccessTime, MdLocalOffer, MdCheckBox, MdDeleteOutline, MdAttachMoney, MdListAlt, MdTrendingUp, MdArrowUpward, MdArrowDownward } from 'react-icons/md';
import TagInput from './TagInput';
import DeleteConfirmation from './DeleteConfirmation';
import './ExpenseList.css';

function ExpenseList({
  apiUrl,
  onDelete,
  initialMonth = 'all',
  initialYear = new Date().getFullYear(),
  initialTags = [],
  initialSearch = '',
  refreshTrigger = 0
}) {
  const { getAuthHeader } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(0);
  const [selectedMonth, setSelectedMonth] = useState(initialMonth);
  const [selectedYear, setSelectedYear] = useState(initialYear);
  const [selectedTags, setSelectedTags] = useState(initialTags);
  const [searchText, setSearchText] = useState(initialSearch);
  const [deletingId, setDeletingId] = useState(null);
  const [availableTags, setAvailableTags] = useState([]);
  const [openMenuId, setOpenMenuId] = useState(null);
  const [sortBy, setSortBy] = useState('date_desc'); // date_desc, date_asc, created_desc, created_asc
  const [showFiltersModal, setShowFiltersModal] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState(null); // { id, description, amount }
  const [bulkSelectMode, setBulkSelectMode] = useState(false);
  const [selectedExpenses, setSelectedExpenses] = useState(new Set());
  const [bulkDeleteConfirmation, setBulkDeleteConfirmation] = useState(false);
  const scrollContainerRef = useRef();

  useEffect(() => {
    fetchExpenses();
  }, [selectedMonth, selectedYear, selectedTags, refreshTrigger]);

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
      let url = `${apiUrl}/api/expenses?skip=0&limit=10000`;

      if (selectedMonth !== 'all') {
        url += `&month=${selectedMonth}&year=${selectedYear}`;
      }

      if (selectedTags.length > 0) {
        url += `&tags=${selectedTags.join(',')}`;
      }

      const response = await fetch(url, {
        headers: getAuthHeader(),
      });
      if (!response.ok) throw new Error('Failed to fetch expenses');

      const data = await response.json();
      setExpenses(data);
    } catch (error) {
      console.error('Error fetching expenses:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirmation) return;

    setDeletingId(deleteConfirmation.id);
    setDeleteConfirmation(null);

    try {
      await onDelete(deleteConfirmation.id);
      setExpenses(expenses.filter(e => e.id !== deleteConfirmation.id));
    } catch (error) {
      console.error('Error deleting expense:', error);
    } finally {
      setDeletingId(null);
    }
  };

  const toggleBulkSelect = (expenseId) => {
    const newSelected = new Set(selectedExpenses);
    if (newSelected.has(expenseId)) {
      newSelected.delete(expenseId);
    } else {
      newSelected.add(expenseId);
    }
    setSelectedExpenses(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedExpenses.size === filteredExpenses.length && selectedExpenses.size > 0) {
      setSelectedExpenses(new Set());
    } else {
      setSelectedExpenses(new Set(filteredExpenses.map(e => e.id)));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedExpenses.size === 0) return;

    try {
      const response = await fetch(`${apiUrl}/api/expenses/bulk/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader(),
        },
        body: JSON.stringify({
          expense_ids: Array.from(selectedExpenses)
        })
      });

      if (!response.ok) {
        throw new Error('Failed to delete expenses');
      }

      const deletedIds = Array.from(selectedExpenses);
      setExpenses(expenses.filter(e => !deletedIds.includes(e.id)));
      setSelectedExpenses(new Set());
      setBulkSelectMode(false);
      setBulkDeleteConfirmation(false);
    } catch (error) {
      console.error('Error bulk deleting expenses:', error);
    }
  };

  // Sync filters with URL params
  useEffect(() => {
    const params = {};
    if (selectedMonth !== 'all') params.month = selectedMonth;
    if (selectedYear !== new Date().getFullYear()) params.year = selectedYear.toString();
    if (selectedTags.length > 0) params.tags = selectedTags.join(',');
    if (searchText) params.search = searchText;

    setSearchParams(params, { replace: true });
  }, [selectedMonth, selectedYear, selectedTags, searchText, setSearchParams]);

  // Close dropdown menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (openMenuId !== null) {
        setOpenMenuId(null);
      }
    };

    if (openMenuId !== null) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [openMenuId]);

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

  // Client-side search text filtering only (backend handles date and tag filtering)
  const filteredExpenses = expenses.filter(expense => {
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
  }).sort((a, b) => {
    // Apply sorting
    switch (sortBy) {
      case 'date_desc':
        return new Date(b.date) - new Date(a.date);
      case 'date_asc':
        return new Date(a.date) - new Date(b.date);
      case 'created_desc':
        return new Date(b.created_at) - new Date(a.created_at);
      case 'created_asc':
        return new Date(a.created_at) - new Date(b.created_at);
      default:
        return 0;
    }
  });

  // Helper to check if expense was created in last 5 minutes
  const isRecentlyAdded = (expense) => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
    const createdAt = new Date(expense.created_at);
    return createdAt > fiveMinutesAgo;
  };

  const totalAmount = filteredExpenses.reduce((sum, expense) => sum + expense.amount, 0);
  const expenseCount = filteredExpenses.length;
  const averageAmount = expenseCount > 0 ? totalAmount / expenseCount : 0;
  const maxAmount = expenseCount > 0 ? Math.max(...filteredExpenses.map(e => e.amount)) : 0;
  const minAmount = expenseCount > 0 ? Math.min(...filteredExpenses.map(e => e.amount)) : 0;
  const totalHours = filteredExpenses.reduce((sum, expense) => sum + (expense.hours || 0), 0);

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
      {/* Metrics Summary */}
      <div className="metrics-summary">
        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <MdAttachMoney size={28} />
          </div>
          <div className="card-content">
            <div className="card-label">Total</div>
            <div className="card-value">{formatAmount(totalAmount)}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <MdListAlt size={28} />
          </div>
          <div className="card-content">
            <div className="card-label">Count</div>
            <div className="card-value">{expenseCount}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
            <MdTrendingUp size={28} />
          </div>
          <div className="card-content">
            <div className="card-label">Average</div>
            <div className="card-value">{formatAmount(averageAmount)}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)' }}>
            <MdArrowUpward size={28} />
          </div>
          <div className="card-content">
            <div className="card-label">Highest</div>
            <div className="card-value">{formatAmount(maxAmount)}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)' }}>
            <MdArrowDownward size={28} />
          </div>
          <div className="card-content">
            <div className="card-label">Lowest</div>
            <div className="card-value">{formatAmount(minAmount)}</div>
          </div>
        </div>

        {totalHours > 0 && (
          <div className="summary-card">
            <div className="card-icon" style={{ background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)' }}>
              <MdAccessTime size={28} />
            </div>
            <div className="card-content">
              <div className="card-label">Hours</div>
              <div className="card-value">{totalHours.toFixed(1)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Compact Toolbar */}
      <div className="expense-toolbar">
        <button
          className={`filter-button ${hasActiveFilters ? 'active' : ''}`}
          onClick={() => setShowFiltersModal(true)}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="4" y1="21" x2="4" y2="14"></line>
            <line x1="4" y1="10" x2="4" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12" y2="3"></line>
            <line x1="20" y1="21" x2="20" y2="16"></line>
            <line x1="20" y1="12" x2="20" y2="3"></line>
            <line x1="1" y1="14" x2="7" y2="14"></line>
            <line x1="9" y1="8" x2="15" y2="8"></line>
            <line x1="17" y1="16" x2="23" y2="16"></line>
          </svg>
          {hasActiveFilters && <span className="filter-badge">{
            (selectedMonth !== 'all' ? 1 : 0) +
            (selectedYear !== new Date().getFullYear() ? 1 : 0) +
            (selectedTags.length > 0 ? 1 : 0)
          }</span>}
        </button>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="sort-select"
        >
          <option value="date_desc">Date (newest)</option>
          <option value="date_asc">Date (oldest)</option>
          <option value="created_desc">Recently added</option>
          <option value="created_asc">Oldest first</option>
        </select>

        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search..."
          className="toolbar-search"
        />

        <button className="export-button" onClick={handleExportCSV} title="Export CSV">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>

        {!bulkSelectMode && (
          <button className="bulk-select-button" onClick={() => setBulkSelectMode(true)} title="Bulk select">
            <MdCheckBox size={20} />
            Select
          </button>
        )}

        {bulkSelectMode && (
          <>
            <button
              className="cancel-select-button"
              onClick={() => {
                setBulkSelectMode(false);
                setSelectedExpenses(new Set());
              }}
              title="Cancel bulk select"
            >
              Cancel
            </button>
            {selectedExpenses.size > 0 && (
              <>
                <span className="selected-count">{selectedExpenses.size} selected</span>
                <button
                  className="bulk-delete-button"
                  onClick={() => setBulkDeleteConfirmation(true)}
                  title="Delete selected"
                >
                  <MdDeleteOutline size={20} />
                  Delete ({selectedExpenses.size})
                </button>
              </>
            )}
          </>
        )}
      </div>

      {bulkDeleteConfirmation && (
        <div className="bulk-delete-confirmation-overlay" onClick={() => setBulkDeleteConfirmation(false)}>
          <div className="bulk-delete-confirmation-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete {selectedExpenses.size} expense{selectedExpenses.size !== 1 ? 's' : ''}?</h3>
            <p>This action cannot be undone.</p>
            <div className="confirmation-actions">
              <button onClick={() => setBulkDeleteConfirmation(false)} className="cancel-button">Cancel</button>
              <button onClick={handleBulkDelete} className="delete-button">Delete</button>
            </div>
          </div>
        </div>
      )}

      {/* Filters Modal */}
      {showFiltersModal && (
        <div className="filters-modal-overlay" onClick={() => setShowFiltersModal(false)}>
          <div className="filters-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="filters-modal-header">
              <h3>Filters</h3>
              <button onClick={() => setShowFiltersModal(false)} className="modal-close">&times;</button>
            </div>

            <div className="filters-modal-body">
              <div className="filter-group">
                <label>Month</label>
                <select
                  value={selectedMonth}
                  onChange={(e) => setSelectedMonth(e.target.value)}
                  className="filter-select"
                >
                  {months.map(month => (
                    <option key={month.value} value={month.value}>{month.label}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Year</label>
                <select
                  value={selectedYear}
                  onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                  className="filter-select"
                >
                  {years.map(year => (
                    <option key={year} value={year}>{year}</option>
                  ))}
                </select>
              </div>

              <div className="filter-group">
                <label>Tags</label>
                <TagInput
                  tags={selectedTags}
                  onChange={setSelectedTags}
                  availableTags={availableTags}
                  placeholder="Select tags..."
                />
              </div>

              <div className="filters-modal-actions">
                <button onClick={handleClearFilters} className="clear-button">
                  Clear All
                </button>
                <button onClick={() => setShowFiltersModal(false)} className="apply-button">
                  Apply
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
                  {bulkSelectMode && (
                    <th className="select-column">
                      <input
                        type="checkbox"
                        checked={selectedExpenses.size === filteredExpenses.length && filteredExpenses.length > 0}
                        onChange={toggleSelectAll}
                        className="select-all-checkbox"
                      />
                    </th>
                  )}
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
                  const isEditing = false; // Inline editing disabled - use dedicated edit page

                  return (
                    <tr
                      key={expense.id}
                      className={`${isEditing ? 'editing' : ''} ${isRecentlyAdded(expense) ? 'recently-added' : ''} ${selectedExpenses.has(expense.id) ? 'selected' : ''}`}
                    >
                      {bulkSelectMode && (
                        <td className="select-column">
                          <input
                            type="checkbox"
                            checked={selectedExpenses.has(expense.id)}
                            onChange={() => toggleBulkSelect(expense.id)}
                            className="expense-checkbox"
                          />
                        </td>
                      )}
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
                              <button onClick={() => navigate(`/expenses/${expense.id}/edit`)} className="edit-button">
                                Edit
                              </button>
                              <button
                                className="delete-button"
                                onClick={() => setDeleteConfirmation({
                                  id: expense.id,
                                  description: expense.description,
                                  amount: expense.amount
                                })}
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
            return (
              <div
                key={expense.id}
                className={`expense-card ${isRecentlyAdded(expense) ? 'recently-added' : ''}`}
              >
                {/* Header with date and three-dot menu */}
                <div className="card-header-row">
                  <div className="expense-date">{formatDate(expense.date)}</div>
                  <div className="card-menu-wrapper">
                    <button
                      className="card-menu-button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(openMenuId === expense.id ? null : expense.id);
                      }}
                    >
                      ⋮
                    </button>
                    {openMenuId === expense.id && (
                      <div className="card-menu-dropdown">
                        <button
                          onClick={() => {
                            setOpenMenuId(null);
                            navigate(`/expenses/${expense.id}/edit`);
                          }}
                          className="menu-item"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => {
                            setOpenMenuId(null);
                            setDeleteConfirmation({
                              id: expense.id,
                              description: expense.description,
                              amount: expense.amount
                            });
                          }}
                          className="menu-item delete"
                          disabled={deletingId === expense.id}
                        >
                          {deletingId === expense.id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Two-column layout */}
                <div className="card-body">
                  {/* Left column - Description */}
                  <div className="card-left">
                    <div className="card-description" title={expense.description}>
                      {expense.description && expense.description.length > 50
                        ? expense.description.substring(0, 50) + '...'
                        : expense.description || '—'}
                    </div>
                  </div>

                  {/* Right column - Details */}
                  <div className="card-right">
                    <div className="card-detail">
                      <span className="detail-label">Amount:</span>
                      <span className="detail-value amount">{formatAmount(expense.amount)}</span>
                    </div>
                    {expense.recipient && (
                      <div className="card-detail">
                        <span className="detail-label">For:</span>
                        <span className="detail-value">{expense.recipient}</span>
                      </div>
                    )}
                    {expense.materials && (
                      <div className="card-detail">
                        <span className="detail-label">Materials:</span>
                        <span className="detail-value">{expense.materials}</span>
                      </div>
                    )}
                    {expense.hours && (
                      <div className="card-detail">
                        <span className="detail-label">Hours:</span>
                        <span className="detail-value">{expense.hours.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Tags at bottom */}
                {expense.tags && expense.tags.length > 0 && (
                  <div className="card-tags">
                    {expense.tags.map((tag, idx) => (
                      <span key={idx} className="tag-badge">{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {loading && (
            <div className="loading-more">Loading more...</div>
          )}
          </div>
        </div>
      )}

      <DeleteConfirmation
        isOpen={deleteConfirmation !== null}
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirmation(null)}
        itemName="Expense"
        itemDetails={deleteConfirmation && (
          <div>
            <div style={{ marginBottom: '0.5rem' }}>
              <strong>{deleteConfirmation.description}</strong>
            </div>
            <div style={{ color: '#667eea', fontWeight: 'bold', fontSize: '1.25rem' }}>
              ${parseFloat(deleteConfirmation.amount).toFixed(2)}
            </div>
          </div>
        )}
      />
    </div>
  );
}

export default ExpenseList;
