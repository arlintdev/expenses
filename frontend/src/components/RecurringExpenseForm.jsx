import { useState, useEffect } from 'react';
import TagInput from './TagInput';
import './RecurringExpenseForm.css';

const MONTHS = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' }
];

function RecurringExpenseForm({ onSubmit, availableTags, isSubmitting, error }) {
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;

  const [formData, setFormData] = useState({
    description: '',
    recipient: '',
    materials: '',
    hours: '',
    amount: '',
    tags: [],
    start_month: currentMonth,
    start_year: currentYear,
    end_month: currentMonth,
    end_year: currentYear,
    day_of_month: 1
  });

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'amount' || name === 'hours' ? (value ? parseFloat(value) : '') :
              name === 'day_of_month' || name === 'start_month' || name === 'end_month' ||
              name === 'start_year' || name === 'end_year' ? (value ? parseInt(value) : '') :
              value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.description || !formData.recipient || !formData.amount) {
      return;
    }
    onSubmit(formData);
  };

  const yearRange = Array.from({ length: 11 }, (_, i) => currentYear - 1 + i);

  return (
    <form className="recurring-expense-form" onSubmit={handleSubmit}>
      <div className="confirmation-fields">
        <div className="confirmation-field">
          <label>Description *</label>
          <input
            type="text"
            name="description"
            placeholder="What is the recurring expense for?"
            value={formData.description}
            onChange={handleInputChange}
            className="confirmation-input"
            required
          />
        </div>

        <div className="confirmation-field">
          <label>Amount *</label>
          <input
            type="number"
            name="amount"
            step="0.01"
            placeholder="0.00"
            value={formData.amount}
            onChange={handleInputChange}
            className="confirmation-input"
            required
          />
        </div>

        <div className="confirmation-field">
          <label>Recipient *</label>
          <input
            type="text"
            name="recipient"
            placeholder="Who do you pay?"
            value={formData.recipient}
            onChange={handleInputChange}
            className="confirmation-input"
            required
          />
        </div>

        <div className="confirmation-field">
          <label>Materials (Optional)</label>
          <input
            type="text"
            name="materials"
            placeholder="What materials or items..."
            value={formData.materials}
            onChange={handleInputChange}
            className="confirmation-input"
          />
        </div>

        <div className="confirmation-field">
          <label>Hours (Optional)</label>
          <input
            type="number"
            name="hours"
            step="0.25"
            placeholder="0.00"
            value={formData.hours}
            onChange={handleInputChange}
            className="confirmation-input"
          />
        </div>

        <div className="confirmation-field">
          <label>Day of Month</label>
          <select
            name="day_of_month"
            value={formData.day_of_month}
            onChange={handleInputChange}
            className="confirmation-input"
          >
            {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
              <option key={day} value={day}>{day}</option>
            ))}
          </select>
        </div>

        <div className="recurring-months-section">
          <h3>Recurring Period</h3>
          <div className="recurring-months-grid">
            <div className="recurring-month-group">
              <label>Start Month</label>
              <select
                name="start_month"
                value={formData.start_month}
                onChange={handleInputChange}
                className="confirmation-input"
              >
                {MONTHS.map(month => (
                  <option key={month.value} value={month.value}>{month.label}</option>
                ))}
              </select>
              <select
                name="start_year"
                value={formData.start_year}
                onChange={handleInputChange}
                className="confirmation-input"
              >
                {yearRange.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div className="recurring-month-group">
              <label>End Month</label>
              <select
                name="end_month"
                value={formData.end_month}
                onChange={handleInputChange}
                className="confirmation-input"
              >
                {MONTHS.map(month => (
                  <option key={month.value} value={month.value}>{month.label}</option>
                ))}
              </select>
              <select
                name="end_year"
                value={formData.end_year}
                onChange={handleInputChange}
                className="confirmation-input"
              >
                {yearRange.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="confirmation-field">
          <label>Tags</label>
          <TagInput
            tags={formData.tags}
            onChange={(tags) => setFormData(prev => ({ ...prev, tags }))}
            availableTags={availableTags}
            placeholder="Add tags..."
          />
        </div>
      </div>

      {error && (
        <div className="modal-error">{error}</div>
      )}

      <div className="recurring-form-actions">
        <button
          type="submit"
          className="confirm-button"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Creating...' : 'Create Recurring Expense'}
        </button>
      </div>
    </form>
  );
}

export default RecurringExpenseForm;
