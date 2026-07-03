import React from 'react';

const Speedometer = ({ speed }) => {
  const minSpeed = 0;
  const maxSpeed = 120; // Max speed for display on the speedometer
  const circumference = 2 * Math.PI * 40; // R=40 for the main circle
  const strokeDasharray = circumference * 0.75; // 3/4 of the circle for the arc
  const strokeDashoffset = circumference * 0.25; // Offset to start from the left bottom

  // Calculate the angle for the needle
  // Map speed from [minSpeed, maxSpeed] to angle from [-135, 135] degrees
  const angle = ((speed - minSpeed) / (maxSpeed - minSpeed)) * 270 - 135;

  return (
    <div className="relative w-48 h-48 flex items-center justify-center">
      <svg className="w-full h-full" viewBox="0 0 100 100">
        {/* Speedometer Arc */}
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke="#1f2937" // primary-darker background arc
          strokeWidth="10"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * 0.25}
          transform="rotate(135 50 50)"
        />
        <circle
          cx="50"
          cy="50"
          r="40"
          fill="none"
          stroke="#f59e0b" // accent color for active speed arc
          strokeWidth="10"
          strokeDasharray={strokeDasharray}
          strokeDashoffset={strokeDashoffset - (speed / maxSpeed) * strokeDasharray * 0.75} // Adjust offset based on speed
          strokeLinecap="round"
          transform="rotate(135 50 50)"
          className="transition-all duration-300 ease-out"
        />

        {/* Speedometer Ticks - Simplified */}
        {[0, 30, 60, 90, 120].map((tickSpeed, index) => {
          const tickAngle = ((tickSpeed - minSpeed) / (maxSpeed - minSpeed)) * 270 - 135;
          const x1 = 50 + 35 * Math.cos((tickAngle - 90) * Math.PI / 180);
          const y1 = 50 + 35 * Math.sin((tickAngle - 90) * Math.PI / 180);
          const x2 = 50 + 40 * Math.cos((tickAngle - 90) * Math.PI / 180);
          const y2 = 50 + 40 * Math.sin((tickAngle - 90) * Math.PI / 180);
          return (
            <line
              key={tickSpeed}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#6b7280" // slate-500
              strokeWidth="1"
              className="transition-all duration-300 ease-out"
            />
          );
        })}
        {[0, 30, 60, 90, 120].map((tickSpeed, index) => {
          const tickAngle = ((tickSpeed - minSpeed) / (maxSpeed - minSpeed)) * 270 - 135;
          const textX = 50 + 30 * Math.cos((tickAngle - 90) * Math.PI / 180);
          const textY = 50 + 30 * Math.sin((tickAngle - 90) * Math.PI / 180);
          return (
            <text
              key={`text-${tickSpeed}`}
              x={textX}
              y={textY}
              fill="#9ca3af" // slate-400
              fontSize="6"
              textAnchor="middle"
              alignmentBaseline="middle"
              className="transition-all duration-300 ease-out"
            >
              {tickSpeed}
            </text>
          );
        })}

        {/* Needle */}
        <line
          x1="50"
          y1="50"
          x2="50"
          y2="15"
          stroke="#f59e0b" // accent color
          strokeWidth="2"
          strokeLinecap="round"
          transform={`rotate(${angle} 50 50)`}
          className="transition-transform duration-300 ease-out"
        />
        <circle cx="50" cy="50" r="3" fill="#f59e0b" />
      </svg>
      <div className="absolute flex flex-col items-center justify-center top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <span className="text-3xl font-black text-white">{speed}</span>
        <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">km/h</span>
      </div>
    </div>
  );
};

export default Speedometer;
