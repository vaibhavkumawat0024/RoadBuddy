import axios from 'axios';

const getBaseURL = () => {
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${hostname}:8000`;
};

const client = axios.create({
  baseURL: getBaseURL(),
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to handle 401s and redirect to login
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      const isAuthUrl = error.config?.url && (
        error.config.url.includes('/login') || 
        error.config.url.includes('/register') || 
        error.config.url.includes('/verify-otp') || 
        error.config.url.includes('/api/auth')
      );
      if (!isAuthUrl && window.location.pathname !== '/auth') {
        window.location.href = '/auth';
      }
    }
    return Promise.reject(error);
  }
);

export default client;

export const unifiedAuthAPI = {
  login: (role, email, password) => client.post('/api/auth/login', { role, email, password }),
  signup: (payload) => client.post('/api/auth/signup', payload),
  me: () => client.get('/api/auth/me'),
  logout: () => client.post('/api/auth/logout')
};

// ─── TRAVELER API ENDPOINTS ──────────────────────────────────────────
export const authAPI = {
  register: (data) => client.post('/api/users/register', data),
  verifyOtp: (email, otp) => client.post('/api/users/verify-otp', { email, otp }),
  login: (email, password) => {
    // OAuth2PasswordRequestForm expects form-urlencoded username/password
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    return client.post('/api/users/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
  },
  getProfile: () => client.get('/api/users/me'),
  updateProfile: (data) => client.patch('/api/users/me', data),
  changePassword: (data) => client.post('/api/users/change-password', data),
};

export const vehiclesAPI = {
  list: () => client.get('/api/users/vehicles'),
  create: (data) => client.post('/api/users/vehicles', data),
  delete: (id) => client.delete(`/api/users/vehicles/${id}`),
};

export const tripsAPI = {
  generate: (data) => client.post('/api/trips/generate', data),
  list: () => client.get('/api/trips/my'),
  get: (id) => client.get(`/api/trips/${id}`),
  delete: (id) => client.delete(`/api/trips/${id}`),
  costBreakdown: (id) => client.get(`/api/trips/${id}/cost`),
  chat: (message, history = []) => client.post('/api/trips/chat', { message, history }),
  safetyCheck: (origin, destination, travelDate) => client.post('/api/trips/safety-check', { origin, destination, travel_date: travelDate }),
  recommendations: (city, budget, interests = ['sightseeing']) => client.post('/api/trips/recommendations', { home_city: city, budget_inr: budget, interests }),
  suggestWaypoints: (origin, destination, preferences = []) => client.post('/api/trips/suggest-waypoints', { origin, destination, preferences }),
};

export const transitAPI = {
  search: (data) => client.post('/api/transport/search', data),
  book: (data) => client.post('/api/transport/book', data),
  listBookings: () => client.get('/api/transport/bookings'),
  cancelBooking: (id) => client.patch(`/api/transport/bookings/${id}/cancel`),
};

export const hotelAPI = {
  search: (data) => client.post('/api/bookings/hotels/search', data),
  book: (data) => client.post('/api/bookings/hotels/book', data),
};

export const trainAPI = {
  search: (data) => client.post('/api/bookings/trains/search', data),
  book: (data) => client.post('/api/bookings/trains/book', data),
};

export const busAPI = {
  search: (data) => client.post('/api/bookings/buses/search', data),
  book: (data) => client.post('/api/bookings/buses/book', data),
};

export const flightAPI = {
  search: (data) => client.post('/api/bookings/flights/search', data),
  book: (data) => client.post('/api/bookings/flights/book', data),
};

export const foodAPI = {
  listRestaurants: (city) => client.get(`/api/food/restaurants?city=${encodeURIComponent(city)}`),
  getMenu: (restaurantId) => client.get(`/api/food/restaurants/${restaurantId}/menu`),
  createOrder: (data) => client.post('/api/food/orders', data),
  listOrders: () => client.get('/api/food/my-orders'),
  notifyArrival: (orderId) => client.post(`/api/food/orders/${orderId}/arrival`),
  
  // Provider operations
  listProviderOrders: () => client.get('/api/food/provider/orders'),
  updateOrderStatus: (orderId, status) => client.patch(`/api/food/provider/orders/${orderId}/status`, { status }),
  updateOrderPrepTime: (orderId, mins) => client.patch(`/api/food/provider/orders/${orderId}/prep-time`, { prep_time_mins: mins }),
  getProviderRestaurant: () => client.get('/api/food/provider/restaurant'),
  addMenuItem: (data) => client.post('/api/food/provider/menu', data),
  deleteMenuItem: (itemId) => client.delete(`/api/food/provider/menu/${itemId}`),
};

export const fuelAPI = {
  calculate: (data) => client.post('/api/fuel/calculate', data),
  getPrices: () => client.get('/api/fuel/fuel-prices'),
  getTollEstimate: (origin, destination) => client.get(`/api/fuel/toll-estimate?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`),
};

export const journalAPI = {
  createEntry: (data) => client.post('/api/journal/entry', data),
  getJournal: (tripId) => client.get(`/api/journal/${tripId}`),
  publishJournal: (tripId) => client.patch(`/api/journal/${tripId}/publish`),
  getSummary: (tripId) => client.get(`/api/journal/${tripId}/summary`),
  summarize: (text) => client.post('/api/journal/summarize', { text }),
};

export const communityAPI = {
  createRoute: (data) => client.post('/api/community/routes', data),
  listRoutes: () => client.get('/api/community/routes'),
  getRoute: (id) => client.get(`/api/community/routes/${id}`),
  cloneRoute: (id) => client.post(`/api/community/routes/${id}/clone`),
  addReview: (id, rating, comment) => client.post(`/api/community/routes/${id}/review`, { rating, comment }),
  listReviews: (id) => client.get(`/api/community/routes/${id}/reviews`),
  smartSearch: (query) => client.post('/api/community/smart-search', { query }),
};

// ─── PROVIDER API ENDPOINTS ──────────────────────────────────────────
export const providerAPI = {
  register: (data) => client.post('/api/provider/register', data),
  login: (email, password) => client.post('/api/provider/login', { email, password }),
  getProfile: () => client.get('/api/provider/me'),
  updateProfile: (data) => client.patch('/api/provider/me', data),
  listAssets: () => client.get('/api/provider/vehicle-assets'),
  createAsset: (data) => client.post('/api/provider/vehicle-assets', data),
  deleteAsset: (id) => client.delete(`/api/provider/vehicle-assets/${id}`),
  listVehicles: () => client.get('/api/provider/vehicles'),
  createVehicle: (data) => client.post('/api/provider/vehicles', data),
  updateVehicle: (id, data) => client.put(`/api/provider/vehicles/${id}`, data),
  deleteVehicle: (id) => client.delete(`/api/provider/vehicles/${id}`),
  listBookings: () => client.get('/api/provider/bookings'),
  listServices: () => client.get('/api/provider/services'),
  getBookedSeats: (vehicleId, date) => client.get(`/api/provider/vehicles/${vehicleId}/booked-seats?travel_date=${date}`),
  getBookingDetails: (vehicleId) => client.get(`/api/provider/vehicles/${vehicleId}/booking-details`),
  startNavigation: (bookingId) => client.post(`/api/provider/bookings/${bookingId}/start-nav`),
  updateLocation: (bookingId, lat, lon) => client.post(`/api/provider/bookings/${bookingId}/location`, { lat, lon }),
  trackBooking: (bookingId) => client.get(`/api/provider/bookings/${bookingId}/track`),
  listActiveEnroute: (userId) => client.get(`/api/provider/bookings/active-enroute?user_id=${userId}`),
  startVehicleTrip: (vehicleId) => client.post(`/api/provider/vehicles/${vehicleId}/start-trip`),
  updateVehicleLocation: (vehicleId, lat, lon) => client.post(`/api/provider/vehicles/${vehicleId}/location`, { lat, lon }),
  listUserBookings: () => client.get('/api/provider/bookings/user'),
  cancelBooking: (bookingId) => client.post(`/api/provider/bookings/${bookingId}/cancel`),
  checkUnread: () => client.get('/api/provider/bookings/unread-check'),
  markRead: () => client.post('/api/provider/bookings/mark-read'),
  chat: (message, history = []) => client.post('/api/provider/chat', { message, history }),
};
