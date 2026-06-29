import axios from 'axios';

// baseURL is empty — all API calls in the codebase already include the full
// /api/... path. A relative empty base means requests go to the same host
// serving the page, whether that's nginx (Docker Compose) or the ingress (Kubernetes).
const api = axios.create({
  baseURL: '',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
