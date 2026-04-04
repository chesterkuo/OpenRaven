import { useRef, useEffect, useMemo, useCallback } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, type SimulationNodeDatum, type SimulationLinkDatum } from "d3-force";

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  properties: Record<string, any>;
}

interface SimNode extends GraphNode, SimulationNodeDatum {}
interface SimLink extends SimulationLinkDatum<SimNode> {
  id: string;
  properties: Record<string, any>;
}

interface GraphViewerProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onNodeClick: (node: GraphNode) => void;
  searchTerm: string;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#60a5fa",
  concept: "#4ade80",
  person: "#fbbf24",
  organization: "#c084fc",
  event: "#f87171",
  location: "#22d3ee",
};
const DEFAULT_COLOR = "#9ca3af";

function getNodeColor(node: GraphNode): string {
  const type = node.properties?.entity_type ?? node.labels[0] ?? "unknown";
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export default function GraphViewer({ nodes, edges, selectedNodeId, onNodeClick, searchTerm }: GraphViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const simLinksRef = useRef<SimLink[]>([]);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });

  const degreeMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const edge of edges) {
      m.set(edge.source, (m.get(edge.source) ?? 0) + 1);
      m.set(edge.target, (m.get(edge.target) ?? 0) + 1);
    }
    return m;
  }, [edges]);

  const getRadius = useCallback((nodeId: string) => {
    const degree = degreeMap.get(nodeId) ?? 1;
    return Math.min(3 + Math.sqrt(degree) * 2, 16);
  }, [degreeMap]);

  // Main simulation + render effect
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || nodes.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width * devicePixelRatio;
      canvas.height = rect.height * devicePixelRatio;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    };
    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    // Deep-copy to prevent d3 from mutating React state
    const simNodes: SimNode[] = nodes.map((n) => ({ ...n }));
    const simLinks: SimLink[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
      id: e.id,
      properties: e.properties,
    }));
    simNodesRef.current = simNodes;
    simLinksRef.current = simLinks;

    const w = canvas.width / devicePixelRatio;
    const h = canvas.height / devicePixelRatio;

    const simulation = forceSimulation<SimNode>(simNodes)
      .force("link", forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(60))
      .force("charge", forceManyBody().strength(-120))
      .force("center", forceCenter(w / 2, h / 2))
      .force("collide", forceCollide<SimNode>().radius((d) => getRadius(d.id) + 2))
      .alphaDecay(0.02)
      .velocityDecay(0.3);

    const paint = () => {
      const { x: tx, y: ty, k } = transformRef.current;
      ctx.save();
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "#030712";
      ctx.fillRect(0, 0, w, h);
      ctx.translate(tx, ty);
      ctx.scale(k, k);

      for (const link of simLinks) {
        const s = link.source as SimNode;
        const t = link.target as SimNode;
        if (s.x == null || t.x == null) continue;
        const isConnected = selectedNodeId && (s.id === selectedNodeId || t.id === selectedNodeId);
        ctx.beginPath();
        ctx.moveTo(s.x, s.y!);
        ctx.lineTo(t.x, t.y!);
        ctx.strokeStyle = isConnected ? "#60a5fa66" : "#374151";
        ctx.lineWidth = isConnected ? 1.5 : 0.5;
        ctx.stroke();
      }

      for (const node of simNodes) {
        if (node.x == null) continue;
        const radius = getRadius(node.id);
        const color = getNodeColor(node);
        const isSelected = node.id === selectedNodeId;
        const isMatch = searchTerm && node.id.toLowerCase().includes(searchTerm.toLowerCase());
        const dimmed = searchTerm && !isMatch;

        ctx.beginPath();
        ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
        ctx.fillStyle = dimmed ? `${color}33` : color;
        ctx.fill();

        if (isSelected) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        const degree = degreeMap.get(node.id) ?? 1;
        if (degree >= 3 || isSelected || isMatch) {
          ctx.font = `${isSelected ? "bold " : ""}${Math.max(3, radius * 0.8)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = dimmed ? "#9ca3af55" : "#e5e7eb";
          ctx.fillText(node.id, node.x, node.y! + radius + 2);
        }
      }

      ctx.restore();
    };

    simulation.on("tick", paint);

    // Click hit-test
    const handleClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const { x: tx, y: ty, k } = transformRef.current;
      const mx = (e.clientX - rect.left - tx) / k;
      const my = (e.clientY - rect.top - ty) / k;

      for (const node of simNodes) {
        if (node.x == null) continue;
        const r = getRadius(node.id) + 4;
        const dx = mx - node.x;
        const dy = my - node.y!;
        if (dx * dx + dy * dy < r * r) {
          onNodeClick(node);
          return;
        }
      }
    };
    canvas.addEventListener("click", handleClick);

    // Pan + zoom
    let isPanning = false;
    let panStart = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button === 0) {
        isPanning = true;
        panStart = { x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y };
      }
    };
    const handleMouseMove = (e: MouseEvent) => {
      if (!isPanning) return;
      transformRef.current.x = e.clientX - panStart.x;
      transformRef.current.y = e.clientY - panStart.y;
      paint();
    };
    const handleMouseUp = () => { isPanning = false; };
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const t = transformRef.current;
      const factor = e.deltaY < 0 ? 1.1 : 0.9;
      const newK = Math.min(Math.max(t.k * factor, 0.1), 10);
      t.x = mx - (mx - t.x) * (newK / t.k);
      t.y = my - (my - t.y) * (newK / t.k);
      t.k = newK;
      paint();
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    canvas.addEventListener("mousemove", handleMouseMove);
    canvas.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("mouseleave", handleMouseUp);
    canvas.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      simulation.stop();
      resizeObserver.disconnect();
      canvas.removeEventListener("click", handleClick);
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
      canvas.removeEventListener("mouseleave", handleMouseUp);
      canvas.removeEventListener("wheel", handleWheel);
    };
  }, [nodes, edges, getRadius, degreeMap]);

  // Repaint on selection/search change without restarting simulation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || simNodesRef.current.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width / devicePixelRatio;
    const h = canvas.height / devicePixelRatio;
    const simNodes = simNodesRef.current;
    const simLinks = simLinksRef.current;
    const { x: tx, y: ty, k } = transformRef.current;

    ctx.save();
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#030712";
    ctx.fillRect(0, 0, w, h);
    ctx.translate(tx, ty);
    ctx.scale(k, k);

    for (const link of simLinks) {
      const s = link.source as SimNode;
      const t = link.target as SimNode;
      if (s.x == null || t.x == null) continue;
      const isConnected = selectedNodeId && (s.id === selectedNodeId || t.id === selectedNodeId);
      ctx.beginPath();
      ctx.moveTo(s.x, s.y!);
      ctx.lineTo(t.x, t.y!);
      ctx.strokeStyle = isConnected ? "#60a5fa66" : "#374151";
      ctx.lineWidth = isConnected ? 1.5 : 0.5;
      ctx.stroke();
    }

    for (const node of simNodes) {
      if (node.x == null) continue;
      const radius = getRadius(node.id);
      const color = getNodeColor(node);
      const isSelected = node.id === selectedNodeId;
      const isMatch = searchTerm && node.id.toLowerCase().includes(searchTerm.toLowerCase());
      const dimmed = searchTerm && !isMatch;

      ctx.beginPath();
      ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
      ctx.fillStyle = dimmed ? `${color}33` : color;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      const degree = degreeMap.get(node.id) ?? 1;
      if (degree >= 3 || isSelected || isMatch) {
        ctx.font = `${isSelected ? "bold " : ""}${Math.max(3, radius * 0.8)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = dimmed ? "#9ca3af55" : "#e5e7eb";
        ctx.fillText(node.id, node.x, node.y! + radius + 2);
      }
    }

    ctx.restore();
  }, [selectedNodeId, searchTerm, degreeMap, getRadius]);

  return (
    <div ref={containerRef} className="flex-1 bg-gray-950 relative" data-testid="graph-viewer">
      <canvas ref={canvasRef} className="absolute inset-0" />
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-gray-600">
          No nodes to display
        </div>
      )}
    </div>
  );
}
