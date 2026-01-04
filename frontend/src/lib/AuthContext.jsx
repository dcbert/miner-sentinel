import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState(null)

  // Verify session with backend
  const checkAuth = useCallback(async () => {
    try {
      const sessionToken = localStorage.getItem('sessionToken')
      if (!sessionToken) {
        setIsAuthenticated(false)
        setUser(null)
        setIsLoading(false)
        return false
      }

      // Verify session is still valid with backend
      const response = await api.get('/api/auth/user/')
      if (response.data.authenticated) {
        setIsAuthenticated(true)
        setUser(response.data.user)
        setIsLoading(false)
        return true
      } else {
        // Session expired or invalid
        localStorage.removeItem('sessionToken')
        setIsAuthenticated(false)
        setUser(null)
        setIsLoading(false)
        return false
      }
    } catch (error) {
      // 401 or network error - session invalid
      console.error('Auth check failed:', error)
      localStorage.removeItem('sessionToken')
      setIsAuthenticated(false)
      setUser(null)
      setIsLoading(false)
      return false
    }
  }, [])

  // Login function
  const login = useCallback(async (userData) => {
    localStorage.setItem('sessionToken', userData?.token || 'session-active')
    setIsAuthenticated(true)
    setUser(userData?.user || null)
  }, [])

  // Logout function
  const logout = useCallback(async () => {
    try {
      await api.post('/api/auth/logout/')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      localStorage.removeItem('sessionToken')
      setIsAuthenticated(false)
      setUser(null)
    }
  }, [])

  // Handle 401 errors from API
  const handleUnauthorized = useCallback(() => {
    localStorage.removeItem('sessionToken')
    setIsAuthenticated(false)
    setUser(null)
  }, [])

  // Check auth on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  // Expose handleUnauthorized globally for api interceptor
  useEffect(() => {
    window.__authLogout = handleUnauthorized
    return () => {
      delete window.__authLogout
    }
  }, [handleUnauthorized])

  const value = {
    isAuthenticated,
    isLoading,
    user,
    login,
    logout,
    checkAuth,
    handleUnauthorized,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
