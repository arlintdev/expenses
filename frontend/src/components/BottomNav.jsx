import { useState } from 'react';
import { Link } from 'react-router-dom';
import { MdAttachMoney, MdDirectionsCar } from 'react-icons/md';
import './BottomNav.css';

function BottomNav({ activeTab, onExpenseClick, onMileageClick }) {
  const [showMenu, setShowMenu] = useState(false);

  const handleExpenseClick = () => {
    setShowMenu(false);
    onExpenseClick();
  };

  const handleMileageClick = () => {
    setShowMenu(false);
    onMileageClick();
  };

  return (
    <>
      {showMenu && (
        <>
          <div className="menu-overlay" onClick={() => setShowMenu(false)} />
          <div className="add-menu">
            <button className="menu-item expense-item" onClick={handleExpenseClick}>
              <MdAttachMoney size={24} />
              <span>Add Expense</span>
            </button>
            <button className="menu-item mileage-item" onClick={handleMileageClick}>
              <MdDirectionsCar size={24} />
              <span>Add Mileage</span>
            </button>
          </div>
        </>
      )}

      <nav className="bottom-nav">
        <Link
          to="/dashboard"
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          <span>Dashboard</span>
        </Link>

        <Link
          to="/expenses"
          className={`nav-item ${activeTab === 'expenses' ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span>Expenses</span>
        </Link>

        <button
          className="add-button"
          onClick={() => setShowMenu(!showMenu)}
        >
          <svg viewBox="0 0 24 24" fill="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </button>

        <Link
          to="/tags"
          className={`nav-item ${activeTab === 'tags' ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" />
            <line x1="7" y1="7" x2="7.01" y2="7" />
          </svg>
          <span>Tags</span>
        </Link>

        <Link
          to="/vehicles"
          className={`nav-item ${activeTab === 'vehicles' ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 17h14v-5l-3-3H8l-3 3v5z"/>
            <circle cx="7" cy="19" r="2"/>
            <circle cx="17" cy="19" r="2"/>
          </svg>
          <span>Vehicles</span>
        </Link>
      </nav>
    </>
  );
}

export default BottomNav;
