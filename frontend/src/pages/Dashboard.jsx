import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Compass, Sparkles, Navigation, Store, DollarSign, ShieldCheck } from 'lucide-react';
import { tripsAPI, unifiedAuthAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

export default function Dashboard({ onLogout }) {
  const [profile, setProfile] = useState(null);
  const [activeTrip, setActiveTrip] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapLoading, setMapLoading] = useState(true);
  
  const mapRef = useRef(null);
  const navigate = useNavigate();
  const { showToast } = useNotification();

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const profileRes = await unifiedAuthAPI.me();
      const userProfile = profileRes.data;
      setProfile(userProfile);

      if (userProfile.role === 'provider') {
        showToast('Redirecting to Logistics Partner dashboard', 'info');
        navigate('/provider');
        return;
      } else if (userProfile.role === 'food_provider') {
        showToast('Redirecting to Dhaba Partner dashboard', 'info');
        navigate('/food-provider');
        return;
      }

      // Fetch active trip
      try {
        const activeRes = await tripsAPI.list();
        const trips = activeRes.data || [];
        if (trips.length > 0) {
          setActiveTrip(trips[trips.length - 1]);
        }
      } catch (err) {
        console.warn('Failed to retrieve active trip route', err);
      }

    } catch (err) {
      console.error('Failed to load dashboard diagnostics', err);
      showToast('Session expired. Redirecting to login...', 'error');
      if (onLogout) onLogout();
      navigate('/auth');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (loading || profile?.role !== 'traveler') return;

    const timer = setTimeout(() => {
      if (!mapRef.current) {
        const mapElement = document.getElementById('dashboard-map');
        if (!mapElement) return;

        const map = L.map('dashboard-map', { zoomControl: false }).setView([19.0760, 72.8777], 9);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          attribution: '© CartoDB'
        }).addTo(map);

        mapRef.current = map;
        setMapLoading(false);

        if (activeTrip) {
          const startIcon = L.divIcon({
            html: `<div class="bg-indigo-600 border border-indigo-400 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-lg">🏁 Start</div>`,
            className: '',
            iconSize: [50, 18]
          });
          const endIcon = L.divIcon({
            html: `<div class="bg-accent border border-amber-400 text-slate-950 text-[9px] font-bold px-1.5 py-0.5 rounded shadow-lg">🎯 Dest</div>`,
            className: '',
            iconSize: [50, 18]
          });

          // Use real coordinates from trip details if available
          const startLat = activeTrip.origin_lat ? parseFloat(activeTrip.origin_lat) : 19.0760;
          const startLon = activeTrip.origin_lon ? parseFloat(activeTrip.origin_lon) : 72.8777;
          const endLat = activeTrip.destination_lat ? parseFloat(activeTrip.destination_lat) : 18.5204;
          const endLon = activeTrip.destination_lon ? parseFloat(activeTrip.destination_lon) : 73.8567;

          const points = [
            [startLat, startLon],
            [endLat, endLon]
          ];
          const polyline = L.polyline(points, { color: '#f59e0b', weight: 4, opacity: 0.8 }).addTo(map);
          map.fitBounds(polyline.getBounds());

          L.marker([startLat, startLon], { icon: startIcon }).addTo(map);
          L.marker([endLat, endLon], { icon: endIcon }).addTo(map);
        } else {
          const locationIcon = L.divIcon({
            html: `<div class="bg-indigo-600 w-4 h-4 rounded-full border-2 border-white pulse-glow"></div>`,
            className: '',
            iconSize: [16, 16]
          });
          L.marker([19.0760, 72.8777], { icon: locationIcon }).addTo(map);
        }

        setTimeout(() => {
          map.invalidateSize();
        }, 100);
      }
    }, 200);

    return () => {
      clearTimeout(timer);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [loading, activeTrip, profile]);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-left space-y-8">
        <Skeleton className="h-10 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Skeleton className="h-24 w-full" count={4} />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Title */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-black text-white tracking-tight">Explore Cockpit</h1>
          <p className="text-xs text-slate-400">Sync with active routes, log travel schedules, and check safety indices.</p>
        </div>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="text-xs text-slate-400 font-bold">Safety rating: 98/100</span>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link
          to="/plan-trip"
          className="p-5 rounded-2xl bg-primary-light border border-slate-800 shadow-md hover:border-accent/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col justify-between h-28"
        >
          <Sparkles className="w-8 h-8 text-accent fill-accent" />
          <span className="text-xs font-black text-white">Plan a Trip</span>
        </Link>
        <Link
          to="/start-trip"
          className="p-5 rounded-2xl bg-primary-light border border-slate-800 shadow-md hover:border-accent/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col justify-between h-28"
        >
          <Navigation className="w-8 h-8 text-accent" />
          <span className="text-xs font-black text-white">Start Live Trip</span>
        </Link>
        <Link
          to="/start-trip?mode=dhabas"
          className="p-5 rounded-2xl bg-primary-light border border-slate-800 shadow-md hover:border-accent/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col justify-between h-28"
        >
          <Store className="w-8 h-8 text-accent" />
          <span className="text-xs font-black text-white">Find Dhabas</span>
        </Link>
        <Link
          to="/start-trip?mode=splitter"
          className="p-5 rounded-2xl bg-primary-light border border-slate-800 shadow-md hover:border-accent/40 hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col justify-between h-28"
        >
          <DollarSign className="w-8 h-8 text-accent" />
          <span className="text-xs font-black text-white">Split Expenses</span>
        </Link>
      </div>

      {/* Map Widget inside a Shared Card container */}
      <Card className="space-y-4">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">Embedded Route Map</h3>
        <div className="relative h-64 rounded-xl overflow-hidden border border-slate-800">
          <div id="dashboard-map" className="w-full h-full" />
          {mapLoading && (
            <div className="absolute inset-0 bg-primary-dark/80 flex items-center justify-center text-slate-400 text-xs">
              Initializing Leaflet Coordinates...
            </div>
          )}
        </div>
      </Card>

      {/* Active Route display */}
      {activeTrip ? (
        <div className="p-5 rounded-2xl bg-gradient-to-br from-indigo-950/20 to-primary-light/50 border border-indigo-500/10 flex justify-between items-center">
          <div className="space-y-1">
            <span className="text-[9px] text-accent uppercase font-black tracking-widest">Active route schedule</span>
            <div className="text-sm font-black text-white">{activeTrip.origin} ➔ {activeTrip.destination}</div>
            <p className="text-xs text-slate-400">Date: {activeTrip.start_date}</p>
          </div>
          <Link
            to={`/my-trips/${activeTrip.id}/itinerary`}
            className="px-4 py-2 bg-slate-850 hover:bg-slate-800 text-xs font-bold text-slate-200 border border-slate-700 rounded-xl transition-all"
          >
            Open Schedule
          </Link>
        </div>
      ) : (
        <div className="p-5 rounded-2xl bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-500 italic">
          No active route schedules synchronized. Click "Plan a Trip" to configure your route.
        </div>
      )}

    </div>
  );
}
