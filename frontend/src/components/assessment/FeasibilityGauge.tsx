"use client";

import { useEffect, useState } from "react";

interface Props {
  score: number;
  size?: number;
  strokeWidth?: number;
}

function getColor(score: number): string {
  if (score < 40) {
    const t = score / 40;
    return lerpColor("#ef4444", "#eab308", t);
  }
  if (score < 70) {
    const t = (score - 40) / 30;
    return lerpColor("#eab308", "#22c55e", t);
  }
  const t = Math.min(1, (score - 70) / 30);
  return lerpColor("#22c55e", "#16a34a", t);
}

function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff,
    ag = (ah >> 8) & 0xff,
    ab = ah & 0xff;
  const br = (bh >> 16) & 0xff,
    bg = (bh >> 8) & 0xff,
    bb = bh & 0xff;
  const rr = Math.round(ar + (br - ar) * t);
  const rg = Math.round(ag + (bg - ag) * t);
  const rb = Math.round(ab + (bb - ab) * t);
  return `#${((rr << 16) | (rg << 8) | rb).toString(16).padStart(6, "0")}`;
}

export default function FeasibilityGauge({
  score,
  size = 200,
  strokeWidth = 20,
}: Props) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 100);
    return () => clearTimeout(timer);
  }, [score]);

  const cx = size / 2;
  const cy = size / 2;
  const r = (size - strokeWidth) / 2;

  const progress = Math.max(0, Math.min(1, animatedScore / 100));
  const angle = Math.PI * (1 - progress);
  const endX = cx + r * Math.cos(angle);
  const endY = cy + r * Math.sin(angle);
  const largeArcFlag = progress > 0.5 ? 1 : 0;

  const fillColor = getColor(animatedScore);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="drop-shadow-sm"
      role="img"
      aria-label={`Feasibility score: ${Math.round(score)}%`}
    >
      <defs>
        <linearGradient id="gauge-glow" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="40%" stopColor="#eab308" />
          <stop offset="70%" stopColor="#22c55e" />
          <stop offset="100%" stopColor="#16a34a" />
        </linearGradient>
      </defs>

      <path
        d={`M ${cx - r} ${cy} A ${r} ${r} 0 1 1 ${cx + r} ${cy}`}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        className="text-zinc-200 dark:text-zinc-700"
      />

      {progress > 0 && (
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 ${largeArcFlag} 1 ${endX} ${endY}`}
          fill="none"
          stroke={fillColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="transition-[stroke] duration-700 ease-out"
          style={{ filter: "drop-shadow(0 0 4px rgba(0,0,0,0.1))" }}
        />
      )}

      <text
        x={cx}
        y={cy + 8}
        textAnchor="middle"
        className="fill-zinc-800 text-4xl font-bold tabular-nums dark:fill-zinc-100"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        {Math.round(animatedScore)}
      </text>

      <text
        x={cx}
        y={cy + 30}
        textAnchor="middle"
        className="fill-zinc-400 text-sm dark:fill-zinc-500"
      >
        out of 100
      </text>
    </svg>
  );
}
