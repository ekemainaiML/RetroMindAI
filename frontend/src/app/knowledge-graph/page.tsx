"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiGet } from "@/utils/api";
import HelpBubble from "@/components/HelpBubble";

interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  confidence: number;
  risk_state: string;
  compliance_state: string;
}

interface GraphEdgeData {
  source: string;
  target: string;
  label: string;
  weight: number;
}

interface KnowledgeGraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}

interface PositionedNode extends GraphNodeData {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const NODE_RADIUS = 30;
const REPULSION = 8000;
const ATTRACTION = 0.003;
const DAMPER = 0.85;

const COLORS: Record<string, string> = {
  three_wheeler: "#f59e0b",
  four_wheeler: "#3b82f6",
  motorcycle: "#8b5cf6",
};

function tick(nodes: PositionedNode[], edges: GraphEdgeData[]): boolean {
  for (const n of nodes) n.vx = 0;
  for (const n of nodes) n.vy = 0;

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(Math.hypot(dx, dy), 1);
      const force = REPULSION / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx -= fx;
      a.vy -= fy;
      b.vx += fx;
      b.vy += fy;
    }
  }

  for (const e of edges) {
    const a = nodes.find((n) => n.id === e.source);
    const b = nodes.find((n) => n.id === e.target);
    if (!a || !b) continue;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.max(Math.hypot(dx, dy), 1);
    const force = (dist - 120) * ATTRACTION;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    a.vx += fx;
    a.vy += fy;
    b.vx -= fx;
    b.vy -= fy;
  }

  const centerX = 600;
  const centerY = 400;
  const softness = 0.01;
  for (const n of nodes) {
    n.vx += (centerX - n.x) * softness;
    n.vy += (centerY - n.y) * softness;
  }

  let moved = false;
  for (const n of nodes) {
    n.vx *= DAMPER;
    n.vy *= DAMPER;
    n.x += n.vx;
    n.y += n.vy;
    if (Math.abs(n.vx) > 0.1 || Math.abs(n.vy) > 0.1) moved = true;
  }
  return moved;
}

