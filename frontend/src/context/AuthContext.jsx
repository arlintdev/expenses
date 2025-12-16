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
    if (token) {
      fetchUserInfo();
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUserInfo = async () => {
    try {
      console.log('Fetching user info with token:', token ? 'Token exists' : 'No token');
      console.log('API URL:', API_URL);

      const response = await fetchWithTimeout(
        `${API_URL}/api/auth/me`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
        10000 // 10 second timeout for auth check
      );

      console.log('Auth check response status:', response.status);

      if (response.ok) {
        const userData = await response.json();
        console.log('User data fetched successfully');
        setUser(userData);
      } else {
        console.error('Auth check failed with status:', response.status);
        const errorText = await response.text();
        console.error('Error response:', errorText);
        logout();
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error);
      console.error('Error details:', error.message);
      if (error instanceof FetchTimeoutError) {
        console.error('Auth check timed out after', error.timeout, 'ms');
      }
      logout();
    } finally {
      setLoading(false);
    }
  };

  const loginWithGoogle = async (googleToken) => {
    try {
      console.log('Attempting Google login, API URL:', API_URL);

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

      console.log('Login response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Login failed:', errorText);

        // Provide specific error message based on status code
        if (response.status === 504) {
          throw new Error('Google authentication service is not responding. Please try again.');
        }
        if (response.status === 503) {
          throw new Error('Database is temporarily unavailable. Please try again in a moment.');
        }
        throw new Error('Authentication failed. Please try again.');
      }

      const data = await response.json();
      console.log('Login successful, storing token');
      setToken(data.access_token);
      setUser(data.user);
      localStorage.setItem('access_token', data.access_token);
      console.log('Token stored in localStorage');

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
