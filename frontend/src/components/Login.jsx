import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import './Login.css';

const Login = () => {
  const { loginWithGoogle } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      setIsLoggingIn(true);
      setErrorMessage(null);
      await loginWithGoogle(credentialResponse.credential);
    } catch (error) {
      console.error('Login error:', error);
      setErrorMessage(error.message || 'An unexpected error occurred. Please try again.');
      setIsLoggingIn(false);
    }
  };

  const handleGoogleError = () => {
    console.error('Google login failed');
    setErrorMessage('Google login failed. Please try again.');
    setIsLoggingIn(false);
  };

  return (
    <div className="hero-container">
      <div className="hero-content">
        <div className="hero-text">
          <div className="hero-badge">ExpenseTracker</div>
          <h1 className="hero-title">Track Every Expense, Effortlessly</h1>
          <p className="hero-subtitle">
            Voice-powered expense tracking with AI assistance. Log expenses by voice,
            scan receipts, and get instant insights into your spending.
          </p>

          <div className="hero-cta">
            {errorMessage && (
              <div className="login-error">
                <svg className="error-icon" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
                <p>{errorMessage}</p>
                <button
                  className="retry-button"
                  onClick={() => setErrorMessage(null)}
                >
                  Try Again
                </button>
              </div>
            )}

            {isLoggingIn ? (
              <div className="login-loading">
                <div className="login-spinner"></div>
                <p>Authenticating with Google...</p>
                <p className="login-loading-hint">This may take a few moments</p>
              </div>
            ) : !errorMessage ? (
              <div className="google-login-wrapper">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  useOneTap={false}
                  theme="filled_blue"
                  size="large"
                  text="signin_with"
                  shape="rectangular"
                />
              </div>
            ) : null}
          </div>
        </div>

        <div className="hero-features">
          <div className="feature-card">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
            </div>
            <h3>Voice Input</h3>
            <p>Log expenses hands-free with voice commands</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
              </svg>
            </div>
            <h3>Real-time Analytics</h3>
            <p>Instant insights into your spending patterns</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 9h-2V5h2v6zm0 4h-2v-2h2v2z"/>
              </svg>
            </div>
            <h3>Smart Tagging</h3>
            <p>AI-powered categorization and organization</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 1.01L7 1c-1.1 0-2 .9-2 2v18c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V3c0-1.1-.9-1.99-2-1.99zM17 19H7V5h10v14z"/>
              </svg>
            </div>
            <h3>Works Anywhere</h3>
            <p>Access from any device, anytime</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
