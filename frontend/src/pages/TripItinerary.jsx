import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Compass, DollarSign, ArrowLeft, Sun, Moon, Sunrise, Sunset, Hotel, Navigation } from 'lucide-react';
import { tripsAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import Button from '../components/Button';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function TripItinerary() {
  const { id } = useParams();
  const [trip, setTrip] = useState(null);
  const [costBreakdown, setCostBreakdown] = useState(null);
  const [loading, setLoading] = useState(true);
  const { showToast } = useNotification();

  useEffect(() => {
    fetchItineraryDetails();
  }, [id]);

  const fetchItineraryDetails = async () => {
    setLoading(true);
    try {
      const [tripRes, costRes] = await Promise.all([
        tripsAPI.get(id),
        tripsAPI.costBreakdown(id).catch(() => null),
      ]);
      setTrip(tripRes.data);
      if (costRes) setCostBreakdown(costRes.data.breakdown);
    } catch (err) {
      showToast('Failed to load itinerary details.', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6 text-left">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-44 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <p className="text-slate-400 text-sm">Itinerary not found.</p>
        <Link to="/dashboard" className="text-accent underline mt-2 inline-block">Back to Dashboard</Link>
      </div>
    );
  }

  // Group stops by day
  const stopsByDay = (trip.stops || []).reduce((acc, stop) => {
    acc[stop.day] = acc[stop.day] || [];
    acc[stop.day].push(stop);
    return acc;
  }, {});

  const getSlotIcon = (slot) => {
    switch (slot.toLowerCase()) {
      case 'morning':
        return <Sunrise className="w-5 h-5 text-amber-400" />;
      case 'afternoon':
        return <Sun className="w-5 h-5 text-accent" />;
      case 'evening':
        return <Sunset className="w-5 h-5 text-indigo-400" />;
      case 'night':
        return <Moon className="w-5 h-5 text-blue-400" />;
      default:
        return <Sun className="w-5 h-5 text-accent" />;
    }
  };

  const chartData = costBreakdown ? [
    { name: 'Fuel', cost: Math.round(costBreakdown.fuel_cost_inr || 0) },
    { name: 'Toll', cost: Math.round(costBreakdown.toll_cost_inr || 0) },
    { name: 'Hotel', cost: Math.round(costBreakdown.hotel_cost_inr || 0) },
    { name: 'Food', cost: Math.round(costBreakdown.food_cost_inr || 0) },
  ] : [];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Back link */}
      <div>
        <Link to="/dashboard" className="text-xs text-slate-400 hover:text-accent font-bold flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
        </Link>
      </div>

      {/* Hero card details */}
      <Card className="relative overflow-hidden bg-primary-light flex flex-col justify-between min-h-[160px]">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
        <div className="relative z-10 space-y-3">
          <span className="text-[10px] bg-accent/20 text-accent font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border border-accent/25">
            {trip.travel_mode.replace('_', ' ')} Mode
          </span>
          <h2 className="text-3xl font-black text-white tracking-tight">
            {trip.origin} ➔ {trip.destination}
          </h2>
          <p className="text-xs text-slate-400">
            Dates: {trip.start_date} {trip.end_date ? `to ${trip.end_date}` : ''} · Budget: ₹{Math.round(trip.budget_inr || 0)}
          </p>
        </div>
      </Card>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        
        {/* Day timeline */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Compass className="w-5 h-5 text-accent" />
            Interactive Timeline
          </h2>

          {Object.keys(stopsByDay).length > 0 ? (
            Object.keys(stopsByDay).sort().map((day) => (
              <div key={day} className="space-y-4">
                <h3 className="text-sm font-black text-accent uppercase tracking-wider border-b border-slate-800 pb-2">
                  🗓️ Day {day}
                </h3>
                <div className="space-y-4 relative border-l border-slate-800 ml-4 pl-6">
                  {stopsByDay[day].map((stop, idx) => (
                    <div key={idx} className="relative space-y-2 group">
                      
                      <span className="absolute -left-[38px] top-0 p-1.5 rounded-full bg-slate-900 border border-slate-800 group-hover:border-accent transition-colors">
                        {getSlotIcon(stop.time_slot)}
                      </span>

                      <Card className="p-4 flex flex-col sm:flex-row justify-between gap-4">
                        <div className="space-y-1 max-w-md">
                          <span className="text-[9px] text-slate-400 uppercase font-black tracking-wider">{stop.time_slot} Slot</span>
                          <h4 className="text-sm font-black text-white">{stop.place_name}</h4>
                          <p className="text-xs text-slate-400 leading-relaxed">{stop.description}</p>
                          {stop.hotel_name && (
                            <div className="flex items-center gap-2 text-[10px] text-amber-400 font-semibold pt-1">
                              <Hotel className="w-3.5 h-3.5" />
                              Stay: {stop.hotel_name} · ★ {stop.hotel_rating || 4.2}
                            </div>
                          )}
                        </div>
                        {stop.duration_mins && (
                          <div className="flex-shrink-0 text-right">
                            <span className="text-[10px] bg-slate-800 text-slate-300 font-mono font-bold px-2 py-0.5 rounded">
                              ⏱️ {stop.duration_mins} mins
                            </span>
                          </div>
                        )}
                      </Card>

                    </div>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-500 italic">No schedule slots mapped.</p>
          )}
        </div>

        {/* Sidebar panels */}
        <div className="lg:col-span-1 space-y-6">
          
          <Card className="text-center space-y-4">
            <h3 className="text-base font-bold text-white">Trip Navigator</h3>
            <p className="text-xs text-slate-400">Deploy live dashboard panel to track coordinates, speeds, and stops.</p>
            <Link
              to={`/start-trip?trip_id=${trip.id}&origin=${encodeURIComponent(trip.origin)}&destination=${encodeURIComponent(trip.destination)}&date=${trip.start_date}`}
              className="block"
            >
              <Button className="w-full">
                <Navigation className="w-4 h-4 fill-slate-950 animate-pulse" />
                Start Navigation
              </Button>
            </Link>
          </Card>

          {costBreakdown && (
            <Card className="space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-accent" />
                AI Cost Projections
              </h3>
              
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <XAxis dataKey="name" stroke="#94a3b8" fontSize={10} tickLine={false} />
                    <Tooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                    <Bar dataKey="cost" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-2 border-t border-slate-800 pt-3 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Fuel Estimate:</span>
                  <span className="text-white font-bold">₹{Math.round(costBreakdown.fuel_cost_inr)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Tolls Estimate:</span>
                  <span className="text-white font-bold">₹{Math.round(costBreakdown.toll_cost_inr)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Stay Estimate:</span>
                  <span className="text-white font-bold">₹{Math.round(costBreakdown.hotel_cost_inr)}</span>
                </div>
                <div className="flex justify-between border-t border-slate-800 pt-2 text-sm font-bold text-accent">
                  <span>Total Projections:</span>
                  <span>₹{Math.round(trip.total_cost_inr || 0)}</span>
                </div>
              </div>
            </Card>
          )}

        </div>

      </div>

    </div>
  );
}
