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
    <div className="login-container">
      <div className="login-card">
        <div className="login-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
            <path d="M12.5 7H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
          </svg>
        </div>
        <h1>ExpenseTracker</h1>
        <p className="login-subtitle">Track your expenses with voice input</p>
        <div className="login-button-wrapper">
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
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap={false}
              theme="filled_blue"
              size="large"
              text="signin_with"
              shape="rectangular"
            />
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default Login;
