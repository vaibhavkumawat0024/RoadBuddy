import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import ChatbotWidget from './components/ChatbotWidget';
import Landing from './pages/Landing';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import TripPlanner from './pages/TripPlanner';
import TripItinerary from './pages/TripItinerary';
import LiveTrip from './pages/LiveTrip';
import MyBookings from './pages/MyBookings';
import Vehicles from './pages/Vehicles';
import ProviderDashboard from './pages/ProviderDashboard';
import FleetManagement from './pages/FleetManagement';
import BookingPipeline from './pages/BookingPipeline';
import FoodProviderDashboard from './pages/FoodProviderDashboard';
import { NotificationProvider } from './context/NotificationContext';
import { ChatProvider } from './context/ChatContext';
import { unifiedAuthAPI } from './api/client';
import './App.css';

function ProtectedRoute({ user, allowedRoles, children }) {
  if (!user) {
    return <Navigate to="/auth" replace />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    if (user.role === 'provider') return <Navigate to="/provider" replace />;
    if (user.role === 'food_provider') return <Navigate to="/food-provider" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

function AuthRedirect({ user, children }) {
  if (user) {
    if (user.role === 'provider') return <Navigate to="/provider" replace />;
    if (user.role === 'food_provider') return <Navigate to="/food-provider" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

export default function App() {
  const [portal, setPortal] = useState('traveler'); // 'traveler' | 'provider'
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await unifiedAuthAPI.me();
      setUser(res.data);
      if (res.data.role === 'provider') {
        setPortal('provider');
      } else if (res.data.role === 'food_provider') {
        setPortal('food_provider');
      } else {
        setPortal('traveler');
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    if (userData.role === 'provider') {
      setPortal('provider');
    } else if (userData.role === 'food_provider') {
      setPortal('food_provider');
    } else {
      setPortal('traveler');
    }
  };

  const handleLogout = async () => {
    try {
      await unifiedAuthAPI.logout();
    } catch (err) {
      console.warn('Backend logout sync failed', err);
    }
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-primary-dark flex items-center justify-center text-slate-400">
        <div className="space-y-4 text-center">
          <div className="w-8 h-8 border-4 border-dashed border-accent rounded-full animate-spin mx-auto"></div>
          <p className="text-xs uppercase font-bold tracking-widest text-slate-500">Syncing Diagnostics...</p>
        </div>
      </div>
    );
  }

  return (
    <NotificationProvider>
      <ChatProvider>
        <Router>
          <div className="min-h-screen flex flex-col bg-primary-dark">
            
            <Navbar
              portal={portal}
              setPortal={setPortal}
              user={user}
              onLogout={handleLogout}
            />

            <div className="flex-grow">
              <Routes>
                
                {/* Marketing Landing */}
                <Route path="/" element={<AuthRedirect user={user}><Landing /></AuthRedirect>} />
                
                {/* Unified Auth route */}
                <Route path="/auth" element={<AuthRedirect user={user}><Auth onLoginSuccess={handleLoginSuccess} /></AuthRedirect>} />

                {/* Traveler Portal routes */}
                <Route path="/dashboard" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><Dashboard onLogout={handleLogout} /></ProtectedRoute>} />
                <Route path="/plan-trip" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><TripPlanner /></ProtectedRoute>} />
                <Route path="/my-trips/:id/itinerary" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><TripItinerary /></ProtectedRoute>} />
                <Route path="/start-trip" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><LiveTrip /></ProtectedRoute>} />
                <Route path="/my-bookings" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><MyBookings /></ProtectedRoute>} />
                <Route path="/vehicles" element={<ProtectedRoute user={user} allowedRoles={['traveler']}><Vehicles /></ProtectedRoute>} />

                {/* Transport Provider Portal routes */}
                <Route path="/provider" element={<ProtectedRoute user={user} allowedRoles={['provider']}><ProviderDashboard onLogout={handleLogout} /></ProtectedRoute>} />
                <Route path="/provider/fleet" element={<ProtectedRoute user={user} allowedRoles={['provider']}><FleetManagement /></ProtectedRoute>} />
                <Route path="/provider/pipeline" element={<ProtectedRoute user={user} allowedRoles={['provider']}><BookingPipeline /></ProtectedRoute>} />

                {/* Food Provider (Dhaba Partner) Portal routes */}
                <Route path="/food-provider" element={<ProtectedRoute user={user} allowedRoles={['food_provider']}><FoodProviderDashboard onLogout={handleLogout} /></ProtectedRoute>} />

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" />} />

              </Routes>
            </div>

            {/* Universally Persistent Floating Chatbot for Traveler */}
            {user && user.role === 'traveler' && <ChatbotWidget />}

          </div>
        </Router>
      </ChatProvider>
    </NotificationProvider>
  );
}
