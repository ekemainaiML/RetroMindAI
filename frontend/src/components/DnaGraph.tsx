"use client";

import { useMemo, useState } from "react";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  confidence: number;
  isCurrent?: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  label: string;
  weight: number;
}

interface Props {
  currentLabel: string;
  currentType: string;
  matches: Array<{
    vehicle_id: string;
    type: string;
    matching_deviations: number;
    confidence: number;
  }>;
}

const WIDTH = 400;
const HEIGHT = 260;
const CX = WIDTH / 2;
const CY = HEIGHT / 2;
const RADIUS = 90;

const NODE_COLORS: Record<string, string> = {
  three_wheeler: "#f59e0b",
  four_wheeler: "#3b82f6",
  motorcycle: "#8b5cf6",
};

function layoutNodes(
  currentLabel: string,
  currentType: string,
  matches: Props["matches"]
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    {
      id: "__current__",
      label: currentLabel.length > 18 ? currentLabel.slice(0, 15) + "…" : currentLabel,
      type: currentType,
      confidence: 1,
      isCurrent: true,
    },
  ];

  const edges: GraphEdge[] = [];
  const count = Math.min(matches.length, 5);

  for (let i = 0; i < count; i++) {
    const m = matches[i];
    const shortId = m.vehicle_id.length > 12 ? m.vehicle_id.slice(0, 10) + "…" : m.vehicle_id;
    nodes.push({
      id: m.vehicle_id,
      label: shortId,
      type: m.type,
      confidence: m.confidence,
    });
    edges.push({
      source: "__current__",
      target: m.vehicle_id,
      label: `${m.matching_deviations} deviation${m.matching_deviations !== 1 ? "s" : ""}`,
      weight: m.matching_deviations,
    });
  }

  return { nodes, edges };
}

function nodePosition(
  index: number,
  total: number
): { x: number; y: number } {
  if (total === 0) return { x: CX, y: CY };
  const angle = (2 * Math.PI * index) / total - Math.PI / 2;
  return {
    x: CX + RADIUS * Math.cos(angle),
    y: CY + RADIUS * Math.sin(angle),
  };
}

export default function DnaGraph({ currentLabel, currentType, matches }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const { nodes, edges } = useMemo(
    () => layoutNodes(currentLabel, currentType, matches),
    [currentLabel, currentType, matches]
  );

  const satelliteNodes = nodes.filter((n) => !n.isCurrent);

  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full max-w-md">
      <defs>
        <radialGradient id="current-grad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
        </radialGradient>
      </defs>

      <circle cx={CX} cy={CY} r={RADIUS + 20} fill="url(#current-grad)" />

      {edges.map((edge) => {
        const idx = satelliteNodes.findIndex((n) => n.id === edge.target);
        const pos = nodePosition(idx, satelliteNodes.length);
        const isHovered = hoveredId === edge.target || hoveredId === edge.source;
        return (
          <g key={`edge-${edge.target}`}>
            <line
              x1={CX}
              y1={CY}
              x2={pos.x}
              y2={pos.y}
              stroke={isHovered ? "#3b82f6" : "#cbd5e1"}
              strokeWidth={isHovered ? 2 : 1}
              strokeOpacity={isHovered ? 0.8 : 0.4}
            />
            <text
              x={(CX + pos.x) / 2}
              y={(CY + pos.y) / 2 - 6}
              textAnchor="middle"
              className="fill-zinc-400 text-[8px]"
            >
              {edge.label}
            </text>
          </g>
        );
      })}

      <g
        onMouseEnter={() => setHoveredId("__current__")}
        onMouseLeave={() => setHoveredId(null)}
      >
        <circle cx={CX} cy={CY} r={22} fill="#3b82f6" opacity={0.15} />
        <circle cx={CX} cy={CY} r={14} fill="#3b82f6" />
        <text
          x={CX}
          y={CY + 1}
          textAnchor="middle"
          dominantBaseline="central"
          className="fill-white text-[9px] font-bold"
        >
          {currentType === "three_wheeler" ? "3W" : currentType === "four_wheeler" ? "4W" : "MC"}
        </text>
        <text
          x={CX}
          y={CY + 26}
          textAnchor="middle"
          className="fill-zinc-500 text-[8px]"
        >
          {currentLabel}
        </text>
      </g>

      {satelliteNodes.map((node, i) => {
        const pos = nodePosition(i, satelliteNodes.length);
        const isHovered = hoveredId === node.id;
        const color = NODE_COLORS[node.type] ?? "#94a3b8";
        return (
          <g
            key={node.id}
            onMouseEnter={() => setHoveredId(node.id)}
            onMouseLeave={() => setHoveredId(null)}
            className="transition-opacity"
            style={{ cursor: "pointer" }}
          >
            <circle cx={pos.x} cy={pos.y} r={isHovered ? 12 : 9} fill={color} opacity={isHovered ? 1 : 0.7} />
            <text
              x={pos.x}
              y={pos.y + (isHovered ? 22 : 18)}
              textAnchor="middle"
              className={`text-[7px] ${isHovered ? "fill-zinc-700 font-semibold" : "fill-zinc-400"}`}
            >
              {node.label}
            </text>
            {isHovered && (
              <text
                x={pos.x}
                y={pos.y + 30}
                textAnchor="middle"
                className="fill-zinc-400 text-[6px]"
              >
                {Math.round(node.confidence * 100)}% match
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
