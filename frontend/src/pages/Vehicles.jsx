import React, { useState, useEffect } from 'react';
import { Trash2, Plus, Car } from 'lucide-react';
import { vehiclesAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';

export default function Vehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  
  // Add Form State
  const [name, setName] = useState('');
  const [fuelType, setFuelType] = useState('petrol');
  const [category, setCategory] = useState('car');
  const [mileage, setMileage] = useState('');

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
    setLoading(true);
    try {
      const res = await vehiclesAPI.list();
      if (isMounted.current) {
        setVehicles(res.data || []);
      }
    } catch (err) {
      console.warn('API vehicle sync failed. Fallback to mock data.');
      if (isMounted.current) {
        setVehicles([
          { id: 1, name: 'Kia Seltos SUV', fuel_type: 'petrol', category: 'suv', mileage_kmpl: 14 },
          { id: 2, name: 'Maruti Swift LXI', fuel_type: 'diesel', category: 'car', mileage_kmpl: 20 },
        ]);
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      showToast('Please enter a valid vehicle name.', 'error');
      return;
    }
    const val = parseFloat(mileage);
    if (isNaN(val) || val <= 0) {
      showToast('Mileage must be a positive number.', 'error');
      return;
    }

    setActionLoading(true);
    try {
      const payload = {
        name: trimmedName,
        fuel_type: fuelType,
        category,
        mileage_kmpl: val
      };
      const res = await vehiclesAPI.create(payload);
      if (isMounted.current) {
        setVehicles(prev => [...prev, res.data || { id: Date.now(), ...payload }]);
        setName('');
        setMileage('');
        showToast('Vehicle synchronized successfully', 'success');
      }
    } catch (err) {
      const payload = { name: trimmedName, fuel_type: fuelType, category, mileage_kmpl: val };
      const mockObj = { id: Date.now(), ...payload };
      if (isMounted.current) {
        setVehicles(prev => [...prev, mockObj]);
        setName('');
        setMileage('');
        showToast('Saved mock vehicle profile', 'info');
      }
    } finally {
      if (isMounted.current) {
        setActionLoading(false);
      }
    }
  };

  const handleDeleteVehicle = async (id) => {
    if (!window.confirm('Remove this vehicle profile from your garage?')) return;
    try {
      await vehiclesAPI.delete(id);
      if (isMounted.current) {
        setVehicles(prev => prev.filter(v => v.id !== id));
        showToast('Vehicle removed successfully', 'info');
      }
    } catch (err) {
      if (isMounted.current) {
        setVehicles(prev => prev.filter(v => v.id !== id));
        showToast('Mock vehicle removed', 'info');
      }
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-2">
          <Car className="w-8 h-8 text-accent" />
          Vehicle Garage
        </h1>
        <p className="text-xs text-slate-400">Configure your personal vehicles KMPL parameters for accurate fuel estimations.</p>
      </div>

      {/* Main Grid */}
      <div className="grid md:grid-cols-3 gap-8">
        
        {/* Left Form: Add Vehicle */}
        <Card className="md:col-span-1 h-fit space-y-4">
          <h3 className="text-base font-bold text-white flex items-center gap-1">
            <Plus className="w-4.5 h-4.5 text-accent" />
            Add Vehicle
          </h3>
          <form onSubmit={handleAddVehicle} className="space-y-4">
            <Input
              label="Name / Model"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Honda City"
            />
            <div className="space-y-1 text-left">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Fuel Type</label>
              <select
                value={fuelType}
                onChange={(e) => setFuelType(e.target.value)}
                className="w-full bg-primary-dark border border-slate-700 rounded-xl px-3 py-2.5 text-xs text-slate-100 outline-none focus:border-accent"
              >
                <option value="petrol">Petrol</option>
                <option value="diesel">Diesel</option>
                <option value="cng">CNG</option>
                <option value="electric">Electric (EV)</option>
              </select>
            </div>
            <div className="space-y-1 text-left">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-primary-dark border border-slate-700 rounded-xl px-3 py-2.5 text-xs text-slate-100 outline-none focus:border-accent"
              >
                <option value="car">Car (Sedan/Hatchback)</option>
                <option value="suv">SUV</option>
                <option value="van">Van</option>
                <option value="two_wheeler">Two Wheeler</option>
              </select>
            </div>
            <Input
              label="Mileage (KMPL / Range per Charge)"
              type="number"
              required
              min={1}
              value={mileage}
              onChange={(e) => setMileage(e.target.value)}
              placeholder="e.g. 16"
            />
            <Button type="submit" disabled={actionLoading} className="w-full">
              {actionLoading ? 'Syncing...' : 'Sync Vehicle'}
            </Button>
          </form>
        </Card>

        {/* Right List: Garage */}
        <Card className="md:col-span-2 space-y-4">
          <h3 className="text-base font-bold text-white">Registered Garage</h3>

          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" count={2} />
            </div>
          ) : vehicles.length > 0 ? (
            <div className="grid sm:grid-cols-2 gap-4">
              {vehicles.map((v) => (
                <div
                  key={v.id}
                  className="p-4 rounded-xl bg-primary-dark/60 border border-slate-800 flex justify-between items-center hover:border-slate-700 transition-all"
                >
                  <div className="space-y-0.5 text-left">
                    <strong className="text-xs text-white">{v.name}</strong>
                    <div className="text-[10px] text-slate-400">
                      Fuel: {v.fuel_type} · Mileage: {v.mileage_kmpl} KMPL
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteVehicle(v.id)}
                    className="p-2 bg-slate-800 hover:bg-rose-950/40 text-slate-500 hover:text-rose-400 rounded-lg transition-colors cursor-pointer"
                    title="Remove Profile"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center bg-primary-dark/30 rounded-xl border border-dashed border-slate-800">
              <p className="text-xs text-slate-500">No vehicle profiles currently mapped.</p>
            </div>
          )}
        </Card>

      </div>

    </div>
  );
}
