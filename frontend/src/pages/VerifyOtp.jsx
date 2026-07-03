import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MailCheck, ShieldAlert, ArrowRight } from 'lucide-react';
import { authAPI } from '../api/client';
import { useNotification } from '../context/NotificationContext';

export default function VerifyOtp() {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const location = useLocation();
  const navigate = useNavigate();
  const { showToast } = useNotification();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const emailParam = params.get('email');
    if (emailParam) {
      setEmail(emailParam);
    } else {
      navigate('/register');
    }
  }, [location, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await authAPI.verifyOtp(email, otp);
      showToast('Account verified successfully! Please log in.', 'success');
      navigate('/login');
    } catch (err) {
      console.error('OTP verify error:', err);
      const detail = err.response?.data?.detail || 'Invalid or expired OTP code.';
      setError(detail);
      showToast(detail, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center bg-primary-dark px-4 py-12 relative">
      <div className="absolute w-72 h-72 rounded-full bg-accent/5 filter blur-3xl -top-10 -left-10" />
      <div className="absolute w-72 h-72 rounded-full bg-indigo-500/5 filter blur-3xl -bottom-10 -right-10" />

      <div className="max-w-md w-full space-y-6 p-8 rounded-2xl bg-primary-light/35 backdrop-blur-lg border border-slate-800 shadow-2xl relative z-10 text-left">
        <div className="text-center space-y-2">
          <h2 className="text-2xl font-black text-white tracking-tight">Verify Your Email</h2>
          <p className="text-xs text-slate-400">
            We sent a verification code to <strong className="text-slate-300">{email}</strong>.
          </p>
        </div>

        {error && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/20 text-rose-300 text-xs font-semibold flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit}>
          
          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Verification Code</label>
            <div className="relative flex items-center">
              <MailCheck className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />
              <input
                type="text"
                required
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                className="w-full bg-primary-dark/80 border border-slate-700 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-100 placeholder-slate-500 tracking-[0.3em] font-mono text-center outline-none focus:border-accent focus:ring-1 focus:ring-accent transition-all"
                placeholder="000000"
                maxLength={6}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-accent to-amber-600 text-slate-950 font-bold rounded-xl shadow-lg hover:shadow-accent/25 active:scale-[0.98] transition-all text-xs uppercase tracking-wider flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
          >
            {loading ? 'Confirming Code...' : 'Verify OTP'}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

        </form>

        <div className="text-center pt-4 border-t border-slate-800/80">
          <p className="text-xs text-slate-400">
            Wrong email address?{' '}
            <Link to="/register" className="text-accent hover:underline font-bold">
              Sign up again
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
