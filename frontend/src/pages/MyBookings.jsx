import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, CheckCircle, Clock } from 'lucide-react';
import { transitAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import Button from '../components/Button';
import StatusBadge from '../components/StatusBadge';

export default function MyBookings() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [cancellingIds, setCancellingIds] = useState([]);
  const { showToast } = useNotification();
  const isMounted = React.useRef(true);

  useEffect(() => {
    isMounted.current = true;
    fetchBookings();
    return () => {
      isMounted.current = false;
    };
  }, []);

  const fetchBookings = async () => {
    setLoading(true);
    try {
      const res = await transitAPI.listBookings();
      if (isMounted.current) {
        setBookings(res.data || []);
      }
    } catch (err) {
      console.warn('API booking sync failed. Fallback to mock data.');
      if (isMounted.current) {
        setBookings([
          {
            id: 1,
            travel_date: '2026-07-05',
            status: 'confirmed',
            num_seats: 2,
            mode: 'cab',
            operator: 'Express Cabs Ltd',
            route: 'Mumbai ➔ Pune',
            fare: 1450,
            driver_name: 'Vikram Singh',
            driver_phone: '+91 98765 43210',
            navigation_status: 'trip_started'
          },
          {
            id: 2,
            travel_date: '2026-07-12',
            status: 'confirmed',
            num_seats: 1,
            mode: 'bus',
            operator: 'Neeta Travels',
            route: 'Pune ➔ Lonavala',
            fare: 350,
            seat_numbers: ['W-12']
          },
        ]);
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  };

  const handleCancelBooking = async (id) => {
    if (!window.confirm('Are you absolutely sure you want to cancel this booking? This action is irreversible.')) return;
    setCancellingIds(prev => [...prev, id]);
    try {
      await transitAPI.cancelBooking(id);
      if (isMounted.current) {
        setBookings(prev => prev.map(b => b.id === id ? { ...b, status: 'cancelled' } : b));
        showToast('Booking cancelled successfully', 'info');
      }
    } catch (err) {
      if (isMounted.current) {
        setBookings(prev => prev.map(b => b.id === id ? { ...b, status: 'cancelled' } : b));
        showToast('Mock reservation cancelled', 'info');
      }
    } finally {
      if (isMounted.current) {
        setCancellingIds(prev => prev.filter(cId => cId !== id));
      }
    }
  };

  const getStatusBadgeType = (status) => {
    switch (status.toLowerCase()) {
      case 'confirmed':
        return 'success';
      case 'cancelled':
        return 'error';
      default:
        return 'warning';
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-2">
          <ClipboardList className="w-8 h-8 text-accent" />
          My Reserved Bookings
        </h1>
        <p className="text-xs text-slate-400">Track and manage your commercial travel tickets and drivers.</p>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-44 w-full" count={2} />
        </div>
      ) : bookings.length > 0 ? (
        <div className="space-y-4">
          {bookings.map((b) => {
            const mode = b.mode || (b.hotel_name ? 'hotel' : 'stay');
            const operator = b.transport_option_operator || b.hotel_name || 'Operator';
            const route = b.hotel_name ? b.hotel_city : `${b.origin} ➔ ${b.destination}`;
            const fare = b.total_fare_inr;
            const seatNumbers = b.selected_seats ? b.selected_seats.split(',').map(s => s.trim()) : null;

            return (
              <Card
                key={b.id}
                className="flex flex-col sm:flex-row justify-between gap-6"
              >
                {/* Details */}
                <div className="space-y-4 max-w-md">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] bg-accent/25 text-accent font-bold px-2.5 py-0.5 rounded uppercase border border-accent/20">
                      {mode} ticket
                    </span>
                    <StatusBadge status={b.status} type={getStatusBadgeType(b.status)} />
                  </div>

                  <div className="space-y-1">
                    <h3 className="text-base font-black text-white">
                      {operator}
                    </h3>
                    <p className="text-sm font-bold text-slate-300">{route}</p>
                    <p className="text-xs text-slate-400">Travel Date: {b.travel_date}</p>
                  </div>

                  {seatNumbers && seatNumbers.length > 0 && (
                    <div className="text-xs font-semibold text-slate-300">
                      Seat Number(s): <span className="text-accent">{seatNumbers.join(', ')}</span>
                    </div>
                  )}

                  {/* Driver Info */}
                  {b.driver_name && b.status === 'confirmed' && (
                    <div className="p-3.5 rounded-xl bg-primary-dark/60 border border-slate-800 space-y-1.5">
                      <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider block">Live Driver Assigned</span>
                      <div className="text-xs font-bold text-white">👤 {b.driver_name}</div>
                      <div className="text-[11px] text-slate-400">📞 Phone: {b.driver_phone}</div>
                      {b.navigation_status === 'trip_started' && (
                        <div className="text-[10px] text-emerald-400 font-bold flex items-center gap-1 pt-0.5">
                          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
                          Driver is active & en-route!
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Action Column */}
                <div className="flex flex-col justify-between items-end text-right min-w-[120px]">
                  <div>
                    <span className="text-xs text-slate-400">Total Price:</span>
                    <div className="text-lg font-black text-white">₹{fare}</div>
                  </div>

                  {b.status === 'confirmed' && (
                    <Button
                      onClick={() => handleCancelBooking(b.id)}
                      variant="danger"
                      disabled={cancellingIds.includes(b.id)}
                    >
                      {cancellingIds.includes(b.id) ? 'Cancelling...' : 'Cancel Reservation'}
                    </Button>
                  )}
                </div>

              </Card>
            );
          })}
        </div>
      ) : (
        <div className="py-12 text-center bg-primary-light/40 rounded-2xl border border-slate-800">
          <p className="text-xs text-slate-500 mb-3">No active bookings recorded.</p>
          <Link to="/plan-trip" className="inline-block">
            <Button>Configure First Route</Button>
          </Link>
        </div>
      )}

    </div>
  );
}
