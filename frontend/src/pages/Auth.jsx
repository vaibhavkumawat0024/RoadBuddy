import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, User, Phone, ShieldAlert, ArrowRight, Compass, Truck, Store } from 'lucide-react';
import { unifiedAuthAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Button from '../components/Button';
import Input from '../components/Input';
import Card from '../components/Card';

export default function Auth({ onLoginSuccess }) {
  const [role, setRole] = useState('traveler'); // 'traveler' | 'provider' | 'food_provider'
  const [mode, setMode] = useState('login'); // 'login' | 'signup'

  // Input Fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Role-Specific Fields
  const [companyName, setCompanyName] = useState('');
  const [fleetType, setFleetType] = useState('cab');
  const [restaurantName, setRestaurantName] = useState('');
  const [location, setLocation] = useState('');
  const [licenseNumber, setLicenseNumber] = useState('');

  // UI States
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const navigate = useNavigate();
  const { showToast } = useNotification();

  const validateForm = () => {
    const errors = {};
    if (!email.includes('@')) {
      errors.email = 'Please enter a valid email address.';
    }
    if (password.length < 6) {
      errors.password = 'Password must be at least 6 characters.';
    }
    if (mode === 'signup') {
      if (!name.trim()) {
        errors.name = 'Full Name is required.';
      }
      if (password !== confirmPassword) {
        errors.confirmPassword = 'Passwords do not match.';
      }
      if (role === 'provider' && !companyName.trim()) {
        errors.companyName = 'Fleet or Company Name is required.';
      }
      if (role === 'food_provider' && !restaurantName.trim()) {
        errors.restaurantName = 'Dhaba / Restaurant name is required.';
      }
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');
    if (!validateForm()) return;

    setLoading(true);
    try {
      if (mode === 'login') {
        const res = await unifiedAuthAPI.login(role, email, password);
        onLoginSuccess(res.data);
        showToast(`Welcome back to RoadBuddy!`, 'success');
        
        if (role === 'traveler') navigate('/dashboard');
        else if (role === 'provider') navigate('/provider');
        else if (role === 'food_provider') navigate('/food-provider');
      } else {
        const payload = {
          role,
          name,
          email,
          phone: phone || null,
          password,
          company_name: role === 'provider' ? companyName : null,
          fleet_type: role === 'provider' ? fleetType : null,
          restaurant_name: role === 'food_provider' ? restaurantName : null,
          location: role === 'food_provider' ? location : null,
          license_number: role === 'food_provider' ? licenseNumber : null
        };
        await unifiedAuthAPI.signup(payload);
        showToast('Account registered successfully!', 'success');
        
        // Auto-login
        const loginRes = await unifiedAuthAPI.login(role, email, password);
        onLoginSuccess(loginRes.data);
        
        if (role === 'traveler') navigate('/dashboard');
        else if (role === 'provider') navigate('/provider');
        else if (role === 'food_provider') navigate('/food-provider');
      }
    } catch (err) {
      console.error('Auth error:', err);
      const detail = err.response?.data?.detail || 'Authentication failed. Please verify your credentials.';
      setApiError(detail);
      showToast(detail, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-primary-dark px-4 py-12 relative text-left">
      <div className="absolute w-72 h-72 rounded-full bg-accent/5 filter blur-3xl -top-10 -left-10" />
      <div className="absolute w-72 h-72 rounded-full bg-indigo-500/5 filter blur-3xl -bottom-10 -right-10" />

      <Card className="max-w-lg w-full space-y-6 bg-primary-light/40 backdrop-blur-lg">
        
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center justify-center gap-1.5">
            <Compass className="w-6 h-6 text-accent" />
            RoadBuddy Portal
          </h2>
          <p className="text-xs text-slate-400">Select your role to access the cockpit.</p>
        </div>

        {/* Role Segmented Tabs */}
        <div className="grid grid-cols-3 bg-primary-dark/80 p-1 rounded-xl border border-slate-800">
          {[
            { id: 'traveler', label: 'Traveler', icon: Compass },
            { id: 'provider', label: 'Logistics', icon: Truck },
            { id: 'food_provider', label: 'Dhaba', icon: Store }
          ].map((r) => {
            const Icon = r.icon;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => { setRole(r.id); setApiError(''); }}
                className={`py-2 rounded-lg text-xs font-bold transition-all flex flex-col sm:flex-row items-center justify-center gap-1 cursor-pointer ${
                  role === r.id
                    ? 'bg-accent text-slate-950 shadow-md font-black'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{r.label}</span>
              </button>
            );
          })}
        </div>

        {/* Toggle Mode */}
        <div className="flex border-b border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => { setMode('login'); setApiError(''); }}
            className={`flex-1 py-2 text-center font-bold uppercase tracking-wider border-b-2 cursor-pointer transition-all ${
              mode === 'login' ? 'border-accent text-accent font-black' : 'border-transparent text-slate-400'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('signup'); setApiError(''); }}
            className={`flex-1 py-2 text-center font-bold uppercase tracking-wider border-b-2 cursor-pointer transition-all ${
              mode === 'signup' ? 'border-accent text-accent font-black' : 'border-transparent text-slate-400'
            }`}
          >
            Sign Up
          </button>
        </div>

        {/* Error banner */}
        {apiError && (
          <div className="p-3.5 rounded-xl bg-rose-955/35 border border-rose-500/20 text-rose-300 text-xs font-semibold flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>{apiError}</span>
          </div>
        )}

        {/* Auth form */}
        <form className="space-y-4" onSubmit={handleSubmit}>
          
          {mode === 'signup' && (
            <Input
              label="Full Name"
              error={validationErrors.name}
              icon={User}
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Doe"
            />
          )}

          <Input
            label="Email Address"
            error={validationErrors.email}
            icon={Mail}
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />

          {mode === 'signup' && (
            <Input
              label="Phone Number (Optional)"
              icon={Phone}
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+91 98765 43210"
            />
          )}

          <div className="grid sm:grid-cols-2 gap-4">
            <Input
              label="Password"
              error={validationErrors.password}
              icon={Lock}
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            {mode === 'signup' ? (
              <Input
                label="Confirm Password"
                error={validationErrors.confirmPassword}
                icon={Lock}
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
              />
            ) : (
              <div className="flex items-center justify-end pt-5">
                <a href="#forgot" className="text-[11px] text-slate-400 hover:underline font-bold">Forgot Password?</a>
              </div>
            )}
          </div>

          {/* Role specific inputs */}
          {mode === 'signup' && role === 'provider' && (
            <div className="p-4 rounded-xl bg-primary-dark/50 border border-slate-800 space-y-4 animate-fade-in-up">
              <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Fleet Partner Credentials</div>
              
              <Input
                label="Fleet / Company Name"
                error={validationErrors.companyName}
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Express Cabs Pvt Ltd"
              />

              <div className="space-y-1 text-left">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Fleet Type</label>
                <select
                  value={fleetType}
                  onChange={(e) => setFleetType(e.target.value)}
                  className="w-full bg-primary-dark border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none"
                >
                  <option value="cab">🚕 Cab Service</option>
                  <option value="bus">🚌 Bus Lines</option>
                  <option value="train">🚆 Train Route</option>
                  <option value="flight">✈️ Flight Operator</option>
                </select>
              </div>
            </div>
          )}

          {mode === 'signup' && role === 'food_provider' && (
            <div className="p-4 rounded-xl bg-primary-dark/50 border border-slate-800 space-y-4 animate-fade-in-up">
              <div className="text-[10px] font-bold text-accent uppercase tracking-widest">Dhaba Partner Credentials</div>
              
              <Input
                label="Dhaba / Restaurant Name"
                error={validationErrors.restaurantName}
                required
                value={restaurantName}
                onChange={(e) => setRestaurantName(e.target.value)}
                placeholder="e.g. Sher-e-Punjab Dhaba"
              />

              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  label="Location / City"
                  required
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="e.g. Lonavala"
                />
                <Input
                  label="FSSAI License (Optional)"
                  value={licenseNumber}
                  onChange={(e) => setLicenseNumber(e.target.value)}
                  placeholder="e.g. 12345678901234"
                />
              </div>
            </div>
          )}

          {/* Submit */}
          <Button
            type="submit"
            disabled={loading}
            className="w-full"
          >
            {loading ? 'Authenticating...' : mode === 'login' ? 'Confirm Cabin access' : 'Register Cockpit Account'}
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>

        </form>

      </Card>
    </div>
  );
}
