import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { ArrowLeft, ShoppingCart, CheckCircle, Navigation, DollarSign } from 'lucide-react';
import { foodAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Card from '../components/Card';
import Input from '../components/Input';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Skeleton from '../components/Skeleton';
import Speedometer from '../components/Speedometer';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-routing-machine';
import 'leaflet-routing-machine/dist/leaflet-routing-machine.css';

// Custom icon for the vehicle
const vehicleIcon = new L.Icon({
  iconUrl: '/icons.svg#car-top-view', // Assuming you have a car icon in your icons.svg
  iconSize: [30, 30],
  iconAnchor: [15, 15],
  className: 'bg-accent rounded-full p-1 shadow-lg pulse-glow-small'
});

// Predefined city coordinates for routing (simulated geocoding)
const cityCoordinates = {
  "mumbai": [19.0760, 72.8777],
  "pune": [18.5204, 73.8567],
  "jaipur": [26.9124, 75.7873],
  "delhi": [28.7041, 77.1025],
  "agra": [27.1767, 78.0081],
  "bengaluru": [12.9716, 77.5946],
  "chennai": [13.0827, 80.2707],
  "kolkata": [22.5726, 88.3639],
};

// Helper to get coordinates for a city name (case-insensitive)
const getCityCoords = (cityName) => {
  return cityCoordinates[cityName.toLowerCase()] || null;
};

export default function LiveTrip() {
  const location = useLocation();
  const { showToast } = useNotification();

  // Params
  const [tripId, setTripId] = useState('');
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');

  // Map & Telemetry State
  const mapRef = useRef(null);
  const vehicleMarkerRef = useRef(null);
  const routingControlRef = useRef(null);
  const [speed, setSpeed] = useState(80); 
  const [distance, setDistance] = useState('Calculating...'); 
  const [elapsedTime, setElapsedTime] = useState('Calculating...'); 
  const [eta, setEta] = useState('Calculating...'); 

  // GPS Simulation State (now follows the real route)
  const [currentPosition, setCurrentPosition] = useState(null);
  const [routeWaypoints, setRouteWaypoints] = useState([]); // Points from the routing machine
  const [currentStep, setCurrentStep] = useState(0);
  const simulationIntervalRef = useRef(null);

  // Partner Dhabas State
  const [dhabas, setDhabas] = useState([]);
  const [selectedDhaba, setSelectedDhaba] = useState(null);
  const [menu, setMenu] = useState([]);
  const [menuLoading, setMenuLoading] = useState(false);
  const [cart, setCart] = useState([]);
  const [orderStatus, setOrderStatus] = useState(null); // 'submitting' | 'confirmed'

  // Expenses State
  const [expenseForm, setExpenseForm] = useState({ title: '', spender: '', amount: '' });
  const [expenses, setExpenses] = useState([]);
  const [members, setMembers] = useState([]);
  const [newMember, setNewMember] = useState('');
  const [splits, setSplits] = useState([]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const id = params.get('trip_id') || '';
    const o = params.get('origin') || 'Mumbai';
    const d = params.get('destination') || 'Pune';
    setTripId(id);
    setOrigin(o);
    setDestination(d);

    setMembers(['Alice', 'Bob', 'Charlie']);
    setExpenses([
      { title: 'Highway Toll', spender: 'Alice', amount: 350 },
      { title: 'Breakfast Stop', spender: 'Bob', amount: 1200 },
    ]);

    // Add pulse-glow-small to document head if not present (ensures it's added only once)
    if (!document.querySelector('style[data-name="pulse-glow-small-style"]')) {
      const styleTag = document.createElement('style');
      styleTag.setAttribute('data-name', 'pulse-glow-small-style');
      styleTag.innerHTML = `
        @keyframes pulseGlowSmall {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.5);
          }
          50% {
            box-shadow: 0 0 0 4px rgba(245, 158, 11, 0);
          }
        }
        .pulse-glow-small {
          animation: pulseGlowSmall 1.5s infinite;
        }
      `;
      document.head.appendChild(styleTag);
    }

    // Fetch dhabas when origin/destination change. Route will be passed later.
    fetchDhabas(o);

  }, [location.search]);

  // Initialize and manage the Leaflet map and routing control
  useEffect(() => {
    if (mapRef.current) return; // Prevent re-initialization

    const map = L.map('map-container', { zoomControl: false }).setView([20.5937, 78.9629], 5); // Center on India
    L.control.zoom({ position: 'topright' }).addTo(map);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© CartoDB'
    }).addTo(map);

    mapRef.current = map;

    // Fix Leaflet tile loading inside flex container
    setTimeout(() => {
      map.invalidateSize();
    }, 100);

    const handleResize = () => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Setup routing when origin, destination, or map changes
  useEffect(() => {
    const map = mapRef.current;
    const startCoords = getCityCoords(origin);
    const endCoords = getCityCoords(destination);

    if (!map || !startCoords || !endCoords) return;

    // Clear previous routing control
    if (routingControlRef.current) {
      map.removeControl(routingControlRef.current);
    }

    // Create a new routing control
    routingControlRef.current = L.Routing.control({
      waypoints: [
        L.latLng(startCoords[0], startCoords[1]),
        L.latLng(endCoords[0], endCoords[1])
      ],
      router: L.Routing.osrmv1({ // Using OSRM demo server
        serviceUrl: 'https://router.project-osrm.org/route/v1'
      }),
      lineOptions: {
        styles: [{ color: '#f59e0b', weight: 5, opacity: 0.8 }]
      },
      createMarker: () => { return null; }, // Suppress default markers
      addWaypoints: false,
      draggableWaypoints: false,
      fitSelectedRoutes: true,
      show: false // Hide instructions panel
    }).addTo(map);

    routingControlRef.current.on('routesfound', (e) => {
      const routes = e.routes;
      if (routes.length > 0) {
        const route = routes[0];
        const coordinates = route.coordinates.map(coord => [coord.lat, coord.lng]);
        setRouteWaypoints(coordinates);
        setCurrentPosition(coordinates[0]);
        setCurrentStep(0);

        // Update telemetry with real route data
        setDistance((route.summary.totalDistance / 1000).toFixed(1) + ' km');
        const totalMinutes = route.summary.totalTime / 60;
        const hours = Math.floor(totalMinutes / 60);
        const minutes = Math.round(totalMinutes % 60);
        setElapsedTime(`${hours}h ${minutes}m`);
        setEta(`${hours}h ${minutes}m`); // ETA can be more complex, but for simulation, use total time

        // Clear existing vehicle marker if present
        if (vehicleMarkerRef.current) {
          map.removeLayer(vehicleMarkerRef.current);
          vehicleMarkerRef.current = null;
        }
        // Add vehicle marker to the start of the route
        vehicleMarkerRef.current = L.marker(coordinates[0], { icon: vehicleIcon }).addTo(map);

        // Start simulation along the new route
        if (simulationIntervalRef.current) {
          clearInterval(simulationIntervalRef.current);
        }
        simulationIntervalRef.current = setInterval(() => {
          setCurrentStep((prevStep) => {
            const nextStep = prevStep + 10; // Jump by more steps for faster simulation
            if (nextStep < coordinates.length) {
              setCurrentPosition(coordinates[nextStep]);
              return nextStep;
            } else {
              clearInterval(simulationIntervalRef.current);
              simulationIntervalRef.current = null;
              showToast("Trip simulation ended!", 'info');
              return prevStep; 
            }
          });
        }, 1000); // Update every 1 second

      } else {
        showToast('No route found between selected locations.', 'error');
        setRouteWaypoints([]);
        setCurrentPosition(null);
        setDistance('N/A');
        setElapsedTime('N/A');
        setEta('N/A');
      }
    });

    routingControlRef.current.on('routingerror', (e) => {
      console.error('Routing error:', e);
      showToast('Failed to calculate route. Please try again or check locations.', 'error');
      setRouteWaypoints([]);
      setCurrentPosition(null);
      setDistance('N/A');
      setElapsedTime('N/A');
      setEta('N/A');
    });

    return () => {
      if (simulationIntervalRef.current) {
        clearInterval(simulationIntervalRef.current);
        simulationIntervalRef.current = null;
      }
      if (routingControlRef.current) {
        map.removeControl(routingControlRef.current);
      }
    };
  }, [mapRef, origin, destination]); // Depend on origin/destination to re-calculate route

  // Update vehicle marker and map view when currentPosition changes
  useEffect(() => {
    if (vehicleMarkerRef.current && currentPosition) {
      vehicleMarkerRef.current.setLatLng(currentPosition);
      mapRef.current.panTo(currentPosition, { animate: true, duration: 1.5 }); 
    }
  }, [currentPosition]);

  // Add Dhaba markers along the calculated route
  useEffect(() => {
    const map = mapRef.current;
    if (!map || routeWaypoints.length === 0 || dhabas.length === 0) return;

    // Clear existing dhaba markers before adding new ones
    map.eachLayer((layer) => {
      if (layer instanceof L.Marker && layer.options.icon?.options?.html?.includes("🍴")) {
        map.removeLayer(layer);
      }
    });

    const dhabaIcon = L.divIcon({
      html: `<div class="bg-emerald-500 w-7 h-7 border-2 border-amber-400 rounded-full flex items-center justify-center text-xs shadow-lg pulse-glow cursor-pointer">🍴</div>`,
      className: '',
      iconSize: [28, 28]
    });

    // Place mock dhabas along the route coordinates if real dhabas are not available
    const placedDhabas = dhabas.map(d => {
      // For now, if d.latitude/longitude are missing, place them somewhat intelligently along the route
      if (!d.latitude || !d.longitude) {
        const randomRouteIndex = Math.floor(Math.random() * routeWaypoints.length);
        const [lat, lng] = routeWaypoints[randomRouteIndex];
        return { ...d, latitude: lat + (Math.random() - 0.5) * 0.02, longitude: lng + (Math.random() - 0.5) * 0.02 };
      }
      return d;
    });

    placedDhabas.forEach((d) => {
      const lat = parseFloat(d.latitude);
      const lng = parseFloat(d.longitude);
      if (isNaN(lat) || isNaN(lng)) return;

      const marker = L.marker([lat, lng], { icon: dhabaIcon }).addTo(map);
      marker.bindPopup(`<strong>🍴 ${d.name}</strong><br/>Partner Stop`);
      marker.on('click', () => {
        handleSelectDhaba(d);
      });
    });
  }, [dhabas, mapRef, routeWaypoints]);

  useEffect(() => {
    calculateSplits();
  }, [expenses, members]);

  const fetchDhabas = async (o) => {
    try {
      const res = await foodAPI.listRestaurants(o); // Attempt to fetch real dhabas near origin
      if (res.data && res.data.length > 0) {
        setDhabas(res.data);
      } else {
        throw new Error("No dhabas found via API, using mock data.");
      }
    } catch (err) {
      console.warn('Failed to load dhabas. Fallback to mock data.', err);
      // Mock dhabas will be placed in the Dhaba marker useEffect, along the route
      setDhabas([
        { id: 1, name: 'Sher-e-Punjab Dhaba', city: 'Lonavala', rating: 4.8, reviews_count: 320, address: 'Old Highway Toll St' },
        { id: 2, name: 'Golden Star Dhaba', city: 'Khandala', rating: 4.5, reviews_count: 154, address: 'Milestone 44' },
        { id: 3, name: 'Highway Foodies', city: 'Random', rating: 4.2, reviews_count: 80, address: 'NH-99' },
      ]);
    }
  };

  const handleSelectDhaba = async (dhaba) => {
    setSelectedDhaba(dhaba);
    setMenuLoading(true);
    setCart([]);
    setOrderStatus(null);
    try {
      const res = await foodAPI.getMenu(dhaba.id);
      setMenu(res.data.menu_items || []);
    } catch (err) {
      console.warn('Failed to load real restaurant menu. Fallback to mock.');
      setMenu([
        { id: 101, name: 'Paneer Butter Masala', price_inr: 240, description: 'Cottage cheese cubes in buttery rich gravy' },
        { id: 102, name: 'Butter Naan', price_inr: 45, description: 'Freshly baked tandoori wheat bread' },
        { id: 103, name: 'Jeera Rice', price_inr: 140, description: 'Fluffy basmati rice tempered with cumin seeds' },
      ]);
    } finally {
      setMenuLoading(false);
    }
  };

  const handleAddToCart = (item) => {
    setCart((prev) => {
      const existing = prev.find(i => i.id === item.id);
      if (existing) {
        return prev.map(i => i.id === item.id ? { ...i, qty: i.qty + 1 } : i);
      }
      return [...prev, { ...item, qty: 1 }];
    });
  };

  const handlePreOrder = async () => {
    setOrderStatus('submitting');
    try {
      const payload = {
        restaurant_id: selectedDhaba.id,
        items: cart.map(c => ({
          menu_item_id: c.id,
          name: c.name,
          quantity: c.qty,
          price: parseFloat(c.price_inr)
        })),
        total_amount: cart.reduce((sum, c) => sum + (c.price_inr * c.qty), 0),
        payment_method: 'prepaid',
        user_arrival_time_mins: 30
      };
      await foodAPI.createOrder(payload);
      setOrderStatus('confirmed');
      showToast(`Pre-order submitted to ${selectedDhaba.name}!`, 'success');
      setCart([]);
    } catch (err) {
      console.error('Failed to submit pre-order:', err);
      // Fallback checkout simulation in case of connection failure or sandbox constraints
      setTimeout(() => {
        setOrderStatus('confirmed');
        showToast(`Pre-order submitted to ${selectedDhaba.name}! (Simulated)`, 'success');
        setCart([]);
      }, 1000);
    }
  };

  const handleAddMember = () => {
    const trimmed = newMember.trim();
    if (!trimmed) {
      showToast('Please enter a traveler name.', 'error');
      return;
    }
    if (members.includes(trimmed)) {
      showToast('Traveler already added to the group.', 'error');
      return;
    }
    setMembers((prev) => [...prev, trimmed]);
    setNewMember('');
    showToast(`${trimmed} added to split`, 'info');
  };

  const handleAddExpense = (e) => {
    e.preventDefault();
    const { title, spender, amount } = expenseForm;
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      showToast('Expense description cannot be empty.', 'error');
      return;
    }
    if (!spender) {
      showToast('Please select who paid for the expense.', 'error');
      return;
    }
    const val = parseFloat(amount);
    if (isNaN(val) || val <= 0) {
      showToast('Expense amount must be a positive number.', 'error');
      return;
    }

    setExpenses((prev) => [...prev, { title: trimmedTitle, spender, amount: val }]);
    setExpenseForm({ title: '', spender: '', amount: '' });
    showToast('Expense logged successfully', 'success');
  };

  const calculateSplits = () => {
    if (members.length === 0) return;
    const total = expenses.reduce((sum, e) => sum + e.amount, 0);
    const share = total / members.length;

    const balances = {};
    members.forEach((m) => { balances[m] = 0; });
    expenses.forEach((e) => {
      balances[e.spender] += e.amount;
    });

    members.forEach((m) => {
      balances[m] -= share;
    });

    const debtors = [];
    const creditors = [];
    members.forEach((m) => {
      const bal = balances[m];
      if (bal < -0.01) debtors.push({ name: m, amount: -bal });
      if (bal > 0.01) creditors.push({ name: m, amount: bal });
    });

    const instructions = [];
    let dIdx = 0;
    let cIdx = 0;
    while (dIdx < debtors.length && cIdx < creditors.length) {
      const debtor = debtors[dIdx];
      const creditor = creditors[cIdx];
      const transfer = Math.min(debtor.amount, creditor.amount);

      instructions.push({
        from: debtor.name,
        to: creditor.name,
        amount: Math.round(transfer)
      });

      debtor.amount -= transfer;
      creditor.amount -= transfer;

      if (debtor.amount < 0.01) dIdx++;
      if (creditor.amount < 0.01) cIdx++;
    }
    setSplits(instructions);
  };

  return (
    <div className="relative flex flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden bg-primary-dark">
      
      {/* Sidebar HUD */}
      <div className="w-full lg:w-96 flex flex-col h-1/2 lg:h-full bg-primary border-r border-slate-800 overflow-y-auto z-10 text-left">
        
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-primary-light/50">
          <Link to="/dashboard" className="text-xs font-bold text-slate-400 hover:text-accent flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> Dashboard
          </Link>
          <span className="text-[10px] bg-accent/20 text-accent font-bold px-2 py-0.5 rounded border border-accent/30">
            Navigation Active
          </span>
        </div>

        {/* HUD Diagnostics */}
        <Card className="rounded-none border-t-0 border-x-0 border-b border-slate-800 space-y-4 bg-gradient-to-br from-primary-light/30 to-primary-dark/30">
          <div className="flex justify-between items-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">HUD Diagnostics</span>
          </div>
          <div className="flex items-center gap-6">
            <Speedometer speed={speed} />
            <div className="flex-grow space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Total Distance:</span>
                <span className="text-white font-bold">{distance}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Elapsed Time:</span>
                <span className="text-white font-bold">{elapsedTime}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">ETA to Dest:</span>
                <span className="text-white font-bold">{eta}</span>
              </div>
            </div>
          </div>
        </Card>

        {/* Split Expenses Widget */}
        <Card className="rounded-none border-t-0 border-x-0 border-b border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
            <DollarSign className="w-4 h-4 text-accent" />
            Group Expense Splitter
          </h3>
          
          <div className="flex gap-2">
            <Input
              value={newMember}
              onChange={(e) => setNewMember(e.target.value)}
              placeholder="Add traveler name..."
            />
            <Button onClick={handleAddMember} variant="secondary" className="h-[38px] px-3.5">
              Add
            </Button>
          </div>

          <form onSubmit={handleAddExpense} className="space-y-2.5">
            <Input
              required
              value={expenseForm.title}
              onChange={(e) => setExpenseForm(prev => ({ ...prev, title: e.target.value }))}
              placeholder="Expense Description (e.g. Fuel)"
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                value={expenseForm.spender}
                onChange={(e) => setExpenseForm(prev => ({ ...prev, spender: e.target.value }))}
                className="bg-primary-dark border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-100 outline-none"
              >
                <option value="">Paid By...</option>
                {members.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
              <Input
                required
                type="number"
                value={expenseForm.amount}
                onChange={(e) => setExpenseForm(prev => ({ ...prev, amount: e.target.value }))}
                placeholder="Amount (₹)"
              />
            </div>
            <Button type="submit" variant="secondary" className="w-full">
              Log Expense
            </Button>
          </form>

          {/* Transactions list */}
          <div className="pt-2 border-t border-slate-800 space-y-1.5">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Settlement view</h4>
            {splits.length > 0 ? (
              splits.map((s, idx) => (
                <div key={idx} className="text-xs text-emerald-400 font-medium">
                  💸 <strong>{s.from}</strong> owes <strong>{s.to}</strong>: ₹{s.amount}
                </div>
              ))
            ) : (
              <p className="text-[11px] text-slate-500 italic">No transactions generated yet.</p>
            )}
          </div>
        </Card>

      </div>

      {/* Leaflet Map */}
      <div className="flex-grow h-1/2 lg:h-full relative">
        <div id="map-container" className="w-full h-full" />
        
        <div className="absolute bottom-6 left-6 right-6 z-20 pointer-events-none hidden sm:block">
          <div className="max-w-xl mx-auto p-4 rounded-xl bg-primary/90 border border-slate-800 shadow-2xl backdrop-blur-md text-left flex justify-between items-center pointer-events-auto">
            <div>
              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider">GPS Diagnostics</span>
              <div className="text-xs text-white font-mono font-bold">
                {currentPosition ? `${currentPosition[0].toFixed(4)}° N, ${currentPosition[1].toFixed(4)}° E` : 'Waiting for GPS...'}
                {currentPosition && routeWaypoints.length > 0 && ` (Step ${currentStep + 1}/${routeWaypoints.length})`}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-xs text-slate-300 font-bold font-mono">Live GPS Lock</span>
            </div>
          </div>
        </div>

        {/* Selected Dhaba Modal */}
        <Modal
          isOpen={!!selectedDhaba}
          onClose={() => setSelectedDhaba(null)}
          title={`🍴 ${selectedDhaba?.name || 'Restaurant'}`}
        >
          {menuLoading ? (
            <Skeleton className="h-12 w-full" count={3} />
          ) : orderStatus === 'confirmed' ? (
            <div className="text-center py-6 space-y-3">
              <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto animate-bounce" />
              <div className="space-y-1">
                <h4 className="text-sm font-black text-white">Order Confirmed!</h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto">
                  Prep is active. ETA at Dhaba in 40 mins.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-xs text-slate-400">Select items to pre-order:</div>
              <div className="space-y-2">
                {menu.map((item) => (
                  <div key={item.id} className="p-3 rounded-xl bg-primary-dark/60 border border-slate-800 flex justify-between items-center text-xs">
                    <div className="space-y-0.5">
                      <strong className="text-white">{item.name}</strong>
                      <p className="text-[10px] text-slate-400">{item.description}</p>
                      <span className="text-emerald-400 font-bold">₹{item.price_inr}</span>
                    </div>
                    <Button onClick={() => handleAddToCart(item)} variant="secondary" className="px-3.5 py-1">
                      + Add
                    </Button>
                  </div>
                ))}
              </div>

              {cart.length > 0 && (
                <div className="pt-4 border-t border-slate-800 space-y-3">
                  <h4 className="text-xs font-black text-white flex items-center gap-1.5">
                    <ShoppingCart className="w-4 h-4 text-accent" />
                    Pre-Order Cart
                  </h4>
                  <div className="space-y-1.5 text-xs text-slate-300">
                    {cart.map((c) => (
                      <div key={c.id} className="flex justify-between">
                        <span>{c.name} (x{c.qty})</span>
                        <span>₹{c.price_inr * c.qty}</span>
                      </div>
                    ))}
                  </div>
                  <Button onClick={handlePreOrder} className="w-full">
                    Confirm & Pre-Pay
                  </Button>
                </div>
              )}
            </div>
          )}
        </Modal>

      </div>

    </div>
  );
}
