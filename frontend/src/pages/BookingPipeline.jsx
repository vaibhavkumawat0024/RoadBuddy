import React, { useState, useEffect } from 'react';
import { ClipboardList, ArrowRight, CheckCircle, User, Calendar, MapPin } from 'lucide-react';
import { providerAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import Button from '../components/Button';
import StatusBadge from '../components/StatusBadge';

export default function BookingPipeline() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('confirmed');

  const { showToast } = useNotification();

  useEffect(() => {
    fetchBookings();
  }, []);

  const fetchBookings = async () => {
    setLoading(true);
    try {
      const res = await providerAPI.listBookings();
      setBookings(res.data || []);
    } catch (err) {
      console.warn('API pipeline sync failed. Fallback to mocks.');
      setBookings([
        { id: 101, traveler_name: 'John Doe', travel_date: '2026-07-05', status: 'confirmed', fare: 1200, route: 'Mumbai ➔ Pune', vehicle_name: 'Cab #MH-12-AB-1234', dispatch_state: 'idle' },
        { id: 102, traveler_name: 'Alice Cooper', travel_date: '2026-07-05', status: 'confirmed', fare: 1200, route: 'Mumbai ➔ Pune', vehicle_name: 'Cab #MH-12-AB-1234', dispatch_state: 'trip_started' },
        { id: 103, traveler_name: 'Bob Ross', travel_date: '2026-07-04', status: 'completed', fare: 350, route: 'Pune ➔ Lonavala', vehicle_name: 'Bus #MH-04-XY-9876', dispatch_state: 'arrived' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (id, nextStatus) => {
    try {
      if (nextStatus === 'trip_started') {
        await providerAPI.startNavigation(id);
      }
      setBookings(prev => prev.map(b => b.id === id ? { ...b, dispatch_state: nextStatus } : b));
      showToast(`Booking dispatch state updated to: ${nextStatus.replace('_', ' ')}`, 'success');
    } catch (err) {
      setBookings(prev => prev.map(b => b.id === id ? { ...b, dispatch_state: nextStatus } : b));
      showToast(`Mock status updated: ${nextStatus.replace('_', ' ')}`, 'success');
    }
  };

  const filtered = bookings.filter(b => {
    if (filterStatus === 'confirmed') return b.status === 'confirmed' && b.dispatch_state !== 'arrived';
    if (filterStatus === 'en-route') return b.dispatch_state === 'trip_started' || b.dispatch_state === 'en_route';
    if (filterStatus === 'completed') return b.status === 'completed' || b.dispatch_state === 'arrived';
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-2">
          <ClipboardList className="w-8 h-8 text-accent" />
          Booking Pipeline
        </h1>
        <p className="text-xs text-slate-400">Track passenger check-ins and update driver dispatch statuses.</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-2">
        {['confirmed', 'en-route', 'completed'].map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className={`px-4 py-2.5 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
              filterStatus === status 
                ? 'border-accent text-accent font-black' 
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Grid List */}
      {loading ? (
        <div className="grid md:grid-cols-2 gap-6">
          <Skeleton className="h-32 w-full" count={2} />
        </div>
      ) : filtered.length > 0 ? (
        <div className="grid md:grid-cols-2 gap-6">
          {filtered.map((b) => (
            <Card
              key={b.id}
              className="flex flex-col justify-between gap-4"
            >
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-slate-400 font-bold tracking-widest font-mono">ID: #{b.id}</span>
                  <StatusBadge
                    status={b.dispatch_state.replace('_', ' ')}
                    type={b.dispatch_state === 'trip_started' ? 'success' : 'info'}
                  />
                </div>

                <div className="space-y-1.5 text-xs">
                  <div className="text-sm font-black text-white flex items-center gap-1">
                    <User className="w-3.5 h-3.5 text-accent" />
                    Traveler: {b.traveler_name || 'Passenger'}
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300 font-bold">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    Route: {b.route}
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    Date: {b.travel_date}
                  </div>
                  <div className="text-[11px] text-slate-400">
                    Assigned Vehicle: <strong className="text-slate-300">{b.vehicle_name}</strong>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="pt-3 border-t border-slate-800/80 flex justify-between items-center gap-4">
                <div>
                  <span className="text-[9px] text-slate-400 block uppercase font-bold">Price</span>
                  <strong className="text-accent text-sm font-black">₹{b.fare}</strong>
                </div>

                <div className="flex gap-2">
                  {b.dispatch_state === 'idle' && (
                    <Button
                      onClick={() => handleUpdateStatus(b.id, 'trip_started')}
                      className="px-3.5 py-1.5"
                    >
                      Start Nav
                      <ArrowRight className="w-3 h-3" />
                    </Button>
                  )}
                  {b.dispatch_state === 'trip_started' && (
                    <Button
                      onClick={() => handleUpdateStatus(b.id, 'arrived')}
                      className="px-3.5 py-1.5"
                    >
                      Complete Trip
                      <CheckCircle className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              </div>

            </Card>
          ))}
        </div>
      ) : (
        <div className="py-12 text-center bg-primary-light/40 rounded-2xl border border-slate-800">
          <p className="text-xs text-slate-500">No bookings in this pipeline stage.</p>
        </div>
      )}

    </div>
  );
}
