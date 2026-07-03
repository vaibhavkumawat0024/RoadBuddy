import React from 'react';

export default function StatusBadge({ status, type = 'info' }) {
  const types = {
    success: 'bg-emerald-950/80 border-emerald-500/20 text-emerald-300',
    error: 'bg-rose-950/80 border-rose-500/20 text-rose-300',
    warning: 'bg-amber-950/80 border-amber-500/20 text-amber-300',
    info: 'bg-slate-800 border-slate-700 text-slate-300',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold px-2.5 py-0.5 rounded border ${types[type]}`}>
      {status}
    </span>
  );
}