export default function KnowledgeGraphPage() {
  const [data, setData] = useState<KnowledgeGraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const nodesRef = useRef<PositionedNode[]>([]);
  const frameRef = useRef<number>(0);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    apiGet<KnowledgeGraphData>("/knowledge-graph")
      .then((d) => {
        setData(d);
        const positioned: PositionedNode[] = d.nodes.map((n, i) => {
          const angle = (2 * Math.PI * i) / d.nodes.length;
          return {
            ...n,
            x: 600 + 280 * Math.cos(angle),
            y: 400 + 280 * Math.sin(angle),
            vx: 0,
            vy: 0,
          };
        });
        nodesRef.current = positioned;
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load graph"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!data || nodesRef.current.length === 0) return;
    let running = true;
    const d = data;
    function loop() {
      if (!running) return;
      const moved = tick(nodesRef.current, d.edges);
      setData((prev) => (prev ? { ...prev } : prev));
      if (moved) {
        frameRef.current = requestAnimationFrame(loop);
      }
    }
    frameRef.current = requestAnimationFrame(loop);
    return () => {
      running = false;
      cancelAnimationFrame(frameRef.current);
    };
  }, [data?.nodes.length, data?.edges.length, data]);

  const handlePointerDown = useCallback(
    (nodeId: string) => {
      setDragging(nodeId);
      const node = nodesRef.current.find((n) => n.id === nodeId);
      if (node) {
        node.vx = 0;
        node.vy = 0;
      }
    },
    []
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      if (!dragging) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const node = nodesRef.current.find((n) => n.id === dragging);
      if (node) {
        node.x = e.clientX - rect.left;
        node.y = e.clientY - rect.top;
      }
    },
    [dragging]
  );

  const handlePointerUp = useCallback(() => {
    setDragging(null);
  }, []);

  const nodes = nodesRef.current;
  const edges = data?.edges ?? [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-text-primary">
            Knowledge Graph
          </h1>
          <p className="mt-1 text-xs text-text-secondary">
            All assessments connected by shared deviation patterns
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center justify-center rounded-lg bg-brand px-4 py-2 text-xs font-medium text-white hover:bg-brand-dark transition-colors"
        >
          New Assessment
        </Link>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-24">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-brand" />
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-danger/30 bg-danger/5 p-3 text-xs text-danger">
          {error}
        </p>
      )}

      {data && (
        <svg
          ref={svgRef}
          viewBox="0 0 1200 800"
          className="w-full h-[75vh] min-h-[500px] rounded-xl border border-border bg-surface-card"
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          style={{ touchAction: "none", cursor: dragging ? "grabbing" : "grab" }}
        >
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {edges.map((e, i) => {
            const a = nodes.find((n) => n.id === e.source);
            const b = nodes.find((n) => n.id === e.target);
            if (!a || !b) return null;
            const thickness = Math.max(1, e.weight);
            const isHovered =
              hoveredNode === e.source || hoveredNode === e.target;
            return (
              <g key={`edge-${i}`}>
                <line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={isHovered ? "#3b82f6" : "#d4d4d8"}
                  strokeWidth={isHovered ? thickness + 1 : thickness}
                  strokeOpacity={isHovered ? 0.8 : 0.25}
                />
              </g>
            );
          })}

          {nodes.map((node) => {
            const isHovered = hoveredNode === node.id;
            const color = COLORS[node.type] ?? "#94a3b8";

            const connected = new Set(
              edges
                .filter((e) => e.source === node.id || e.target === node.id)
                .flatMap((e) => [e.source, e.target])
            );

            return (
              <g
                key={node.id}
                onPointerDown={() => handlePointerDown(node.id)}
                onPointerEnter={() => setHoveredNode(node.id)}
                onPointerLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                {isHovered && (
                  <>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={NODE_RADIUS + 12}
                      fill={color}
                      opacity={0.1}
                    />
                  </>
                )}

                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isHovered ? NODE_RADIUS + 4 : NODE_RADIUS}
                  fill={isHovered ? color : `${color}cc`}
                  stroke={isHovered ? "#fff" : "transparent"}
                  strokeWidth={2}
                  filter={isHovered ? "url(#glow)" : undefined}
                />

                <text
                  x={node.x}
                  y={node.y + 1}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="fill-white text-[10px] font-bold"
                  pointerEvents="none"
                >
                  {node.type === "three_wheeler"
                    ? "3W"
                    : node.type === "four_wheeler"
                      ? "4W"
                      : node.type === "motorcycle"
                        ? "MC"
                        : "?"}
                </text>

                {isHovered && (
                  <>
                    <text
                      x={node.x}
                      y={node.y + NODE_RADIUS + 18}
                      textAnchor="middle"
                      className="fill-zinc-700 text-[11px] font-semibold dark:fill-zinc-300"
                      pointerEvents="none"
                    >
                      {node.label}
                    </text>
                    <text
                      x={node.x}
                      y={node.y + NODE_RADIUS + 34}
                      textAnchor="middle"
                      className="fill-zinc-400 text-[10px]"
                      pointerEvents="none"
                    >
                      {Math.round(node.confidence * 100)}% · {node.compliance_state.replace(/_/g, " ")}
                    </text>
                    <text
                      x={node.x}
                      y={node.y + NODE_RADIUS + 48}
                      textAnchor="middle"
                      className="fill-zinc-400 text-[9px]"
                      pointerEvents="none"
                    >
                      {connected.size - 1} connection{connected.size - 1 !== 1 ? "s" : ""}
                    </text>
                  </>
                )}
              </g>
            );
          })}

          {nodes.length === 0 && !loading && (
            <>
              <rect x="200" y="220" width="800" height="360" rx="12" fill="#fafafa" className="dark:fill-zinc-900" />
              <text x={600} y={320} textAnchor="middle" className="fill-zinc-400 text-lg font-semibold">
                Your Knowledge Graph is Empty
              </text>
              <text x={600} y={360} textAnchor="middle" className="fill-zinc-400 text-sm">
                Complete an assessment to populate the graph.
              </text>
              <text x={600} y={390} textAnchor="middle" className="fill-zinc-400 text-xs">
                Each assessment becomes a node; shared deviations create edges.
              </text>
              <foreignObject x={460} y={420} width={280} height={80}>
                 <div className="flex flex-col items-center gap-2">
                   <a href="/" className="inline-flex items-center justify-center rounded-lg bg-brand px-5 py-2 text-sm font-medium text-white hover:bg-brand-dark transition-colors">
                     Start Assessment
                   </a>
                 </div>
              </foreignObject>
            </>
          )}
        </svg>
      )}

      {data && data.nodes.length > 0 && (
        <div className="mt-4 flex items-center gap-4 text-[10px] text-text-tertiary">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-accent" /> Three Wheeler
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-info" /> Four Wheeler
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-violet-500" /> Motorcycle
          </span>
          <span className="ml-auto text-text-tertiary">
            Drag nodes · Hover for details
          </span>
        </div>
      )}
      <HelpBubble />
    </div>
  );
}
