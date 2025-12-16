import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchWithTimeout, FetchTimeoutError } from '../utils/fetchWithTimeout';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [loading, setLoading] = useState(true);

  // Use relative URL when in production (served from same origin)
  // Use VITE_API_URL for development
  const API_URL = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    if (token && !user) {
      // Only fetch if we don't already have user data
      // This prevents redundant API call after login
      console.log('[Auth] Token exists but no user data, fetching user info');
      fetchUserInfo();
    } else if (token && user) {
      // We already have user data (from login), skip fetch
      console.log('[Auth] Token and user both exist, skipping redundant fetch');
      setLoading(false);
    } else {
      // No token, not logged in
      setLoading(false);
    }
  }, [token]);

  const fetchUserInfo = async () => {
    const startTime = performance.now();
    try {
      console.log('[Auth] fetchUserInfo START');

      const fetchStart = performance.now();
      const response = await fetchWithTimeout(
        `${API_URL}/api/auth/me`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
        10000 // 10 second timeout for auth check
      );

      const fetchDuration = performance.now() - fetchStart;
      console.log('[Auth] fetchUserInfo API call complete:', fetchDuration.toFixed(2), 'ms');

      if (response.ok) {
        const parseStart = performance.now();
        const userData = await response.json();
        const parseDuration = performance.now() - parseStart;
        console.log('[Auth] JSON parse complete:', parseDuration.toFixed(2), 'ms');

        setUser(userData);
        const totalDuration = performance.now() - startTime;
        console.log('[Auth] fetchUserInfo TOTAL:', totalDuration.toFixed(2), 'ms');
      } else {
        console.error('[Auth] Auth check failed with status:', response.status);
        logout();
      }
    } catch (error) {
      console.error('[Auth] fetchUserInfo failed:', error);
      if (error instanceof FetchTimeoutError) {
        console.error('[Auth] Timeout after', error.timeout, 'ms');
      }
      logout();
    } finally {
      setLoading(false);
    }
  };

  const loginWithGoogle = async (googleToken) => {
    const loginStartTime = performance.now();
    try {
      console.log('[Auth] loginWithGoogle START');

      const apiStart = performance.now();
      const response = await fetchWithTimeout(
        `${API_URL}/api/auth/google`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token: googleToken }),
        },
        45000 // 45 second timeout for login (allow time for database locks to resolve)
      );

      const apiDuration = performance.now() - apiStart;
      console.log('[Auth] /api/auth/google API call complete:', apiDuration.toFixed(2), 'ms');

      if (!response.ok) {
        const errorText = await response.text();
        console.error('[Auth] Login failed:', errorText);

        // Provide specific error message based on status code
        if (response.status === 504) {
          throw new Error('Google authentication service is not responding. Please try again.');
        }
        if (response.status === 503) {
          throw new Error('Database is temporarily unavailable. Please try again in a moment.');
        }
        throw new Error('Authentication failed. Please try again.');
      }

      const parseStart = performance.now();
      const data = await response.json();
      const parseDuration = performance.now() - parseStart;
      console.log('[Auth] JSON parse complete:', parseDuration.toFixed(2), 'ms');

      const stateStart = performance.now();
      // Store in localStorage first, then update state
      // React 18 auto-batches these state updates
      localStorage.setItem('access_token', data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      const stateDuration = performance.now() - stateStart;
      console.log('[Auth] State updates complete:', stateDuration.toFixed(2), 'ms');

      const totalLoginDuration = performance.now() - loginStartTime;
      console.log('[Auth] loginWithGoogle TOTAL:', totalLoginDuration.toFixed(2), 'ms');

      return data;
    } catch (error) {
      console.error('Login failed:', error);

      if (error instanceof FetchTimeoutError) {
        throw new Error('Login is taking longer than expected. Please check your connection and try again.');
      }

      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('access_token');
  };

  const getAuthHeader = () => {
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const value = {
    user,
    token,
    loading,
    loginWithGoogle,
    logout,
    getAuthHeader,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
