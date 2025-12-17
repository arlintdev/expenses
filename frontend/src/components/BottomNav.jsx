import { Link } from 'react-router-dom';
import './BottomNav.css';

function BottomNav({ activeTab, onMicClick }) {
  return (
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
        onClick={onMicClick}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" strokeWidth="2">
          <path d="M7 14l5-5 5 5z"/>
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
  );
}

export default BottomNav;
