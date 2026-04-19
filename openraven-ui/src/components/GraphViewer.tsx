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
  mode?: "full" | "mini";
  focusNodeId?: string | null;
}

const TYPE_COLORS: Record<string, string> = {
  technology: "#fa520f",
  concept: "#1f1f1f",
  person: "#ffa110",
  organization: "#d94800",
  event: "#dc2626",
  location: "#8b6914",
  statute: "#2563eb",
  content: "#6b7280",
  method: "#8b6914",
  data: "#a0a0a0",
  artifact: "#16a34a",
};
const DEFAULT_COLOR = "#999999";

function getNodeColor(node: GraphNode): string {
  const type = node.properties?.entity_type ?? node.labels[0] ?? "unknown";
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export default function GraphViewer({ nodes, edges, selectedNodeId, onNodeClick, searchTerm, mode = "full", focusNodeId }: GraphViewerProps) {
  const isMini = mode === "mini";
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const simLinksRef = useRef<SimLink[]>([]);
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const hoveredNodeRef = useRef<SimNode | null>(null);

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
      .force("link", forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(isMini ? 30 : 60))
      .force("charge", forceManyBody().strength(isMini ? -30 : -120))
      .force("center", forceCenter(w / 2, h / 2).strength(isMini ? 1 : 0.1))
      .force("collide", forceCollide<SimNode>().radius((d) => getRadius(d.id) + 2))
      .alphaDecay(isMini ? 0.05 : 0.02)
      .velocityDecay(isMini ? 0.5 : 0.3);

    const paint = () => {
      const { x: tx, y: ty, k } = transformRef.current;
      ctx.save();
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = isMini ? "#f8f6f0" : "#fef9ef";
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
        ctx.strokeStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
        ctx.lineWidth = isConnected ? 1.5 : 0.5;
        ctx.stroke();

        // Draw arrowhead
        const angle = Math.atan2(t.y! - s.y!, t.x! - s.x!);
        const targetRadius = getRadius(t.id);
        const arrowX = t.x! - Math.cos(angle) * targetRadius;
        const arrowY = t.y! - Math.sin(angle) * targetRadius;
        const arrowSize = isConnected ? 5 : 3;
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(
          arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
          arrowY - arrowSize * Math.sin(angle - Math.PI / 6),
        );
        ctx.lineTo(
          arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
          arrowY - arrowSize * Math.sin(angle + Math.PI / 6),
        );
        ctx.closePath();
        ctx.fillStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
        ctx.fill();
      }

      const searchLower = searchTerm.toLowerCase();
      for (const node of simNodes) {
        if (node.x == null) continue;
        const radius = getRadius(node.id);
        const color = getNodeColor(node);
        const isSelected = node.id === selectedNodeId;
        const isMatch = searchTerm && (
          node.id.toLowerCase().includes(searchLower) ||
          (node.properties?.description ?? "").toLowerCase().includes(searchLower) ||
          (node.properties?.entity_type ?? "").toLowerCase().includes(searchLower)
        );
        const dimmed = searchTerm && !isMatch;
        const isHovered = hoveredNodeRef.current && node.id === hoveredNodeRef.current.id;

        ctx.beginPath();
        ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
        ctx.fillStyle = dimmed ? `${color}33` : color;
        ctx.fill();

        if (isSelected) {
          ctx.strokeStyle = "#fa520f";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        if (isHovered) {
          ctx.strokeStyle = "#fa520f";
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        const degree = degreeMap.get(node.id) ?? 1;
        const showLabel = isMini ? (isSelected || isHovered) : (degree >= 3 || isSelected || isMatch || isHovered);
        if (showLabel) {
          const fontSize = isMini ? 10 : Math.max(3, radius * 0.8);
          ctx.font = `${isSelected ? "bold " : ""}${fontSize}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "top";
          ctx.fillStyle = dimmed ? "#1f1f1f33" : "#1f1f1f";
          ctx.fillText(node.id, node.x, node.y! + radius + 2);
        }
      }

      ctx.restore();
    };

    simulation.on("tick", paint);

    // Interaction state
    let isPanning = false;
    let panStart = { x: 0, y: 0 };
    let dragNode: SimNode | null = null;
    let dragDistance = 0;

    function hitTest(clientX: number, clientY: number): SimNode | null {
      const rect = canvas.getBoundingClientRect();
      const { x: tx, y: ty, k } = transformRef.current;
      const mx = (clientX - rect.left - tx) / k;
      const my = (clientY - rect.top - ty) / k;
      for (const node of simNodes) {
        if (node.x == null) continue;
        const r = getRadius(node.id) + 4;
        const dx = mx - node.x;
        const dy = my - node.y!;
        if (dx * dx + dy * dy < r * r) return node;
      }
      return null;
    }

    const handleMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      dragDistance = 0;

      const hit = hitTest(e.clientX, e.clientY);
      if (hit) {
        dragNode = hit;
        simulation.alphaTarget(0.3).restart();
      } else {
        if (!isMini) {
          isPanning = true;
          panStart = { x: e.clientX - transformRef.current.x, y: e.clientY - transformRef.current.y };
        }
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      dragDistance += Math.abs(e.movementX) + Math.abs(e.movementY);

      if (dragNode) {
        const rect = canvas.getBoundingClientRect();
        const { x: tx, y: ty, k } = transformRef.current;
        dragNode.fx = (e.clientX - rect.left - tx) / k;
        dragNode.fy = (e.clientY - rect.top - ty) / k;
        return;
      }

      if (isPanning) {
        transformRef.current.x = e.clientX - panStart.x;
        transformRef.current.y = e.clientY - panStart.y;
        paint();
        return;
      }

      // Hover detection (only when not dragging or panning)
      const hit = hitTest(e.clientX, e.clientY);
      if (hit !== hoveredNodeRef.current) {
        hoveredNodeRef.current = hit;
        canvas.style.cursor = hit ? "pointer" : "grab";
        paint(); // repaint to show hover highlight
      }
    };

    const handleMouseUp = () => {
      if (dragNode) {
        simulation.alphaTarget(0);
        // Pin the node where it was dropped
        dragNode.fx = dragNode.x;
        dragNode.fy = dragNode.y;
        dragNode = null;
      }
      isPanning = false;
    };

    const handleClick = (e: MouseEvent) => {
      if (dragDistance > 3) return; // was a drag, not a click
      const hit = hitTest(e.clientX, e.clientY);
      if (hit) onNodeClick(hit);
    };

    const handleDblClick = (e: MouseEvent) => {
      const hit = hitTest(e.clientX, e.clientY);
      if (hit) {
        // Unpin node on double-click
        hit.fx = null;
        hit.fy = null;
        simulation.alphaTarget(0.3).restart();
        setTimeout(() => { if (!dragNode) simulation.alphaTarget(0); }, 500);
      }
    };

    const handleWheel = (e: WheelEvent) => {
      if (isMini) return;
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
    canvas.addEventListener("click", handleClick);
    canvas.addEventListener("dblclick", handleDblClick);
    canvas.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      simulation.stop();
      resizeObserver.disconnect();
      canvas.removeEventListener("mousedown", handleMouseDown);
      canvas.removeEventListener("mousemove", handleMouseMove);
      canvas.removeEventListener("mouseup", handleMouseUp);
      canvas.removeEventListener("mouseleave", handleMouseUp);
      canvas.removeEventListener("click", handleClick);
      canvas.removeEventListener("dblclick", handleDblClick);
      canvas.removeEventListener("wheel", handleWheel);
    };
  }, [nodes, edges, getRadius, degreeMap, isMini]);

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
    ctx.fillStyle = "#fef9ef";
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
      ctx.strokeStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
      ctx.lineWidth = isConnected ? 1.5 : 0.5;
      ctx.stroke();

      // Draw arrowhead
      const angle = Math.atan2(t.y! - s.y!, t.x! - s.x!);
      const targetRadius = getRadius(t.id);
      const arrowX = t.x! - Math.cos(angle) * targetRadius;
      const arrowY = t.y! - Math.sin(angle) * targetRadius;
      const arrowSize = isConnected ? 5 : 3;
      ctx.beginPath();
      ctx.moveTo(arrowX, arrowY);
      ctx.lineTo(
        arrowX - arrowSize * Math.cos(angle - Math.PI / 6),
        arrowY - arrowSize * Math.sin(angle - Math.PI / 6),
      );
      ctx.lineTo(
        arrowX - arrowSize * Math.cos(angle + Math.PI / 6),
        arrowY - arrowSize * Math.sin(angle + Math.PI / 6),
      );
      ctx.closePath();
      ctx.fillStyle = isConnected ? "rgba(250, 82, 15, 0.4)" : "rgba(31, 31, 31, 0.15)";
      ctx.fill();
    }

    const searchLower = searchTerm.toLowerCase();
    for (const node of simNodes) {
      if (node.x == null) continue;
      const radius = getRadius(node.id);
      const color = getNodeColor(node);
      const isSelected = node.id === selectedNodeId;
      const isMatch = searchTerm && (
        node.id.toLowerCase().includes(searchLower) ||
        (node.properties?.description ?? "").toLowerCase().includes(searchLower) ||
        (node.properties?.entity_type ?? "").toLowerCase().includes(searchLower)
      );
      const dimmed = searchTerm && !isMatch;
      const isHovered = hoveredNodeRef.current && node.id === hoveredNodeRef.current.id;

      ctx.beginPath();
      ctx.arc(node.x, node.y!, radius, 0, 2 * Math.PI);
      ctx.fillStyle = dimmed ? `${color}33` : color;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "#fa520f";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      if (isHovered) {
        ctx.strokeStyle = "#fa520f";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      const degree = degreeMap.get(node.id) ?? 1;
      const showLabel = isMini ? (isSelected || isHovered) : (degree >= 3 || isSelected || isMatch || isHovered);
      if (showLabel) {
        const fontSize = isMini ? 10 : Math.max(3, radius * 0.8);
        ctx.font = `${isSelected ? "bold " : ""}${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillStyle = dimmed ? "#1f1f1f33" : "#1f1f1f";
        ctx.fillText(node.id, node.x, node.y! + radius + 2);
      }
    }

    ctx.restore();
  }, [selectedNodeId, searchTerm, degreeMap, getRadius, isMini]);

  useEffect(() => {
    if (!focusNodeId) return;
    const canvas = canvasRef.current;
    if (!canvas || simNodesRef.current.length === 0) return;

    const targetNode = simNodesRef.current.find((n) => n.id === focusNodeId);
    if (!targetNode || targetNode.x == null) return;

    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const h = rect.height;
    const t = transformRef.current;
    t.x = w / 2 - targetNode.x * t.k;
    t.y = h / 2 - targetNode.y! * t.k;

    let start: number | null = null;
    const duration = 2000;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const animate = (timestamp: number) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      if (elapsed > duration) return;
      const progress = elapsed / duration;
      const pulseRadius = getRadius(focusNodeId) + 20 * Math.sin(progress * Math.PI * 4) * (1 - progress);
      const alpha = 0.4 * (1 - progress);

      const { x: tx, y: ty, k } = transformRef.current;
      ctx.save();
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      ctx.translate(tx, ty);
      ctx.scale(k, k);
      ctx.beginPath();
      ctx.arc(targetNode.x!, targetNode.y!, pulseRadius, 0, 2 * Math.PI);
      ctx.strokeStyle = `rgba(250, 82, 15, ${alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();

      requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [focusNodeId, getRadius]);

  return (
    <div ref={containerRef} className="flex-1 relative" style={{ background: isMini ? "transparent" : "#fef9ef" }} data-testid="graph-viewer">
      <canvas ref={canvasRef} className="absolute inset-0" />
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center" style={{ color: "var(--color-text-muted)" }}>
          No nodes to display
        </div>
      )}
    </div>
  );
}
