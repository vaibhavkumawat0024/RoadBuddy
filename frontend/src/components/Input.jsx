import React from 'react';

export default function Input({ label, error, icon: Icon, className = '', ...props }) {
  return (
    <div className={`space-y-1 text-left w-full ${className}`}>
      {label && <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">{label}</label>}
      <div className="relative flex items-center">
        {Icon && <Icon className="w-4 h-4 text-slate-500 absolute left-3 pointer-events-none" />}
        <input
          className={`w-full bg-primary-dark/80 border rounded-xl py-2.5 pr-4 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-accent transition-all ${
            Icon ? 'pl-10' : 'pl-4'
          } ${error ? 'border-rose-500/50 focus:border-rose-500' : 'border-slate-700'}`}
          {...props}
        />
      </div>
      {error && <p className="text-[10px] text-rose-400 font-semibold">{error}</p>}
    </div>
  );
}
