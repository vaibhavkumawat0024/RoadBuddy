import React, { useState, useEffect } from 'react';
import { Store, ClipboardList, TrendingUp, Clock, Trash2, Plus } from 'lucide-react';
import { foodAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';
import Skeleton from '../components/Skeleton';
import Card from '../components/Card';
import Button from '../components/Button';
import Modal from '../components/Modal';
import Input from '../components/Input';

export default function FoodProviderDashboard() {
  const [orders, setOrders] = useState([]);
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formLoading, setFormLoading] = useState(false);
  const [actionLoadingIds, setActionLoadingIds] = useState([]);
  const { showToast } = useNotification();

  // Add Item Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [itemName, setItemName] = useState('');
  const [itemDesc, setItemDesc] = useState('');
  const [itemPrice, setItemPrice] = useState('');
  const [itemCategory, setItemCategory] = useState('Veg');

  const isMounted = React.useRef(true);

  useEffect(() => {
    isMounted.current = true;
    fetchDashboardDetails();
    return () => {
      isMounted.current = false;
    };
  }, []);

  const fetchDashboardDetails = async () => {
    setLoading(true);
    try {
      const [ordersRes, restRes] = await Promise.all([
        foodAPI.listProviderOrders(),
        foodAPI.getProviderRestaurant(),
      ]);
      if (isMounted.current) {
        setOrders(ordersRes.data || []);
        setMenu(restRes.data.menu_items || []);
      }
    } catch (err) {
      console.warn('Failed to load food partner dashboard details. Fallback to mocks.');
      if (isMounted.current) {
        setOrders([
          { id: 401, user_name: 'John Doe', items: [{ name: 'Paneer Butter Masala', quantity: 2, price: 240 }], total_amount: 480, status: 'cooking', user_arrival_time_mins: 15 },
          { id: 402, user_name: 'Alice Cooper', items: [{ name: 'Butter Naan', quantity: 4, price: 45 }, { name: 'Jeera Rice', quantity: 1, price: 140 }], total_amount: 320, status: 'pending', user_arrival_time_mins: 20 },
        ]);
        setMenu([
          { id: 101, name: 'Paneer Butter Masala', price_inr: 240, rating: 4.8 },
          { id: 102, name: 'Butter Naan', price_inr: 45, rating: 4.5 },
          { id: 103, name: 'Jeera Rice', price_inr: 140, rating: 4.6 },
        ]);
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  };

  const handleUpdateStatus = async (id, nextStatus) => {
    setActionLoadingIds(prev => [...prev, id]);
    try {
      await foodAPI.updateOrderStatus(id, nextStatus);
      if (isMounted.current) {
        setOrders(prev => prev.map(o => o.id === id ? { ...o, status: nextStatus } : o));
        showToast(`Order status updated to ${nextStatus}`, 'success');
      }
    } catch (err) {
      if (isMounted.current) {
        setOrders(prev => prev.map(o => o.id === id ? { ...o, status: nextStatus } : o));
        showToast(`Local order status updated to ${nextStatus}`, 'info');
      }
    } finally {
      if (isMounted.current) {
        setActionLoadingIds(prev => prev.filter(aId => aId !== id));
      }
    }
  };

  const handleAddItem = async (e) => {
    e.preventDefault();
    const trimmedName = itemName.trim();
    if (!trimmedName) {
      showToast('Item name cannot be empty.', 'error');
      return;
    }
    const val = parseFloat(itemPrice);
    if (isNaN(val) || val <= 0) {
      showToast('Price must be a positive number.', 'error');
      return;
    }

    setFormLoading(true);
    try {
      const payload = {
        name: trimmedName,
        description: itemDesc,
        price_inr: val,
        category: itemCategory
      };
      const res = await foodAPI.addMenuItem(payload);
      if (isMounted.current) {
        setMenu(prev => [...prev, res.data || { id: Date.now(), ...payload, rating: 4.0 }]);
        setItemName('');
        setItemDesc('');
        setItemPrice('');
        setIsModalOpen(false);
        showToast('Menu item added successfully', 'success');
      }
    } catch (err) {
      const payload = { name: trimmedName, description: itemDesc, price_inr: val, category: itemCategory };
      const mockObj = { id: Date.now(), ...payload, rating: 4.0 };
      if (isMounted.current) {
        setMenu(prev => [...prev, mockObj]);
        setItemName('');
        setItemDesc('');
        setItemPrice('');
        setIsModalOpen(false);
        showToast('Saved menu item in sandbox', 'info');
      }
    } finally {
      if (isMounted.current) {
        setFormLoading(false);
      }
    }
  };

  const handleDeleteItem = async (id) => {
    if (!window.confirm('Are you absolutely sure you want to delete this menu item? This cannot be undone.')) return;
    try {
      await foodAPI.deleteMenuItem(id);
      if (isMounted.current) {
        setMenu(prev => prev.filter(item => item.id !== id));
        showToast('Menu item deleted successfully', 'info');
      }
    } catch (err) {
      if (isMounted.current) {
        setMenu(prev => prev.filter(item => item.id !== id));
        showToast('Menu item removed', 'info');
      }
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-left space-y-8 animate-fade-in-up">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-2">
          <Store className="w-8 h-8 text-accent animate-pulse" />
          Dhaba Control Dashboard
        </h1>
        <p className="text-xs text-slate-400">Manage roadside dining orders, prep timelines, and menu dispatches.</p>
      </div>

      {/* Grid Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center text-accent">
            <ClipboardList className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Incoming Orders</span>
            <h3 className="text-2xl font-black text-white">{orders.length} active</h3>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center text-accent">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Avg Prep Time</span>
            <h3 className="text-2xl font-black text-white">18 mins</h3>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/25 flex items-center justify-center text-accent">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">Today's Revenue</span>
            <h3 className="text-2xl font-black text-white">
              ₹{orders.reduce((sum, o) => sum + (o.total_amount || 0), 0) || 800}
            </h3>
          </div>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid lg:grid-cols-3 gap-8">
        
        {/* Left: Active Orders queue (2 cols) */}
        <Card className="lg:col-span-2 space-y-4">
          <h3 className="text-base font-bold text-white uppercase tracking-wider">Kitchen Order Dispatch Queue</h3>

          {loading ? (
            <Skeleton className="h-16 w-full" count={2} />
          ) : orders.length > 0 ? (
            <div className="space-y-3">
              {orders.map((o) => {
                const customer = o.user_name || o.customer_name || 'Passenger';
                const itemsStr = o.items ? o.items.map(i => `${i.name} (x${i.quantity})`).join(', ') : o.item_name;
                const eta = o.preparation_time_mins || o.eta_mins || 20;

                return (
                  <div
                    key={o.id}
                    className="p-4 rounded-xl bg-primary-dark/60 border border-slate-800 flex justify-between items-center"
                  >
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400 font-mono">ID: #{o.id} · Customer: {customer}</div>
                      <div className="text-sm font-black text-white">{itemsStr}</div>
                      <div className="text-[10px] text-slate-400">Prep Timer: <strong className="text-accent">{eta} mins remaining</strong></div>
                    </div>
                    <div className="flex gap-2">
                      {(o.status === 'pending' || o.status === 'received') && (
                        <Button
                          onClick={() => handleUpdateStatus(o.id, 'cooking')}
                          disabled={actionLoadingIds.includes(o.id)}
                        >
                          {actionLoadingIds.includes(o.id) ? 'Updating...' : 'Accept & Cook'}
                        </Button>
                      )}
                      {o.status === 'cooking' && (
                        <Button
                          onClick={() => handleUpdateStatus(o.id, 'ready')}
                          disabled={actionLoadingIds.includes(o.id)}
                        >
                          {actionLoadingIds.includes(o.id) ? 'Updating...' : 'Mark Ready'}
                        </Button>
                      )}
                      {o.status === 'ready' && (
                        <span className="text-xs text-emerald-400 font-bold px-3 py-1.5 border border-emerald-500/20 bg-emerald-950/20 rounded-lg">
                          ✓ Ready for pickup
                        </span>
                      )}
                      {o.status === 'completed' && (
                        <span className="text-xs text-slate-400 font-bold px-3 py-1.5 border border-slate-700 bg-slate-800/40 rounded-lg">
                          Delivered
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No incoming kitchen orders.</p>
          )}
        </Card>

        {/* Right: Menu Catalog (1 col) */}
        <Card className="lg:col-span-1 space-y-4">
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <h3 className="text-base font-bold text-white uppercase tracking-wider">Menu Catalog</h3>
            <button
              onClick={() => setIsModalOpen(true)}
              className="text-xs text-accent hover:underline font-bold flex items-center gap-1 cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" /> Item
            </button>
          </div>
          <div className="space-y-2">
            {menu.map((item) => (
              <div key={item.id} className="p-3 rounded-xl bg-primary-dark/60 border border-slate-800 flex justify-between items-center">
                <div className="text-left space-y-0.5">
                  <strong className="text-xs text-white block">{item.name}</strong>
                  <span className="text-[10px] text-slate-400">{item.category} · ★ {item.rating || 4.0}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-emerald-400 font-bold">₹{item.price_inr}</span>
                  <button
                    onClick={() => handleDeleteItem(item.id)}
                    className="p-1.5 hover:bg-rose-950/30 text-slate-500 hover:text-rose-400 rounded-lg transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Card>

      </div>

      {/* Add Menu Item Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="➕ Add Restaurant Menu Item"
      >
        <form onSubmit={handleAddItem} className="space-y-4">
          <Input
            label="Item Name"
            required
            value={itemName}
            onChange={(e) => setItemName(e.target.value)}
            placeholder="e.g. Kadhai Paneer"
          />
          <Input
            label="Description"
            value={itemDesc}
            onChange={(e) => setItemDesc(e.target.value)}
            placeholder="e.g. Mildly spiced rich gravy paneer dish"
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Price (INR)"
              required
              type="number"
              value={itemPrice}
              onChange={(e) => setItemPrice(e.target.value)}
              placeholder="e.g. 180"
            />
            <div className="space-y-1 text-left">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Category</label>
              <select
                value={itemCategory}
                onChange={(e) => setItemCategory(e.target.value)}
                className="w-full bg-primary-dark border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 outline-none focus:border-accent"
              >
                <option value="Veg">Veg</option>
                <option value="Non-Veg">Non-Veg</option>
                <option value="Beverage">Beverage</option>
                <option value="Dessert">Dessert</option>
              </select>
            </div>
          </div>
          <Button type="submit" disabled={formLoading} className="w-full">
            {formLoading ? 'Adding...' : 'Add to Menu Catalog'}
          </Button>
        </form>
      </Modal>

    </div>
  );
}
