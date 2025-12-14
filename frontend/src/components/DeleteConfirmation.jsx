import './DeleteConfirmation.css';

function DeleteConfirmation({ isOpen, onConfirm, onCancel, itemName = 'this item', itemDetails }) {
  if (!isOpen) return null;

  return (
    <div className="delete-confirmation-overlay" onClick={onCancel}>
      <div className="delete-confirmation-content" onClick={(e) => e.stopPropagation()}>
        <div className="delete-confirmation-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
        </div>

        <h3>Delete {itemName}?</h3>

        {itemDetails && (
          <div className="delete-item-details">
            {itemDetails}
          </div>
        )}

        <p className="delete-warning">
          This action cannot be undone.
        </p>

        <div className="delete-actions">
          <button onClick={onCancel} className="delete-cancel-button">
            Cancel
          </button>
          <button onClick={onConfirm} className="delete-confirm-button">
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeleteConfirmation;
