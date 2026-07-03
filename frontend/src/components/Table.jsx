import React from 'react';

export default function Table({ headers, children, className = '' }) {
  return (
    <div className={`overflow-x-auto rounded-2xl border border-slate-800 bg-primary-light/40 shadow-xl ${className}`}>
      <table className="w-full text-sm text-left text-slate-300">
        <thead className="text-[10px] text-slate-400 uppercase tracking-widest bg-primary-light border-b border-slate-800">
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="px-6 py-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 font-medium">
          {children}
        </tbody>
      </table>
    </div>
  );
}
