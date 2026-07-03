import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Compass, Ship, User, LogOut, LayoutDashboard, Map, Settings, Users, LogIn, ClipboardList, Shield } from 'lucide-react';
import { useNotification } from '../context/NotificationContext';

export default function Navbar({ portal, setPortal, user, onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useNotification();

  const handleLogout = () => {
    onLogout();
    showToast('Logged out successfully', 'info');
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav className="bg-primary-light/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-50 text-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo */}
          <div className="flex items-center gap-2">
            <Link to={portal === 'traveler' ? '/dashboard' : (user?.role === 'food_provider' ? '/food-provider' : '/provider')} className="flex items-center gap-2 group">
              <div className="p-2 bg-gradient-to-tr from-accent to-amber-500 rounded-xl shadow-lg shadow-accent/20 group-hover:scale-105 transition-transform">
                <Compass className="w-5 h-5 text-slate-950 font-bold" />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-black tracking-tight text-white leading-none">
                  Road<span className="text-accent">Buddy</span>
                </span>
                <span className="text-[9px] text-slate-400 font-bold tracking-widest uppercase mt-0.5">Your Trip Pilot</span>
              </div>
            </Link>
          </div>

          {/* Portal Switcher & Nav Links */}
          {user && (
            <div className="hidden md:flex items-center gap-6">
              
              {/* Traveler Portal Links */}
              {portal === 'traveler' && (
                <div className="flex items-center gap-1.5 text-sm font-semibold">
                  <Link
                    to="/dashboard"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/dashboard') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    Dashboard
                  </Link>
                  <Link
                    to="/plan-trip"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/plan-trip') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <Map className="w-4 h-4" />
                    Plan Trip
                  </Link>
                  <Link
                    to="/my-bookings"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/my-bookings') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <ClipboardList className="w-4 h-4" />
                    My Bookings
                  </Link>
                </div>
              )}

              {/* Provider Portal Links */}
              {portal === 'provider' && (
                <div className="flex items-center gap-1.5 text-sm font-semibold">
                  <Link
                    to="/provider"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/provider') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    Overview
                  </Link>
                  <Link
                    to="/provider/fleet"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/provider/fleet') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <Ship className="w-4 h-4" />
                    Fleet Management
                  </Link>
                  <Link
                    to="/provider/pipeline"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/provider/pipeline') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <ClipboardList className="w-4 h-4" />
                    Booking Pipeline
                  </Link>
                </div>
              )}

              {/* Food Provider Portal Links */}
              {portal === 'food_provider' && (
                <div className="flex items-center gap-1.5 text-sm font-semibold">
                  <Link
                    to="/food-provider"
                    className={`px-3 py-2 rounded-lg flex items-center gap-1.5 transition-all ${
                      isActive('/food-provider') ? 'bg-accent/10 text-accent' : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <LayoutDashboard className="w-4 h-4" />
                    Dhaba Overview
                  </Link>
                </div>
              )}

              {/* Portal Context Switcher Badge */}
              <button
                onClick={() => {
                  const nextPortal = portal === 'traveler' 
                    ? (user?.role === 'food_provider' ? 'food_provider' : 'provider') 
                    : 'traveler';
                  setPortal(nextPortal);
                  showToast(`Switched to ${nextPortal === 'traveler' ? 'Traveler' : (user?.role === 'food_provider' ? 'Dhaba Partner' : 'Provider')} Portal`, 'success');
                  navigate(nextPortal === 'traveler' 
                    ? '/dashboard' 
                    : (user?.role === 'food_provider' ? '/food-provider' : '/provider')
                  );
                }}
                className="bg-slate-800 hover:bg-slate-700 text-xs font-bold px-3 py-1.5 rounded-full border border-slate-700 text-slate-300 transition-colors flex items-center gap-1"
              >
                <Shield className="w-3.5 h-3.5 text-accent" />
                Mode: {portal === 'traveler' ? 'Traveler' : (portal === 'food_provider' ? 'Dhaba Partner' : 'Provider')}
              </button>

            </div>
          )}

          {/* User Profile / Logout / Actions */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-bold text-white leading-none">{user.name}</span>
                  <span className="text-[10px] text-slate-400 font-semibold">{portal === 'traveler' ? 'Explorer' : (user.role === 'food_provider' ? 'Dhaba Partner' : 'Logistics Partner')}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 rounded-lg transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/auth"
                  className="px-3.5 py-1.5 rounded-lg border border-slate-700 text-xs font-bold text-slate-300 hover:bg-slate-800 transition-colors flex items-center gap-1"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  Sign In
                </Link>
              </div>
            )}
          </div>

        </div>
      </div>
    </nav>
  );
}
