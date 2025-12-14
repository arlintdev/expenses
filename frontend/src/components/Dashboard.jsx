import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  AreaChart, Area, PieChart, Pie, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import './Dashboard.css';

function Dashboard({ apiUrl }) {
  const { getAuthHeader } = useAuth();
  const [loading, setLoading] = useState(true);
  const [summaryStats, setSummaryStats] = useState(null);
  const [tagData, setTagData] = useState([]);
  const [dateData, setDateData] = useState([]);
  const [recentExpenses, setRecentExpenses] = useState([]);
  const [dateRange, setDateRange] = useState('current_month');
  const [customDateFrom, setCustomDateFrom] = useState('');
  const [customDateTo, setCustomDateTo] = useState('');
  const [error, setError] = useState(null);

  // Color palette matching the app theme
  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0'];

  useEffect(() => {
    fetchDashboardData();
  }, [dateRange, customDateFrom, customDateTo]);

  const getDateRangeParams = () => {
    const today = new Date();
    let dateFrom, dateTo;

    switch (dateRange) {
      case 'current_month':
        dateFrom = new Date(today.getFullYear(), today.getMonth(), 1);
        dateTo = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        break;
      case 'last_month':
        dateFrom = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        dateTo = new Date(today.getFullYear(), today.getMonth(), 0);
        break;
      case 'last_3_months':
        dateFrom = new Date(today.getFullYear(), today.getMonth() - 3, 1);
        dateTo = today;
        break;
      case 'current_year':
        dateFrom = new Date(today.getFullYear(), 0, 1);
        dateTo = today;
        break;
      case 'custom':
        if (customDateFrom && customDateTo) {
          dateFrom = new Date(customDateFrom);
          dateTo = new Date(customDateTo);
        } else {
          return null;
        }
        break;
      default:
        return null;
    }

    return {
      date_from: dateFrom.toISOString().split('T')[0],
      date_to: dateTo.toISOString().split('T')[0]
    };
  };

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = getDateRangeParams();
      if (!params && dateRange === 'custom') {
        setLoading(false);
        return;
      }

      const queryString = params ? `?date_from=${params.date_from}&date_to=${params.date_to}` : '';

      // Fetch all data in parallel
      const [summaryRes, tagRes, dateRes, expensesRes] = await Promise.all([
        fetch(`${apiUrl}/api/analytics/summary${queryString}`, {
          headers: getAuthHeader(),
        }),
        fetch(`${apiUrl}/api/analytics/by-tag${queryString}`, {
          headers: getAuthHeader(),
        }),
        fetch(`${apiUrl}/api/analytics/by-date${queryString}`, {
          headers: getAuthHeader(),
        }),
        fetch(`${apiUrl}/api/expenses?limit=5`, {
          headers: getAuthHeader(),
        })
      ]);

      if (!summaryRes.ok || !tagRes.ok || !dateRes.ok || !expensesRes.ok) {
        throw new Error('Failed to fetch dashboard data');
      }

      const [summary, tags, dates, expenses] = await Promise.all([
        summaryRes.json(),
        tagRes.json(),
        dateRes.json(),
        expensesRes.json()
      ]);

      setSummaryStats(summary);
      setTagData(tags.data || []);
      setDateData(dates.data || []);
      setRecentExpenses(expenses);
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const formatDateFull = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip">
          <p className="tooltip-label">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="tooltip-value" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-loading">
          <div className="spinner"></div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-error">
          <p>Error loading dashboard: {error}</p>
          <button onClick={fetchDashboardData} className="retry-button">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <div className="date-range-selector">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="date-range-select"
          >
            <option value="current_month">Current Month</option>
            <option value="last_month">Last Month</option>
            <option value="last_3_months">Last 3 Months</option>
            <option value="current_year">Year to Date</option>
            <option value="custom">Custom Range</option>
          </select>

          {dateRange === 'custom' && (
            <div className="custom-date-inputs">
              <input
                type="date"
                value={customDateFrom}
                onChange={(e) => setCustomDateFrom(e.target.value)}
                className="date-input"
              />
              <span>to</span>
              <input
                type="date"
                value={customDateTo}
                onChange={(e) => setCustomDateTo(e.target.value)}
                className="date-input"
              />
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="1" x2="12" y2="23"></line>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
          </div>
          <div className="card-content">
            <div className="card-label">Total Spent</div>
            <div className="card-value">{formatCurrency(summaryStats?.total_amount || 0)}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
              <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
            </svg>
          </div>
          <div className="card-content">
            <div className="card-label">Total Expenses</div>
            <div className="card-value">{summaryStats?.expense_count || 0}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
          </div>
          <div className="card-content">
            <div className="card-label">Average Amount</div>
            <div className="card-value">{formatCurrency(summaryStats?.average_amount || 0)}</div>
          </div>
        </div>

        <div className="summary-card">
          <div className="card-icon" style={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)' }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
              <line x1="7" y1="7" x2="7.01" y2="7"></line>
            </svg>
          </div>
          <div className="card-content">
            <div className="card-label">Tags</div>
            <div className="card-value">{tagData.length}</div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="charts-grid">
        {/* Spending Trend */}
        <div className="chart-card chart-card-wide">
          <h3>Spending Trend</h3>
          {dateData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={dateData}>
                <defs>
                  <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#764ba2" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  stroke="#666"
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  tickFormatter={(value) => `$${value}`}
                  stroke="#666"
                  style={{ fontSize: '12px' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#667eea"
                  strokeWidth={3}
                  fill="url(#colorAmount)"
                  name="Amount"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">No data available for selected period</div>
          )}
        </div>

        {/* Spending by Tag - Pie Chart */}
        <div className="chart-card">
          <h3>Spending by Tag</h3>
          {tagData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tagData}
                  dataKey="total_amount"
                  nameKey="tag"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ tag, percentage }) => `${tag} (${percentage}%)`}
                  labelLine={true}
                >
                  {tagData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                  contentStyle={{
                    background: 'white',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    padding: '10px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">No tag data available</div>
          )}
        </div>

        {/* Spending by Tag - Bar Chart */}
        <div className="chart-card">
          <h3>Top Tags</h3>
          {tagData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tagData.slice(0, 6)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  dataKey="tag"
                  stroke="#666"
                  style={{ fontSize: '12px' }}
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis
                  tickFormatter={(value) => `$${value}`}
                  stroke="#666"
                  style={{ fontSize: '12px' }}
                />
                <Tooltip
                  formatter={(value) => formatCurrency(value)}
                  contentStyle={{
                    background: 'white',
                    border: '1px solid #e0e0e0',
                    borderRadius: '8px',
                    padding: '10px'
                  }}
                />
                <Bar dataKey="total_amount" name="Amount">
                  {tagData.slice(0, 6).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">No tag data available</div>
          )}
        </div>
      </div>

      {/* Recent Expenses */}
      <div className="recent-expenses-card">
        <h3>Recent Expenses</h3>
        {recentExpenses.length > 0 ? (
          <div className="recent-expenses-list">
            {recentExpenses.map((expense) => (
              <div key={expense.id} className="recent-expense-item">
                <div className="expense-item-left">
                  <div className="expense-item-description">{expense.description}</div>
                  <div className="expense-item-meta">
                    {formatDateFull(expense.date)}
                    {expense.tags && expense.tags.length > 0 && (
                      <span className="expense-item-tags">
                        {expense.tags.map((tag, idx) => (
                          <span key={idx} className="expense-tag">{tag}</span>
                        ))}
                      </span>
                    )}
                  </div>
                </div>
                <div className="expense-item-amount">{formatCurrency(expense.amount)}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="chart-empty">No recent expenses</div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
