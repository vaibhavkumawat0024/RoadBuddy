import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { CalendarDays, MapPin, DollarSign, Loader2, Sparkles } from 'lucide-react';
import { tripsAPI, vehiclesAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';

export default function TripPlanner() {
  const [vehicles, setVehicles] = useState([]);
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [budget, setBudget] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [travelMode, setTravelMode] = useState('own_vehicle');
  const [vehicleId, setVehicleId] = useState('');
  const [numPeople, setNumPeople] = useState(1);
  const [groupType, setGroupType] = useState('solo');

  const [loading, setLoading] = useState(false);
  const [vehiclesLoading, setVehiclesLoading] = useState(true);

  const navigate = useNavigate();
  const { showToast } = useNotification();

  const isMounted = React.useRef(true);

  useEffect(() => {
    isMounted.current = true;
    fetchVehicles();
    return () => {
      isMounted.current = false;
    };
  }, []);

  const fetchVehicles = async () => {
    try {
      const res = await vehiclesAPI.list();
      if (isMounted.current) {
        setVehicles(res.data || []);
        if (res.data && res.data.length > 0) {
          setVehicleId(res.data[0].id.toString());
        }
      }
    } catch (err) {
      console.warn('Failed to load user vehicles', err);
    } finally {
      if (isMounted.current) {
        setVehiclesLoading(false);
      }
    }
  };

  const handleCreateTrip = async (e) => {
    e.preventDefault();
    const trimmedOrigin = origin.trim();
    const trimmedDest = destination.trim();
    if (!trimmedOrigin || !trimmedDest) {
      showToast('Starting point and Destination cannot be empty.', 'error');
      return;
    }
    const budgetVal = parseFloat(budget);
    if (isNaN(budgetVal) || budgetVal <= 0) {
      showToast('Trip budget must be a positive number.', 'error');
      return;
    }
    const peopleVal = parseInt(numPeople);
    if (isNaN(peopleVal) || peopleVal < 1) {
      showToast('Number of travelers must be at least 1.', 'error');
      return;
    }
    if (travelMode === 'own_vehicle' && !vehicleId) {
      showToast('Please register a vehicle in your Garage first, or choose another travel mode.', 'error');
      return;
    }

    setLoading(true);
    showToast('Consulting RoadBuddy AI routing engine...', 'info');

    const payload = {
      origin: trimmedOrigin,
      destination: trimmedDest,
      budget_inr: budgetVal,
      start_date: startDate,
      end_date: endDate || null,
      travel_mode: travelMode,
      num_people: peopleVal,
      vehicle_id: travelMode === 'own_vehicle' ? vehicleId.toString() : null,
      group_type: groupType,
    };

    try {
      const res = await tripsAPI.generate(payload);
      if (isMounted.current) {
        showToast('Trip itinerary generated successfully!', 'success');
        navigate(`/my-trips/${res.data.id}/itinerary`);
      }
    } catch (err) {
      console.error('Itinerary generation failed:', err);
      const detail = err.response?.data?.detail || 'Failed to generate itinerary. Please try again.';
      if (isMounted.current) {
        showToast(detail, 'error');
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 text-left space-y-8">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-2">
          <Sparkles className="w-8 h-8 text-accent fill-accent animate-pulse" />
          AI Route Configurator
        </h1>
        <p className="text-xs text-slate-400">Configure parameters to deploy neural path schedules.</p>
      </div>

      {loading ? (
        <Card className="p-8 shadow-xl space-y-6 text-center py-16">
          <div className="flex justify-center">
            <Loader2 className="w-12 h-12 text-accent animate-spin" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-black text-white">Synthesizing Safety Itinerary...</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Our Llama 3 engine is configuring route waypoints, weather hazards, and verified food partner stops along the highway.
            </p>
          </div>
          <div className="max-w-md mx-auto">
            <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
              <div className="h-full bg-accent animate-pulse-progress w-[65%]" />
            </div>
          </div>
        </Card>
      ) : (
        <Card>
          <form onSubmit={handleCreateTrip} className="space-y-6">
            
            {/* Origin & Destination */}
            <div className="grid sm:grid-cols-2 gap-4">
              <Input
                label="Starting point"
                required
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                icon={MapPin}
                placeholder="e.g. Mumbai"
              />
              <Input
                label="Destination"
                required
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                icon={MapPin}
                placeholder="e.g. Pune"
              />
            </div>

            {/* Dates */}
            <div className="grid sm:grid-cols-2 gap-4">
              <Input
                label="Start Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                icon={CalendarDays}
              />
              <Input
                label="End Date (Optional)"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                icon={CalendarDays}
              />
            </div>

            {/* Budget, People & Group Type */}
            <div className="grid sm:grid-cols-3 gap-4">
              <Input
                label="Trip Budget (INR)"
                type="number"
                required
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                icon={DollarSign}
                placeholder="Total budget e.g. 15000"
              />
              <Input
                label="Number of Travelers"
                type="number"
                required
                min={1}
                value={numPeople}
                onChange={(e) => setNumPeople(e.target.value)}
              />
              <div className="space-y-1 text-left">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Group Type</label>
                <select
                  value={groupType}
                  onChange={(e) => setGroupType(e.target.value)}
                  className="w-full bg-primary-dark border border-slate-700 rounded-xl py-2.5 px-4 text-xs text-slate-100 outline-none focus:border-accent"
                >
                  <option value="solo">Solo Explorer</option>
                  <option value="couple">Couple</option>
                  <option value="family">Family Trip</option>
                  <option value="friends">Friends / Group</option>
                </select>
              </div>
            </div>

            {/* Travel Mode & Vehicle */}
            <div className="grid sm:grid-cols-2 gap-4 text-left">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Travel Mode</label>
                <select
                  value={travelMode}
                  onChange={(e) => setTravelMode(e.target.value)}
                  className="w-full bg-primary-dark border border-slate-700 rounded-xl py-2.5 px-4 text-xs text-slate-100 outline-none focus:border-accent"
                >
                  <option value="own_vehicle">🚗 Own Vehicle (GPS mode)</option>
                  <option value="bus">🚌 Public Transport — Bus</option>
                  <option value="train">🚆 Public Transport — Train</option>
                  <option value="flight">✈️ Public Transport — Flight</option>
                  <option value="cab">🚕 Reserve Marketplace Cab</option>
                </select>
              </div>

              {travelMode === 'own_vehicle' && (
                <div className="space-y-1 animate-fade-in-up">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Select Vehicle</label>
                  {vehiclesLoading ? (
                    <Skeleton className="h-10 w-full" />
                  ) : vehicles.length > 0 ? (
                    <select
                      value={vehicleId}
                      onChange={(e) => setVehicleId(e.target.value)}
                      className="w-full bg-primary-dark border border-slate-700 rounded-xl py-2.5 px-4 text-xs text-slate-100 outline-none focus:border-accent"
                    >
                      {vehicles.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.name} ({v.fuel_type} · {v.mileage_kmpl} KMPL)
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="text-xs text-amber-500 font-semibold py-2">
                      No vehicles found. <Link to="/vehicles" className="underline text-accent">Add vehicle</Link> first.
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Submit */}
            <Button
              type="submit"
              disabled={loading || (travelMode === 'own_vehicle' && vehicles.length === 0)}
              className="w-full"
            >
              Deploy AI Configurator
              <Sparkles className="w-4 h-4 fill-slate-950 animate-pulse" />
            </Button>

          </form>
        </Card>
      )}

    </div>
  );
}
