import React, { useState, useRef, useEffect } from 'react';
import { Bot, MessageSquare, Send, X, Sparkles } from 'lucide-react';
import { useChat } from '../context/ChatContext';

export default function ChatbotWidget() {
  const { isOpen, setIsOpen, messages, chatLoading, sendChatMessage } = useChat();
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendChatMessage(input);
    setInput('');
  };

  const handleChipClick = (query) => {
    sendChatMessage(query);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-[9999] p-4 bg-gradient-to-tr from-accent to-amber-500 rounded-full shadow-2xl hover:scale-105 active:scale-95 transition-all text-slate-950 hover:shadow-accent/25 cursor-pointer pulse-glow flex items-center justify-center"
      >
        <MessageSquare className="w-6 h-6 stroke-[2.5]" />
      </button>
    );
  }

  const chips = [
    "Plan a trip to Pune",
    "Show nearby dhabas",
    "Calculate fuel cost",
  ];

  return (
    <div className="fixed bottom-6 right-6 z-[9999] w-[350px] sm:w-[380px] h-[500px] bg-primary border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col text-left">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-primary-light/50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-accent/10 border border-accent/20 rounded-lg text-accent">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-black text-white">Cockpit Copilot</h3>
            <span className="text-[9px] text-emerald-400 font-bold block leading-none mt-0.5">● Ready to assist</span>
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-slate-400 hover:text-white p-1 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-grow overflow-y-auto p-4 space-y-3 no-scrollbar">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-xl text-xs leading-relaxed max-w-[85%] ${
              m.role === 'user'
                ? 'bg-accent text-slate-950 font-bold self-end ml-auto rounded-tr-none'
                : 'bg-primary-dark border border-slate-800 text-slate-200 mr-auto rounded-tl-none'
            }`}
          >
            {m.content}
          </div>
        ))}
        {chatLoading && (
          <div className="p-3 rounded-xl bg-primary-dark border border-slate-800 text-slate-400 mr-auto rounded-tl-none animate-pulse text-[10px]">
            Synthesizing response...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Chips & Input footer */}
      <div className="border-t border-slate-800 p-3 bg-primary-dark/30 space-y-3 flex-shrink-0">
        
        {/* Suggestion Chips */}
        <div className="flex flex-wrap gap-1.5">
          {chips.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleChipClick(chip)}
              className="px-2.5 py-1 bg-primary-light border border-slate-800 hover:border-slate-700 text-slate-300 rounded-full text-[10px] font-bold transition-all cursor-pointer flex items-center gap-1"
            >
              <Sparkles className="w-2.5 h-2.5 text-accent fill-accent" />
              {chip}
            </button>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="flex gap-2">
          <input
            type="text"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            className="flex-grow bg-primary-dark border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-100 placeholder-slate-500 outline-none focus:border-accent"
          />
          <button
            type="submit"
            disabled={chatLoading}
            className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-accent rounded-xl font-bold text-xs flex items-center justify-center cursor-pointer disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>

      </div>

    </div>
  );
}
