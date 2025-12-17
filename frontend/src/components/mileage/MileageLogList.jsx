import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { MdDirectionsCar, MdDelete, MdLocalOffer, MdCalendarToday } from 'react-icons/md';
import './MileageLogList.css';

function MileageLogList({ apiUrl, initialVehicleId, initialDateFrom, initialDateTo, refreshTrigger }) {
  const { getAuthHeader } = useAuth();
  const [logs, setLogs] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [vehicleFilter, setVehicleFilter] = useState(initialVehicleId || '');
  const [dateFrom, setDateFrom] = useState(initialDateFrom || '');
  const [dateTo, setDateTo] = useState(initialDateTo || '');
  const [summary, setSummary] = useState({ totalBusinessMiles: 0, totalDeduction: 0 });

  useEffect(() => {
    fetchVehicles();
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [vehicleFilter, dateFrom, dateTo, refreshTrigger]);

  const fetchVehicles = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/vehicles`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setVehicles(data);
      }
    } catch (error) {
      console.error('Error fetching vehicles:', error);
    }
  };

  const fetchLogs = async () => {
    try {
      setLoading(true);
      let url = `${apiUrl}/api/mileage-logs?limit=100`;
      if (vehicleFilter) url += `&vehicle_id=${vehicleFilter}`;
      if (dateFrom) url += `&date_from=${dateFrom}`;
      if (dateTo) url += `&date_to=${dateTo}`;

      const response = await fetch(url, {
        headers: getAuthHeader()
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data);

        // Calculate summary
        const totalBusinessMiles = data.reduce((sum, log) => sum + log.business_miles, 0);
        const totalDeduction = data.reduce((sum, log) => sum + log.deductible_amount, 0);
        setSummary({ totalBusinessMiles, totalDeduction });
      }
    } catch (error) {
      console.error('Error fetching mileage logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (logId) => {
    if (!confirm('Delete this mileage log? The linked expense will also be deleted.')) return;

    try {
      const response = await fetch(`${apiUrl}/api/mileage-logs/${logId}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });

      if (response.ok) {
        fetchLogs();
      }
    } catch (error) {
      console.error('Error deleting mileage log:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getVehicleName = (vehicleId) => {
    const vehicle = vehicles.find(v => v.id === vehicleId);
    return vehicle ? vehicle.name : 'Unknown Vehicle';
  };

  if (loading && logs.length === 0) {
    return <div className="loading">Loading mileage logs...</div>;
  }

  return (
    <div className="mileage-log-list">
      <div className="list-header">
        <h2>Mileage Logs</h2>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Vehicle</label>
          <select value={vehicleFilter} onChange={(e) => setVehicleFilter(e.target.value)}>
            <option value="">All Vehicles</option>
            {vehicles.map(vehicle => (
              <option key={vehicle.id} value={vehicle.id}>
                {vehicle.name}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>From</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>To</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
        {(vehicleFilter || dateFrom || dateTo) && (
          <button
            className="clear-filters"
            onClick={() => {
              setVehicleFilter('');
              setDateFrom('');
              setDateTo('');
            }}
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="summary-value">{summary.totalBusinessMiles.toLocaleString()}</div>
          <div className="summary-label">Business Miles</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">${summary.totalDeduction.toFixed(2)}</div>
          <div className="summary-label">Total Deduction</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{logs.length}</div>
          <div className="summary-label">Total Trips</div>
        </div>
      </div>

      {logs.length === 0 ? (
        <div className="empty-state">
          <MdDirectionsCar size={64} />
          <p>No mileage logs found. Start tracking your business trips!</p>
        </div>
      ) : (
        <div className="logs-list">
          {logs.map(log => (
            <div key={log.id} className="log-card">
              <div className="log-header">
                <div className="log-date">
                  <MdCalendarToday size={16} />
                  {formatDate(log.date)}
                </div>
                <div className="log-vehicle">
                  <MdDirectionsCar size={16} />
                  {getVehicleName(log.vehicle_id)}
                </div>
              </div>

              <div className="log-purpose">{log.purpose}</div>

              <div className="log-details">
                <div className="detail-item">
                  <span className="detail-label">Odometer:</span>
                  <span className="detail-value">
                    {log.odometer_start.toLocaleString()} → {log.odometer_end.toLocaleString()}
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Business Miles:</span>
                  <span className="detail-value highlight">
                    {log.business_miles.toLocaleString()} mi
                  </span>
                </div>
                {log.personal_miles > 0 && (
                  <div className="detail-item">
                    <span className="detail-label">Personal Miles:</span>
                    <span className="detail-value">{log.personal_miles.toLocaleString()} mi</span>
                  </div>
                )}
                <div className="detail-item">
                  <span className="detail-label">IRS Rate:</span>
                  <span className="detail-value">${log.irs_rate}/mi</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Deduction:</span>
                  <span className="detail-value deduction">${log.deductible_amount.toFixed(2)}</span>
                </div>
              </div>

              {log.tags && log.tags.length > 0 && (
                <div className="log-tags">
                  <MdLocalOffer size={14} />
                  {log.tags.map((tag, index) => (
                    <span key={index} className="tag">{tag}</span>
                  ))}
                </div>
              )}

              <div className="log-actions">
                {log.linked_expense_id && (
                  <span className="expense-link" title="Linked expense created">
                    Expense Created
                  </span>
                )}
                <button
                  className="delete-button"
                  onClick={() => handleDelete(log.id)}
                  title="Delete log and linked expense"
                >
                  <MdDelete size={18} />
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default MileageLogList;
