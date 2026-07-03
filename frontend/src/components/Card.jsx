import React from 'react';

export default function Card({ children, className = '', ...props }) {
  return (
    <div
      className={`p-6 rounded-2xl bg-primary-light border border-slate-800 shadow-md hover:border-slate-700/80 transition-all ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
