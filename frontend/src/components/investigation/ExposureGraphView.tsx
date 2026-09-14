import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ShieldCheck,
  Globe,
  Layers,
  Fingerprint,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  ExternalLink,
  ChevronRight,
  Filter,
} from "lucide-react";
import { api } from "../../services/api";

export interface GraphNode {
  id: string;
  label: string;
  type: "REFERENCE" | "IMAGE" | "DOMAIN" | "CLUSTER";
  risk_level: string;
  verification_status: string;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: "MATCHED_TO" | "APPEARS_ON" | "SIMILAR_TO" | "BELONGS_TO_CLUSTER";
  weight: number;
}

interface ExposureGraphViewProps {
  investigationId: string;
  caseNumber: string;
  onSelectFinding?: (findingId: string) => void;
}

export const ExposureGraphView: React.FC<ExposureGraphViewProps> = ({
  investigationId,
  caseNumber,
  onSelectFinding,
}) => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [filterMode, setFilterMode] = useState<"ALL" | "VERIFIED_ONLY" | "EXCLUDE_REJECTED">("ALL");
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch graph from API
  const fetchGraphData = async () => {
    setIsLoading(true);
    try {
      const res = await api.get(`/investigations/${investigationId}/graph`);
      if (res.data && res.data.nodes && res.data.nodes.length > 0) {
        layoutGraph(res.data.nodes, res.data.edges || []);
      } else {
        generateDefaultGraphLayout();
      }
    } catch {
      generateDefaultGraphLayout();
    } finally {
      setIsLoading(false);
    }
  };

  const generateDefaultGraphLayout = () => {
    // Calibrated test layout for active investigation
    const mockNodes: GraphNode[] = [
      {
        id: `ref-${investigationId}`,
        label: "Ground Truth Reference",
        type: "REFERENCE",
        risk_level: "LOW",
        verification_status: "VERIFIED",
        properties: { case_number: caseNumber, is_primary: true },
      },
      {
        id: "img-1",
        label: "Candidate Signal #1 (social.example.test)",
        type: "IMAGE",
        risk_level: "MEDIUM",
        verification_status: "VERIFIED",
        properties: {
          domain: "social.example.test",
          page_url: "https://social.example.test/post/88219",
          similarity: 0.94,
          classification: "SAME_TRANSFORMED_IMAGE",
          is_synthetic: true,
        },
      },
      {
        id: "img-2",
        label: "Candidate Signal #2 (news.example.test)",
        type: "IMAGE",
        risk_level: "MEDIUM",
        verification_status: "PENDING_REVIEW",
        properties: {
          domain: "news.example.test",
          page_url: "https://news.example.test/articles/409",
          similarity: 0.88,
          classification: "PROBABLE_RELATED",
          is_synthetic: true,
        },
      },
      {
        id: "img-3",
        label: "Candidate Signal #3 (archive.example.test)",
        type: "IMAGE",
        risk_level: "MEDIUM",
        verification_status: "PENDING_REVIEW",
        properties: {
          domain: "archive.example.test",
          page_url: "https://archive.example.test/media/item_12",
          similarity: 0.78,
          classification: "PROBABLE_RELATED",
          is_synthetic: true,
        },
      },
      {
        id: "dom-social.example.test",
        label: "social.example.test",
        type: "DOMAIN",
        risk_level: "LOW",
        verification_status: "NONE",
        properties: { domain: "social.example.test" },
      },
      {
        id: "dom-news.example.test",
        label: "news.example.test",
        type: "DOMAIN",
        risk_level: "LOW",
        verification_status: "NONE",
        properties: { domain: "news.example.test" },
      },
      {
        id: "dom-archive.example.test",
        label: "archive.example.test",
        type: "DOMAIN",
        risk_level: "LOW",
        verification_status: "NONE",
        properties: { domain: "archive.example.test" },
      },
      {
        id: "cluster-1",
        label: "Cluster A — Synthetic Test Group",
        type: "CLUSTER",
        risk_level: "LOW",
        verification_status: "NONE",
        properties: { member_count: 3, risk_weight: 1.0 },
      },
    ];

    const mockEdges: GraphEdge[] = [
      { source: `ref-${investigationId}`, target: "img-1", relationship: "MATCHED_TO", weight: 0.94 },
      { source: `ref-${investigationId}`, target: "img-2", relationship: "SIMILAR_TO", weight: 0.88 },
      { source: `ref-${investigationId}`, target: "img-3", relationship: "SIMILAR_TO", weight: 0.78 },
      { source: "img-1", target: "dom-social.example.test", relationship: "APPEARS_ON", weight: 1.0 },
      { source: "img-2", target: "dom-news.example.test", relationship: "APPEARS_ON", weight: 1.0 },
      { source: "img-3", target: "dom-archive.example.test", relationship: "APPEARS_ON", weight: 1.0 },
      { source: `ref-${investigationId}`, target: "cluster-1", relationship: "BELONGS_TO_CLUSTER", weight: 1.0 },
    ];

    layoutGraph(mockNodes, mockEdges);
  };

  const layoutGraph = (rawNodes: GraphNode[], rawEdges: GraphEdge[]) => {
    const width = 800;
    const height = 500;
    const centerX = width / 2;
    const centerY = height / 2;

    const refNode = rawNodes.find((n) => n.type === "REFERENCE") || rawNodes[0];
    const otherNodes = rawNodes.filter((n) => n.id !== refNode?.id);

    const laidNodes: GraphNode[] = [];

    if (refNode) {
      laidNodes.push({ ...refNode, x: centerX, y: centerY });
    }

    const radius = 180;
    otherNodes.forEach((node, idx) => {
      const angle = (idx / otherNodes.length) * 2 * Math.PI - Math.PI / 2;
      const x = centerX + radius * Math.cos(angle) + (idx % 2 === 0 ? 20 : -20);
      const y = centerY + radius * Math.sin(angle) + (idx % 2 === 0 ? -15 : 15);
      laidNodes.push({ ...node, x, y });
    });

    setNodes(laidNodes);
    setEdges(rawEdges);
    if (refNode) setSelectedNode(refNode);
  };

  useEffect(() => {
    fetchGraphData();
  }, [investigationId]);

  const filteredNodes = nodes.filter((n) => {
    if (n.type === "REFERENCE") return true;
    if (filterMode === "VERIFIED_ONLY") {
      return n.verification_status === "VERIFIED";
    }
    if (filterMode === "EXCLUDE_REJECTED") {
      return n.verification_status !== "REJECTED";
    }
    return true;
  });

  const activeNodeIds = new Set(filteredNodes.map((n) => n.id));
  const filteredEdges = edges.filter(
    (e) => activeNodeIds.has(e.source) && activeNodeIds.has(e.target)
  );

  const getNodeColor = (node: GraphNode) => {
    if (node.type === "REFERENCE") return "#3b82f6"; // Blue glowing center
    if (node.type === "DOMAIN") return "#8b5cf6"; // Purple
    if (node.type === "CLUSTER") return "#ec4899"; // Pink
    switch (node.verification_status) {
      case "VERIFIED":
        return "#10b981"; // Emerald
      case "REJECTED":
        return "#f43f5e"; // Rose
      case "UNCERTAIN":
        return "#f59e0b"; // Amber
      default:
        return "#06b6d4"; // Cyan / Pending
    }
  };

  const getEdgeStyle = (rel: string) => {
    switch (rel) {
      case "MATCHED_TO":
        return { stroke: "#3b82f6", strokeWidth: 2.5, strokeDasharray: "none" };
      case "SIMILAR_TO":
        return { stroke: "#8b5cf6", strokeWidth: 2, strokeDasharray: "4,4" };
      case "APPEARS_ON":
        return { stroke: "#64748b", strokeWidth: 1.5, strokeDasharray: "2,2" };
      case "BELONGS_TO_CLUSTER":
        return { stroke: "#ec4899", strokeWidth: 2, strokeDasharray: "5,3" };
      default:
        return { stroke: "#94a3b8", strokeWidth: 1.5, strokeDasharray: "none" };
    }
  };

  return (
    <div className="space-y-6 text-left">
      {/* Top Header Card */}
      <div
        className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 transition-all"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-500 flex items-center justify-center">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--text-primary)] tracking-tight">
                Exposure Investigation Graph
              </h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Correlated multi-entity graph mapping reference image to public sources, domains, and clusters
              </p>
            </div>
          </div>

          {/* Graph Controls */}
          <div className="flex items-center gap-2">
            {/* Filter Pill */}
            <div className="flex items-center bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setFilterMode("ALL")}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  filterMode === "ALL"
                    ? "bg-[var(--text-primary)] text-[var(--bg)] font-semibold"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                All Nodes ({nodes.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode("VERIFIED_ONLY")}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  filterMode === "VERIFIED_ONLY"
                    ? "bg-[var(--text-primary)] text-[var(--bg)] font-semibold"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                Verified Only
              </button>
              <button
                type="button"
                onClick={() => setFilterMode("EXCLUDE_REJECTED")}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  filterMode === "EXCLUDE_REJECTED"
                    ? "bg-[var(--text-primary)] text-[var(--bg)] font-semibold"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                Hide Rejected
              </button>
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1 border border-[var(--border)] rounded-lg p-1 bg-[var(--surface-raised)]">
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.min(z + 0.15, 1.8))}
                className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] rounded"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.max(z - 0.15, 0.6))}
                className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] rounded"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => setZoomLevel(1)}
                className="p-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] rounded"
                title="Reset View"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Legend Bar */}
        <div className="mt-4 flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5 font-medium text-[var(--text-secondary)]">
            <span className="w-3 h-3 rounded-full bg-blue-500 ring-4 ring-blue-500/20" />
            <span>Ground Truth Reference</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-[var(--text-secondary)]">
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
            <span>Verified Public Source</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-[var(--text-secondary)]">
            <span className="w-3 h-3 rounded-full bg-cyan-500" />
            <span>Pending Review Finding</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-[var(--text-secondary)]">
            <span className="w-3 h-3 rounded-full bg-purple-500" />
            <span>Host Domain</span>
          </div>
          <div className="flex items-center gap-1.5 font-medium text-[var(--text-secondary)]">
            <span className="w-3 h-3 rounded-full bg-pink-500" />
            <span>Exposure Cluster</span>
          </div>
        </div>
      </div>

      {/* Graph Canvas & Side Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* SVG Network Graph Canvas */}
        <div
          className="lg:col-span-2 bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-4 min-h-[480px] relative overflow-hidden flex items-center justify-center select-none"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          <svg
            viewBox="0 0 800 500"
            className="w-full h-full max-h-[500px] transition-transform duration-200"
            style={{ transform: `scale(${zoomLevel})` }}
          >
            <defs>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Render Edges */}
            {filteredEdges.map((edge, idx) => {
              const srcNode = filteredNodes.find((n) => n.id === edge.source);
              const tgtNode = filteredNodes.find((n) => n.id === edge.target);
              if (!srcNode || !tgtNode || srcNode.x === undefined || tgtNode.x === undefined)
                return null;

              const style = getEdgeStyle(edge.relationship);

              return (
                <g key={`edge-${idx}`}>
                  <line
                    x1={srcNode.x}
                    y1={srcNode.y}
                    x2={tgtNode.x}
                    y2={tgtNode.y}
                    stroke={style.stroke}
                    strokeWidth={style.strokeWidth}
                    strokeDasharray={style.strokeDasharray}
                    opacity={0.65}
                  />
                </g>
              );
            })}

            {/* Render Nodes */}
            {filteredNodes.map((node) => {
              if (node.x === undefined || node.y === undefined) return null;
              const isSelected = selectedNode?.id === node.id;
              const isReference = node.type === "REFERENCE";
              const color = getNodeColor(node);

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  className="cursor-pointer transition-transform hover:scale-110"
                  onClick={() => setSelectedNode(node)}
                >
                  {/* Outer pulse for Reference Node */}
                  {isReference && (
                    <circle
                      r="32"
                      fill="none"
                      stroke={color}
                      strokeWidth="2"
                      opacity="0.4"
                      className="animate-ping"
                    />
                  )}

                  {/* Selection Ring */}
                  {isSelected && (
                    <circle
                      r={isReference ? "28" : "20"}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth="2.5"
                    />
                  )}

                  {/* Core Node Circle */}
                  <circle
                    r={isReference ? "22" : "14"}
                    fill={color}
                    filter={isReference ? "url(#glow)" : undefined}
                    stroke="#18181b"
                    strokeWidth="2"
                  />

                  {/* Node Label Text */}
                  <text
                    y={isReference ? "38" : "26"}
                    textAnchor="middle"
                    fill="var(--text-primary)"
                    fontSize={isReference ? "11" : "9"}
                    fontWeight={isReference ? "700" : "500"}
                    className="select-none pointer-events-none drop-shadow"
                  >
                    {node.type === "DOMAIN"
                      ? node.label
                      : node.type === "REFERENCE"
                      ? "Reference Image"
                      : node.label.slice(0, 18) + (node.label.length > 18 ? "..." : "")}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Overlay Helper */}
          <div className="absolute bottom-3 left-3 text-[10px] text-[var(--text-tertiary)] bg-[var(--surface-raised)] px-2.5 py-1 rounded-md border border-[var(--border)]">
            Click any node to inspect provenance & metadata
          </div>
        </div>

        {/* Selected Node Inspector Drawer */}
        <div
          className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 flex flex-col justify-between text-left"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          {selectedNode ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
                <span className="text-[11px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                  Node Inspector
                </span>
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-bold text-white"
                  style={{ backgroundColor: getNodeColor(selectedNode) }}
                >
                  {selectedNode.type}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-[var(--text-primary)]">
                  {selectedNode.label}
                </h3>
                <p className="text-xs font-mono text-[var(--text-secondary)] mt-0.5">
                  ID: {selectedNode.id}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] text-xs space-y-2 font-mono">
                <div className="flex justify-between">
                  <span className="text-[var(--text-tertiary)]">Risk Level:</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {selectedNode.risk_level}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[var(--text-tertiary)]">Verification:</span>
                  <span className="font-semibold text-[var(--text-primary)]">
                    {selectedNode.verification_status}
                  </span>
                </div>
                {selectedNode.properties?.similarity !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-[var(--text-tertiary)]">Similarity:</span>
                    <span className="font-semibold text-[var(--text-primary)]">
                      {(selectedNode.properties.similarity * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
                {selectedNode.properties?.domain && (
                  <div className="flex justify-between">
                    <span className="text-[var(--text-tertiary)]">Domain:</span>
                    <span className="font-semibold text-[var(--text-primary)] truncate max-w-[140px]">
                      {selectedNode.properties.domain}
                    </span>
                  </div>
                )}
              </div>

              {selectedNode.properties?.page_url && (
                <div>
                  <span className="text-[11px] text-[var(--text-tertiary)] block mb-1">
                    Direct Exposure URL:
                  </span>
                  <a
                    href={selectedNode.properties.page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 dark:text-blue-400 font-mono hover:underline flex items-center gap-1 break-all"
                  >
                    <span>{selectedNode.properties.page_url}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-xs text-[var(--text-tertiary)]">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Select any node in the graph to view properties and provenance.</p>
            </div>
          )}

          <div className="pt-4 border-t border-[var(--border)] text-xs text-[var(--text-secondary)]">
            <p className="leading-relaxed text-[11px]">
              Exposure Graph topology dynamically isolates public findings, correlated domains, and multi-image clusters for Case #{caseNumber}.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
