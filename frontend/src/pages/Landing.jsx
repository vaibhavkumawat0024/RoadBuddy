import React, { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Compass, Shield, Zap, TrendingUp, Users, ArrowRight } from 'lucide-react';

export default function Landing() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let particles = [];

    const resize = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };

    window.addEventListener('resize', resize);
    resize();

    class TelemetryNode {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.8;
        this.vy = (Math.random() - 0.5) * 0.8;
        this.radius = Math.random() * 2 + 1;
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
        if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
      }
      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(245, 158, 11, 0.3)';
        ctx.fill();
      }
    }

    const init = () => {
      particles = [];
      const numNodes = Math.min(60, Math.floor(canvas.width / 20));
      for (let i = 0; i < numNodes; i++) {
        particles.push(new TelemetryNode());
      }
    };
    init();

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineWidth = 0.5;

      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120) {
            const alpha = (1 - dist / 120) * 0.2;
            ctx.strokeStyle = `rgba(99, 102, 241, ${alpha})`;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      particles.forEach((p) => {
        p.update();
        p.draw();
      });

      animationFrameId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="relative min-h-[calc(100vh-64px)] flex flex-col justify-between overflow-hidden bg-primary-dark">
      
      {/* Dynamic Telemetry Network Animation (Video Effect) */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>

      {/* Hero Content Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 z-10 flex-grow flex items-center">
        <div className="grid lg:grid-cols-2 gap-12 items-center w-full">
          
          {/* Left Text details */}
          <div className="space-y-6 max-w-xl text-left">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-accent/15 border border-accent/30 text-accent rounded-full text-xs font-bold uppercase tracking-wider">
              <Zap className="w-3.5 h-3.5 fill-accent" />
              Next-Gen Route Analytics Live
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white leading-none tracking-tight">
              Adventure with <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent via-amber-400 to-indigo-400">
                Absolute Precision
              </span>
            </h1>
            <p className="text-sm sm:text-base text-slate-400 leading-relaxed">
              Plan and navigate your routes with real-time diagnostics, cost projections, and pre-order food bookings at verified partner rest stops.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <Link
                to="/register"
                className="px-6 py-3 bg-gradient-to-r from-accent to-amber-600 text-slate-950 font-bold rounded-xl shadow-lg hover:shadow-accent/25 hover:scale-[1.02] active:scale-95 transition-all text-sm flex items-center gap-1"
              >
                Plan a Trip Now
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/login"
                className="px-6 py-3 bg-primary-light hover:bg-slate-800 text-slate-200 border border-slate-700 font-bold rounded-xl transition-all text-sm"
              >
                Sign In
              </Link>
            </div>
          </div>

          {/* Right Card Bento Grid Mockups */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl bg-primary-light/40 backdrop-blur-md border border-slate-800 shadow-xl flex flex-col justify-between h-44 text-left">
              <Shield className="w-8 h-8 text-accent" />
              <div>
                <h3 className="text-sm font-bold text-white mb-1">Safety HUD</h3>
                <p className="text-[11px] text-slate-400">Real-time driver alerts and active path assessment scores.</p>
              </div>
            </div>
            <div className="p-5 rounded-2xl bg-primary-light/40 backdrop-blur-md border border-slate-800 shadow-xl flex flex-col justify-between h-44 text-left transform translate-y-6">
              <Zap className="w-8 h-8 text-accent" />
              <div>
                <h3 className="text-sm font-bold text-white mb-1">OBD-II Sync</h3>
                <p className="text-[11px] text-slate-400">Telemetry tracking, speeds, fuel calibrations, and ETAs.</p>
              </div>
            </div>
            <div className="p-5 rounded-2xl bg-primary-light/40 backdrop-blur-md border border-slate-800 shadow-xl flex flex-col justify-between h-44 text-left">
              <TrendingUp className="w-8 h-8 text-accent" />
              <div>
                <h3 className="text-sm font-bold text-white mb-1">Cost Estimator</h3>
                <p className="text-[11px] text-slate-400">Accurate breakdowns of highway toll charges and fuel usage.</p>
              </div>
            </div>
            <div className="p-5 rounded-2xl bg-primary-light/40 backdrop-blur-md border border-slate-800 shadow-xl flex flex-col justify-between h-44 text-left transform translate-y-6">
              <Users className="w-8 h-8 text-accent" />
              <div>
                <h3 className="text-sm font-bold text-white mb-1">Pre-Pay Dhabas</h3>
                <p className="text-[11px] text-slate-400">Verified roadside restaurant locations with menu order dispatches.</p>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Footer Branding */}
      <div className="border-t border-slate-900 bg-primary-dark/80 backdrop-blur-md py-4 text-center text-xs text-slate-500 z-10 flex justify-between px-8">
        <span>© 2026 RoadBuddy. Built with absolute precision.</span>
        <span className="text-accent text-[10px] font-bold tracking-widest uppercase">System Status: Optimal</span>
      </div>

    </div>
  );
}
