import React from 'react';
import { X } from 'lucide-react';

export default function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-primary-dark/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="max-w-xl w-full bg-primary border border-slate-800 rounded-2xl shadow-2xl overflow-hidden text-left flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-primary-light/50 flex-shrink-0">
          <h3 className="text-sm font-black text-white">{title}</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto">{children}</div>

      </div>
    </div>
  );
}
