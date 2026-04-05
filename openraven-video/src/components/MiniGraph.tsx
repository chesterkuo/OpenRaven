import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  SimulationNodeDatum,
} from "d3-force";
import React, { useMemo } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { colors } from "../styles";

type NodeType = "technology" | "concept" | "person" | "organization" | "event" | "location";

interface GraphNode extends SimulationNodeDatum {
  id: string;
  type: NodeType;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
}

const NODE_COLORS: Record<NodeType, string> = {
  technology: colors.brand,
  concept: colors.text,
  person: colors.brandAmber,
  organization: colors.darkOrange,
  event: colors.gold,
  location: "#8b6914",
};

// Generate deterministic sample graph data
function generateGraphData(): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const types: NodeType[] = ["technology", "concept", "person", "organization", "event", "location"];
  const labels = [
    "NDA", "GDPR", "Contract Law", "IP Rights", "Data Privacy",
    "Compliance", "Due Diligence", "Risk Assessment", "Legal AI",
    "SaaS Terms", "Arbitration", "Force Majeure", "Liability",
    "Indemnity", "Warranty", "Confidentiality", "Jurisdiction",
    "Dispute Resolution", "License", "Patent", "Copyright",
    "Trademark", "Trade Secret", "Employment Law", "Corporate Gov.",
    "Regulatory", "Audit", "Forensics", "Discovery", "Mediation",
    "Securities", "Tax Law", "Real Estate", "Insurance", "Banking",
    "Antitrust", "Environmental", "Immigration", "Consumer", "Maritime",
  ];

  const nodes: GraphNode[] = labels.map((label, i) => ({
    id: `n${i}`,
    type: types[i % types.length],
    label,
  }));

  const edges: GraphEdge[] = [];
  // Create a connected graph with clusters
  for (let i = 1; i < nodes.length; i++) {
    edges.push({ source: nodes[i].id, target: nodes[Math.floor(i / 3)].id });
    if (i % 4 === 0 && i > 4) {
      edges.push({ source: nodes[i].id, target: nodes[i - 3].id });
    }
  }

  return { nodes, edges };
}

// Pre-compute layout (runs once via useMemo)
function computeLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number) {
  const simNodes = nodes.map((n) => ({ ...n }));
  const simLinks = edges.map((e) => ({ source: e.source, target: e.target }));

  const sim = forceSimulation(simNodes)
    .force("link", forceLink(simLinks).id((d: any) => d.id).distance(80))
    .force("charge", forceManyBody().strength(-150))
    .force("center", forceCenter(width / 2, height / 2))
    .force("collide", forceCollide(20));

  // Run simulation to completion
  for (let i = 0; i < 300; i++) sim.tick();
  sim.stop();

  return { nodes: simNodes, links: simLinks };
}

type MiniGraphProps = {
  width?: number;
  height?: number;
};

export const MiniGraph: React.FC<MiniGraphProps> = ({ width = 1200, height = 700 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const data = useMemo(() => {
    const { nodes, edges } = generateGraphData();
    return computeLayout(nodes, edges, width, height);
  }, [width, height]);

  return (
    <svg width={width} height={height}>
      {/* Edges */}
      {data.links.map((link: any, i: number) => {
        const appearFrame = 10 + i * 3;
        const opacity = interpolate(frame, [appearFrame, appearFrame + 15], [0, 0.3], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <line
            key={`e${i}`}
            x1={link.source.x}
            y1={link.source.y}
            x2={link.target.x}
            y2={link.target.y}
            stroke={colors.textMuted}
            strokeWidth={1}
            opacity={opacity}
          />
        );
      })}

      {/* Nodes */}
      {data.nodes.map((node: any, i: number) => {
        const appearFrame = 5 + i * 4;
        const scale = spring({
          frame: frame - appearFrame,
          fps,
          from: 0,
          to: 1,
          config: { damping: 10, stiffness: 100 },
        });

        const radius = 6 + (i < 5 ? 8 : i < 15 ? 4 : 0);
        const nodeColor = NODE_COLORS[node.type as NodeType];

        return (
          <g key={node.id} transform={`translate(${node.x},${node.y}) scale(${scale})`}>
            <circle r={radius} fill={nodeColor} />
            {radius > 8 && (
              <text
                y={radius + 14}
                textAnchor="middle"
                fontSize={11}
                fontWeight={600}
                fill={colors.text}
              >
                {node.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
};
