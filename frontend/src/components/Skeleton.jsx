import React from 'react';

export default function Skeleton({ className, count = 1 }) {
  const arr = Array.from({ length: count });

  return (
    <>
      {arr.map((_, i) => (
        <div
          key={i}
          className={`bg-slate-800/40 border border-slate-800 rounded-xl animate-pulse ${className}`}
        >
          <div className="h-full w-full opacity-0">Loading...</div>
        </div>
      ))}
    </>
  );
}
