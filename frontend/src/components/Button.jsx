import React from 'react';

export default function Button({ children, type = 'button', variant = 'primary', className = '', ...props }) {
  const base = 'px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider transition-all duration-200 active:scale-[0.98] cursor-pointer disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-1.5';
  
  const variants = {
    primary: 'bg-gradient-to-r from-accent to-amber-600 text-slate-950 shadow-md hover:shadow-accent/25 hover:scale-[1.01]',
    secondary: 'bg-primary-light border border-slate-700 text-slate-200 hover:bg-slate-850',
    danger: 'bg-rose-955/30 hover:bg-rose-900/60 border border-rose-500/25 text-rose-300',
  };

  return (
    <button
      type={type}
      className={`${base} ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
