import axios from 'axios';


const api = axios.create({
  baseURL: process.env.NODE_ENV === 'development'?'http://localhost:8000':window.location.origin,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  xsrfCookieName: 'csrftoken',  // Django's default CSRF cookie name
  xsrfHeaderName: 'X-CSRFToken',  // Django's default CSRF header name
})

// Helper function to get CSRF token from cookie
function getCookie(name) {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add CSRF token to request headers for POST, PUT, DELETE, PATCH
    if (['post', 'put', 'delete', 'patch'].includes(config.method.toLowerCase())) {
      const csrfToken = getCookie('csrftoken')
      if (csrfToken) {
        config.headers['X-CSRFToken'] = csrfToken
      }
    }

    const token = localStorage.getItem('sessionToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('sessionToken')
      // Call auth context logout if available (set by AuthProvider)
      if (typeof window.__authLogout === 'function') {
        window.__authLogout()
      }
    }
    return Promise.reject(error)
  }
)

export default api
