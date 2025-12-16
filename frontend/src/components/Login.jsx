import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import './Login.css';

const Login = () => {
  const { loginWithGoogle } = useAuth();
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const handleGoogleSuccess = async (credentialResponse) => {
    const handleStart = performance.now();
    console.log('[Login] Google OAuth success, starting login flow');

    try {
      setIsLoggingIn(true);
      setErrorMessage(null);

      const loginStart = performance.now();
      await loginWithGoogle(credentialResponse.credential);
      const loginDuration = performance.now() - loginStart;

      const totalDuration = performance.now() - handleStart;
      console.log('[Login] Complete login flow duration:', totalDuration.toFixed(2), 'ms');
    } catch (error) {
      console.error('[Login] Login error:', error);
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

          <div className="upload-methods">
            <div className="method-item">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
              </svg>
              <span>Voice</span>
            </div>
            <div className="method-item">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/>
              </svg>
              <span>Photo</span>
            </div>
            <div className="method-item">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
              <span>Screenshot</span>
            </div>
            <div className="method-item">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span>CSV</span>
            </div>
            <div className="method-item">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L21 7"/>
              </svg>
              <span>Manual</span>
            </div>
          </div>

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
              <div style={{ display: 'none' }}>
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  useOneTap={false}
                />
              </div>
            ) : null}

            {!isLoggingIn && !errorMessage && (
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={handleGoogleError}
                useOneTap={false}
                render={(renderProps) => (
                  <button
                    onClick={renderProps.onClick}
                    disabled={renderProps.disabled}
                    className="custom-google-button"
                  >
                    <svg viewBox="0 0 24 24" className="google-icon">
                      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    <span>Continue with Google</span>
                  </button>
                )}
              />
            )}
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
