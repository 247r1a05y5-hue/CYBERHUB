import React, { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../services/api";
import type {
  Participant,
  ParticipantImage,
  ParticipantPublicSource,
  DatasetStats,
  MatchCandidate,
  Platform,
  MatchStatus,
} from "../types/dataset";

// ---------------------------------------------------------------------------
// Styles (inline for zero-dependency)
// ---------------------------------------------------------------------------

const PLATFORM_ICONS: Record<string, string> = {
  instagram: "📸",
  linkedin: "💼",
  facebook: "👤",
  twitter: "🐦",
  tiktok: "🎵",
  youtube: "▶️",
  other: "🔗",
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="ds-stat-card">
      <div className="ds-stat-value">{value}</div>
      <div className="ds-stat-label">{label}</div>
      {sub && <div className="ds-stat-sub">{sub}</div>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "CONSENTED" ? "#22c55e"
    : status === "PENDING" ? "#f59e0b"
    : status === "REVOKED" || status === "EXPIRED" ? "#ef4444"
    : status === "INDEXED" ? "#3b82f6"
    : status === "FAILED" ? "#ef4444"
    : "#6b7280";

  return (
    <span style={{
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "999px",
      fontSize: "0.72rem",
      fontWeight: 700,
      letterSpacing: "0.04em",
      background: color + "22",
      color,
      border: `1px solid ${color}44`,
    }}>
      {status}
    </span>
  );
}

function MatchStatusBadge({ status }: { status: MatchStatus }) {
  const colorMap: Record<MatchStatus, string> = {
    PENDING_REVIEW: "#f59e0b",
    VERIFIED: "#22c55e",
    REJECTED: "#ef4444",
    UNCERTAIN: "#8b5cf6",
  };
  const color = colorMap[status] || "#6b7280";
  return (
    <span style={{
      display: "inline-block",
      padding: "3px 12px",
      borderRadius: "999px",
      fontSize: "0.75rem",
      fontWeight: 700,
      background: color + "22",
      color,
      border: `1px solid ${color}55`,
    }}>
      {status.replace("_", " ")}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function DatasetPage() {
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [selected, setSelected] = useState<Participant | null>(null);
  const [images, setImages] = useState<ParticipantImage[]>([]);
  const [sources, setSources] = useState<ParticipantPublicSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"dashboard" | "enroll" | "match">("dashboard");

  // Enroll form state
  const [enrollName, setEnrollName] = useState("");
  const [enrollCode, setEnrollCode] = useState("");
  const [enrollConsent, setEnrollConsent] = useState(false);
  const [enrollInstagram, setEnrollInstagram] = useState("");
  const [enrollLinkedIn, setEnrollLinkedIn] = useState("");
  const [enrollFacebook, setEnrollFacebook] = useState("");
  const [enrollOther, setEnrollOther] = useState("");
  const [enrollPhoto, setEnrollPhoto] = useState<File | null>(null);
  const [enrolling, setEnrolling] = useState(false);

  // Match state
  const [matchFile, setMatchFile] = useState<File | null>(null);
  const [matchPreview, setMatchPreview] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchCandidate | null>(null);
  const [matching, setMatching] = useState<string | null>(null);
  const [matchStage, setMatchStage] = useState<string>("");
  const [verifying, setVerifying] = useState(false);

  const photoInputRef = useRef<HTMLInputElement>(null);
  const matchInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get("/dataset/stats");
      setStats(res.data);
    } catch (e: any) {
      console.error("[DATASET] Failed to fetch stats:", e);
    }
  }, []);

  const fetchParticipants = useCallback(async () => {
    try {
      const res = await api.get("/dataset/participants");
      setParticipants(res.data);
    } catch (e: any) {
      console.error("[DATASET] Failed to fetch participants:", e);
    }
  }, []);

  const fetchParticipantDetails = useCallback(async (p: Participant) => {
    setSelected(p);
    try {
      // images are tracked via stats, sources visible in list
      const res = await api.get(`/dataset/participants/${p.id}`);
      // sources are in list endpoint — no separate image list endpoint needed
    } catch (e) {
      console.error("[DATASET] Detail fetch error:", e);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchParticipants();
  }, [fetchStats, fetchParticipants]);

  // ---------------------------------------------------------------------------
  // Enrollment
  // ---------------------------------------------------------------------------

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!enrollConsent) {
      setError("Participant consent checkbox is required before enrollment.");
      return;
    }
    if (!enrollName.trim()) {
      setError("Display name is required.");
      return;
    }

    setEnrolling(true);
    setError(null);
    setSuccess(null);

    try {
      // 1. Create participant
      const formData = new FormData();
      formData.append("display_name", enrollName.trim());
      if (enrollCode.trim()) formData.append("participant_code", enrollCode.trim());
      formData.append("grant_consent", "true");

      const createRes = await api.post("/dataset/participants", formData);
      const participant: Participant = createRes.data;

      // 2. Upload photo if provided
      if (enrollPhoto) {
        const imgForm = new FormData();
        imgForm.append("file", enrollPhoto);
        await api.post(`/dataset/participants/${participant.id}/images`, imgForm);
      }

      // 3. Add confirmed public sources
      const sourceMap: Array<{ platform: Platform; url: string }> = [];
      if (enrollInstagram.trim()) sourceMap.push({ platform: "instagram", url: enrollInstagram.trim() });
      if (enrollLinkedIn.trim()) sourceMap.push({ platform: "linkedin", url: enrollLinkedIn.trim() });
      if (enrollFacebook.trim()) sourceMap.push({ platform: "facebook", url: enrollFacebook.trim() });
      if (enrollOther.trim()) sourceMap.push({ platform: "other", url: enrollOther.trim() });

      for (const s of sourceMap) {
        await api.post(`/dataset/participants/${participant.id}/sources`, {
          platform: s.platform,
          url: s.url,
          participant_confirmed: true,
        });
      }

      setSuccess(`✓ Enrolled: ${participant.display_name} (${participant.participant_code})`);
      setEnrollName("");
      setEnrollCode("");
      setEnrollConsent(false);
      setEnrollInstagram("");
      setEnrollLinkedIn("");
      setEnrollFacebook("");
      setEnrollOther("");
      setEnrollPhoto(null);
      await fetchStats();
      await fetchParticipants();
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || "Enrollment failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setEnrolling(false);
    }
  };

  const handleIndexParticipant = async (p: Participant) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post(`/dataset/participants/${p.id}/index`);
      const results: ParticipantImage[] = res.data;
      const indexed = results.filter((img) => img.index_status === "INDEXED").length;
      const failed = results.filter((img) => img.index_status === "FAILED").length;
      setSuccess(
        `Indexing complete: ${indexed} face(s) indexed${failed ? `, ${failed} failed` : ""}.`
      );
      await fetchStats();
      await fetchParticipants();
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || "Indexing failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteParticipant = async (p: Participant) => {
    if (!confirm(`Delete participant "${p.display_name}"? This removes all their data including AWS face vectors.`)) return;
    setLoading(true);
    setError(null);
    try {
      await api.delete(`/dataset/participants/${p.id}`);
      setSuccess(`Deleted participant ${p.display_name}.`);
      setSelected(null);
      await fetchStats();
      await fetchParticipants();
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || "Delete failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Camera Match
  // ---------------------------------------------------------------------------

  const handleMatchFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMatchFile(file);
    setMatchResult(null);
    setMatching(null);
    const url = URL.createObjectURL(file);
    setMatchPreview(url);
  };

  const handleRunMatch = async () => {
    if (!matchFile) return;
    setMatching("Uploading image...");
    setMatchResult(null);
    setError(null);

    const stages = [
      "Uploading image...",
      "Analyzing face...",
      "Searching dataset...",
      "Matching against indexed faces...",
      "Loading public sources...",
    ];
    let stageIdx = 0;
    const stageInterval = setInterval(() => {
      stageIdx = Math.min(stageIdx + 1, stages.length - 1);
      setMatching(stages[stageIdx]);
    }, 700);

    try {
      const formData = new FormData();
      formData.append("file", matchFile);
      formData.append("face_match_threshold", "80");

      const res = await api.post("/dataset/match", formData);
      clearInterval(stageInterval);
      setMatching(null);
      setMatchResult(res.data);
    } catch (e: any) {
      clearInterval(stageInterval);
      setMatching(null);
      const msg = e.response?.data?.detail || e.message || "Match failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  };

  const handleVerify = async (status: "VERIFIED" | "REJECTED" | "UNCERTAIN") => {
    if (!matchResult) return;
    setVerifying(true);
    setError(null);
    try {
      await api.post(`/dataset/matches/${matchResult.match_id}/verify`, {
        status,
        verification_note: null,
      });
      setMatchResult({ ...matchResult, match_status: status });
      setSuccess(`Match ${status.toLowerCase()}.`);
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || "Verification failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
    } finally {
      setVerifying(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="ds-page">
      <style>{`
        .ds-page {
          min-height: 100vh;
          background: #09090b;
          color: #f4f4f5;
          font-family: 'Inter', 'Segoe UI', sans-serif;
          padding: 0;
        }
        .ds-header {
          background: linear-gradient(135deg, #0f0f13 0%, #1a0a2e 50%, #0f0f13 100%);
          border-bottom: 1px solid #27272a;
          padding: 24px 32px;
          display: flex;
          align-items: center;
          gap: 16px;
        }
        .ds-header-icon {
          width: 44px; height: 44px;
          background: linear-gradient(135deg, #7c3aed, #4f46e5);
          border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          font-size: 20px;
        }
        .ds-header-title { font-size: 1.4rem; font-weight: 800; letter-spacing: -0.02em; }
        .ds-header-sub { font-size: 0.82rem; color: #71717a; margin-top: 2px; }
        .ds-tabs {
          display: flex;
          gap: 4px;
          padding: 16px 32px 0;
          border-bottom: 1px solid #27272a;
          background: #0f0f13;
        }
        .ds-tab {
          padding: 10px 20px;
          border-radius: 8px 8px 0 0;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          background: transparent;
          color: #71717a;
          transition: all 0.15s;
          border-bottom: 2px solid transparent;
        }
        .ds-tab:hover { color: #a1a1aa; }
        .ds-tab.active {
          color: #a78bfa;
          border-bottom: 2px solid #7c3aed;
          background: #7c3aed11;
        }
        .ds-body { padding: 32px; max-width: 1200px; margin: 0 auto; }
        .ds-stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 32px; }
        .ds-stat-card {
          background: linear-gradient(135deg, #18181b 0%, #1c1c22 100%);
          border: 1px solid #27272a;
          border-radius: 16px;
          padding: 20px;
          text-align: center;
        }
        .ds-stat-value { font-size: 2rem; font-weight: 800; color: #a78bfa; }
        .ds-stat-label { font-size: 0.78rem; color: #71717a; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
        .ds-stat-sub { font-size: 0.72rem; color: #52525b; margin-top: 2px; }
        .ds-section-title {
          font-size: 1rem; font-weight: 700; color: #d4d4d8;
          margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
        }
        .ds-participant-list { display: flex; flex-direction: column; gap: 8px; }
        .ds-participant-row {
          background: #18181b;
          border: 1px solid #27272a;
          border-radius: 12px;
          padding: 14px 18px;
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ds-participant-row:hover { border-color: #7c3aed44; background: #1e1824; }
        .ds-participant-row.selected { border-color: #7c3aed; background: #1e1824; }
        .ds-participant-code {
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.75rem;
          color: #7c3aed;
          background: #7c3aed18;
          padding: 2px 8px;
          border-radius: 6px;
          font-weight: 700;
        }
        .ds-participant-name { font-weight: 600; flex: 1; }
        .ds-participant-actions { display: flex; gap: 8px; }
        .ds-btn {
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          border: none;
          transition: all 0.15s;
        }
        .ds-btn-primary {
          background: linear-gradient(135deg, #7c3aed, #4f46e5);
          color: white;
        }
        .ds-btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
        .ds-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .ds-btn-ghost {
          background: transparent;
          color: #71717a;
          border: 1px solid #3f3f46;
        }
        .ds-btn-ghost:hover { color: #d4d4d8; border-color: #71717a; }
        .ds-btn-danger {
          background: transparent;
          color: #ef4444;
          border: 1px solid #ef444433;
        }
        .ds-btn-danger:hover { background: #ef444411; }
        .ds-btn-verify {
          background: #22c55e22;
          color: #22c55e;
          border: 1px solid #22c55e44;
        }
        .ds-btn-verify:hover { background: #22c55e33; }
        .ds-btn-reject {
          background: #ef444422;
          color: #ef4444;
          border: 1px solid #ef444444;
        }
        .ds-btn-reject:hover { background: #ef444433; }
        .ds-form { display: flex; flex-direction: column; gap: 16px; max-width: 540px; }
        .ds-form-group { display: flex; flex-direction: column; gap: 6px; }
        .ds-label { font-size: 0.82rem; font-weight: 600; color: #a1a1aa; }
        .ds-input {
          background: #18181b;
          border: 1px solid #3f3f46;
          border-radius: 8px;
          padding: 10px 14px;
          color: #f4f4f5;
          font-size: 0.88rem;
          transition: border-color 0.15s;
          outline: none;
          font-family: inherit;
        }
        .ds-input:focus { border-color: #7c3aed; }
        .ds-input::placeholder { color: #52525b; }
        .ds-checkbox-row {
          display: flex; align-items: center; gap: 10px;
          padding: 14px;
          background: #18181b;
          border: 1px solid #3f3f46;
          border-radius: 8px;
          cursor: pointer;
        }
        .ds-checkbox-row input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; accent-color: #7c3aed; }
        .ds-consent-text { font-size: 0.83rem; color: #a1a1aa; }
        .ds-alert {
          padding: 12px 16px;
          border-radius: 10px;
          font-size: 0.85rem;
          font-weight: 500;
          margin-bottom: 16px;
        }
        .ds-alert-error { background: #ef444411; border: 1px solid #ef444433; color: #fca5a5; }
        .ds-alert-success { background: #22c55e11; border: 1px solid #22c55e33; color: #86efac; }
        .ds-alert-info { background: #3b82f611; border: 1px solid #3b82f633; color: #93c5fd; }
        .ds-match-area {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 24px;
        }
        .ds-match-upload {
          background: #18181b;
          border: 2px dashed #3f3f46;
          border-radius: 16px;
          padding: 32px;
          text-align: center;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ds-match-upload:hover { border-color: #7c3aed44; background: #1e1824; }
        .ds-match-preview { border-radius: 12px; max-width: 100%; max-height: 220px; object-fit: cover; }
        .ds-match-result {
          background: linear-gradient(135deg, #0f0f13 0%, #1a0a2e 100%);
          border: 1px solid #7c3aed44;
          border-radius: 16px;
          padding: 24px;
        }
        .ds-match-title { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; color: #7c3aed; text-transform: uppercase; margin-bottom: 8px; }
        .ds-match-name { font-size: 1.4rem; font-weight: 800; margin-bottom: 4px; }
        .ds-match-code { font-family: monospace; color: #7c3aed; font-size: 0.88rem; }
        .ds-match-sim {
          font-size: 2.2rem; font-weight: 900;
          color: #a78bfa;
          margin: 12px 0;
        }
        .ds-match-sim-label { font-size: 0.72rem; color: #52525b; text-transform: uppercase; letter-spacing: 0.05em; }
        .ds-sources-list { margin-top: 16px; }
        .ds-source-item {
          display: flex; align-items: center; gap: 10px;
          padding: 10px 12px;
          background: #18181b;
          border: 1px solid #27272a;
          border-radius: 8px;
          margin-bottom: 6px;
        }
        .ds-source-platform { font-size: 0.8rem; color: #71717a; flex: 1; }
        .ds-source-link {
          color: #7c3aed; font-size: 0.8rem; text-decoration: none;
          background: #7c3aed18; padding: 3px 10px; border-radius: 6px;
        }
        .ds-source-link:hover { background: #7c3aed33; }
        .ds-verify-actions { display: flex; gap: 8px; margin-top: 16px; }
        .ds-no-aws {
          background: #f59e0b11;
          border: 1px solid #f59e0b33;
          border-radius: 12px;
          padding: 16px;
          font-size: 0.85rem;
          color: #fbbf24;
          margin-bottom: 24px;
        }
        .ds-photo-drop {
          display: flex; flex-direction: column; align-items: center; gap: 8px;
          padding: 24px;
          background: #18181b;
          border: 2px dashed #3f3f46;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.15s;
        }
        .ds-photo-drop:hover { border-color: #7c3aed55; }
        .ds-stage-indicator {
          display: flex; align-items: center; gap: 8px;
          padding: 12px 16px;
          background: #3b82f611;
          border: 1px solid #3b82f633;
          border-radius: 10px;
          color: #93c5fd;
          font-size: 0.85rem;
          margin-bottom: 16px;
        }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .ds-spin { display: inline-block; animation: spin 1s linear infinite; }
        .ds-section-card {
          background: #18181b;
          border: 1px solid #27272a;
          border-radius: 16px;
          padding: 24px;
          margin-bottom: 24px;
        }
      `}</style>

      {/* Header */}
      <div className="ds-header">
        <div className="ds-header-icon">🧬</div>
        <div>
          <div className="ds-header-title">Controlled Dataset</div>
          <div className="ds-header-sub">AWS Rekognition · Face Enrollment & Match</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="ds-tabs">
        {(["dashboard", "enroll", "match"] as const).map((tab) => (
          <button
            key={tab}
            className={`ds-tab${activeTab === tab ? " active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "dashboard" ? "📊 Dashboard" : tab === "enroll" ? "➕ Enroll" : "🔍 Camera Match"}
          </button>
        ))}
      </div>

      <div className="ds-body">
        {/* Alerts */}
        {error && (
          <div className="ds-alert ds-alert-error">
            ⚠️ {error}
            <button
              onClick={() => setError(null)}
              style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer" }}
            >
              ✕
            </button>
          </div>
        )}
        {success && (
          <div className="ds-alert ds-alert-success">
            {success}
            <button
              onClick={() => setSuccess(null)}
              style={{ float: "right", background: "none", border: "none", color: "inherit", cursor: "pointer" }}
            >
              ✕
            </button>
          </div>
        )}

        {/* AWS Warning */}
        {stats && !stats.aws_configured && (
          <div className="ds-no-aws">
            ⚡ <strong>AWS Rekognition not configured.</strong> Set <code>AWS_REGION</code> and{" "}
            <code>AWS_REKOGNITION_COLLECTION_ID</code> in your <code>.env</code> file, then add AWS credentials via
            environment variables or <code>~/.aws/credentials</code> to enable real face indexing and matching.
          </div>
        )}

        {/* ── DASHBOARD TAB ─────────────────────────────────────── */}
        {activeTab === "dashboard" && (
          <>
            {/* Stats row */}
            <div className="ds-stats-row">
              <StatCard label="Participants" value={stats?.participant_count ?? "—"} />
              <StatCard label="Images Uploaded" value={stats?.image_count ?? "—"} />
              <StatCard label="Faces Indexed" value={stats?.indexed_face_count ?? "—"} sub="AWS Rekognition" />
              <StatCard label="Public Sources" value={stats?.source_count ?? "—"} sub="participant-confirmed" />
              <StatCard
                label="Consent Pending"
                value={stats?.consent_pending_count ?? "—"}
                sub={stats?.consent_pending_count ? "action required" : "all consented"}
              />
            </div>

            {/* Participant list */}
            <div className="ds-section-card">
              <div className="ds-section-title">
                👥 Enrolled Participants
                <button className="ds-btn ds-btn-ghost" style={{ marginLeft: "auto", fontSize: "0.78rem" }} onClick={() => { fetchParticipants(); fetchStats(); }}>
                  ↻ Refresh
                </button>
              </div>
              {participants.length === 0 ? (
                <div style={{ color: "#52525b", fontSize: "0.88rem", textAlign: "center", padding: "32px" }}>
                  No participants enrolled yet. Go to <strong>Enroll</strong> tab to add the first one.
                </div>
              ) : (
                <div className="ds-participant-list">
                  {participants.map((p) => (
                    <div
                      key={p.id}
                      className={`ds-participant-row${selected?.id === p.id ? " selected" : ""}`}
                      onClick={() => setSelected(selected?.id === p.id ? null : p)}
                    >
                      <span className="ds-participant-code">{p.participant_code}</span>
                      <span className="ds-participant-name">{p.display_name}</span>
                      <StatusBadge status={p.consent_status} />
                      <div className="ds-participant-actions">
                        <button
                          className="ds-btn ds-btn-ghost"
                          onClick={(e) => { e.stopPropagation(); handleIndexParticipant(p); }}
                          disabled={loading || p.consent_status !== "CONSENTED"}
                          title={p.consent_status !== "CONSENTED" ? "Consent required before indexing" : "Index into AWS Rekognition"}
                        >
                          ⚡ Index
                        </button>
                        <button
                          className="ds-btn ds-btn-danger"
                          onClick={(e) => { e.stopPropagation(); handleDeleteParticipant(p); }}
                          disabled={loading}
                        >
                          🗑
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {/* ── ENROLL TAB ───────────────────────────────────────── */}
        {activeTab === "enroll" && (
          <div className="ds-section-card">
            <div className="ds-section-title">➕ Enroll New Participant</div>
            <form className="ds-form" onSubmit={handleEnroll}>
              <div className="ds-form-group">
                <label className="ds-label">Display Name *</label>
                <input
                  className="ds-input"
                  placeholder="e.g. Jane Smith"
                  value={enrollName}
                  onChange={(e) => setEnrollName(e.target.value)}
                  required
                />
              </div>
              <div className="ds-form-group">
                <label className="ds-label">Participant Code (optional — auto-generated if blank)</label>
                <input
                  className="ds-input"
                  placeholder="e.g. P014"
                  value={enrollCode}
                  onChange={(e) => setEnrollCode(e.target.value)}
                />
              </div>

              {/* Participant photo */}
              <div className="ds-form-group">
                <label className="ds-label">Authorized Photo (optional — can index later)</label>
                <div
                  className="ds-photo-drop"
                  onClick={() => photoInputRef.current?.click()}
                >
                  {enrollPhoto ? (
                    <span style={{ color: "#a78bfa" }}>📎 {enrollPhoto.name}</span>
                  ) : (
                    <>
                      <span style={{ fontSize: "1.5rem" }}>📷</span>
                      <span style={{ color: "#71717a", fontSize: "0.85rem" }}>Click to upload authorized photo</span>
                      <span style={{ color: "#52525b", fontSize: "0.75rem" }}>JPEG / PNG / WebP · max 5 MB · exactly one face</span>
                    </>
                  )}
                  <input
                    ref={photoInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    style={{ display: "none" }}
                    onChange={(e) => setEnrollPhoto(e.target.files?.[0] || null)}
                  />
                </div>
              </div>

              {/* Social URLs */}
              <div className="ds-form-group">
                <label className="ds-label">Instagram URL (participant-confirmed)</label>
                <input
                  className="ds-input"
                  placeholder="https://instagram.com/username"
                  value={enrollInstagram}
                  onChange={(e) => setEnrollInstagram(e.target.value)}
                  type="url"
                />
              </div>
              <div className="ds-form-group">
                <label className="ds-label">LinkedIn URL (participant-confirmed)</label>
                <input
                  className="ds-input"
                  placeholder="https://linkedin.com/in/username"
                  value={enrollLinkedIn}
                  onChange={(e) => setEnrollLinkedIn(e.target.value)}
                  type="url"
                />
              </div>
              <div className="ds-form-group">
                <label className="ds-label">Facebook URL (participant-confirmed)</label>
                <input
                  className="ds-input"
                  placeholder="https://facebook.com/username"
                  value={enrollFacebook}
                  onChange={(e) => setEnrollFacebook(e.target.value)}
                  type="url"
                />
              </div>
              <div className="ds-form-group">
                <label className="ds-label">Other URL (participant-confirmed)</label>
                <input
                  className="ds-input"
                  placeholder="https://..."
                  value={enrollOther}
                  onChange={(e) => setEnrollOther(e.target.value)}
                  type="url"
                />
              </div>

              {/* Consent checkbox */}
              <label className="ds-checkbox-row">
                <input
                  type="checkbox"
                  checked={enrollConsent}
                  onChange={(e) => setEnrollConsent(e.target.checked)}
                />
                <span className="ds-consent-text">
                  I confirm that this participant has given explicit, informed consent for their photograph to be
                  stored and indexed for face recognition within this controlled dataset. All provided URLs are
                  participant-confirmed public profiles.
                </span>
              </label>

              <button
                type="submit"
                className="ds-btn ds-btn-primary"
                disabled={enrolling || !enrollConsent}
                style={{ width: "100%", padding: "12px" }}
              >
                {enrolling ? (
                  <span><span className="ds-spin">⟳</span> Enrolling...</span>
                ) : (
                  "Enroll Participant"
                )}
              </button>
            </form>
          </div>
        )}

        {/* ── MATCH TAB ────────────────────────────────────────── */}
        {activeTab === "match" && (
          <div className="ds-match-area">
            {/* Upload side */}
            <div>
              <div className="ds-section-card">
                <div className="ds-section-title">📷 Query Image</div>
                <div
                  className="ds-match-upload"
                  onClick={() => matchInputRef.current?.click()}
                >
                  {matchPreview ? (
                    <img src={matchPreview} className="ds-match-preview" alt="Query face" />
                  ) : (
                    <>
                      <span style={{ fontSize: "2.5rem" }}>👤</span>
                      <span style={{ color: "#71717a" }}>Click or drag a photo to search</span>
                      <span style={{ color: "#52525b", fontSize: "0.78rem" }}>Single face · JPEG/PNG/WebP</span>
                    </>
                  )}
                  <input
                    ref={matchInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    style={{ display: "none" }}
                    onChange={handleMatchFileChange}
                  />
                </div>

                {matchFile && (
                  <button
                    className="ds-btn ds-btn-primary"
                    onClick={handleRunMatch}
                    disabled={!!matching}
                    style={{ width: "100%", marginTop: "16px", padding: "12px" }}
                  >
                    {matching ? (
                      <span><span className="ds-spin">⟳</span> {matching}</span>
                    ) : (
                      "🔍 Search Dataset"
                    )}
                  </button>
                )}
              </div>

              {!stats?.aws_configured && (
                <div className="ds-alert ds-alert-info" style={{ marginTop: 0 }}>
                  ℹ️ AWS Rekognition is not configured. Match will return <code>AWS_NOT_CONFIGURED</code>.
                  This is <strong>not</strong> a "no match" result — it is a configuration error.
                </div>
              )}
            </div>

            {/* Result side */}
            <div>
              {matchResult && (
                <div className="ds-match-result">
                  {matchResult.error_code && matchResult.error_code !== "NO_DATASET_MATCH" ? (
                    <>
                      <div className="ds-match-title">⚠️ Search Error</div>
                      <div style={{ color: "#fca5a5", fontWeight: 700, fontSize: "1rem", marginBottom: 8 }}>
                        {matchResult.error_code}
                      </div>
                      <div style={{ color: "#71717a", fontSize: "0.85rem" }}>
                        {matchResult.error_message}
                      </div>
                      <div style={{ marginTop: 12, fontSize: "0.78rem", color: "#52525b" }}>
                        Note: AWS failures are distinct from "no match" — this does not mean the face was not found.
                      </div>
                    </>
                  ) : matchResult.error_code === "NO_DATASET_MATCH" ? (
                    <>
                      <div className="ds-match-title">🔍 No Match Found</div>
                      <div style={{ color: "#71717a", fontSize: "0.88rem" }}>
                        No face in the dataset matched the query image above the similarity threshold.
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="ds-match-title">🎯 Match Candidate</div>
                      <div className="ds-match-name">{matchResult.display_name}</div>
                      <div className="ds-match-code">{matchResult.participant_code}</div>

                      <div style={{ margin: "16px 0" }}>
                        <div className="ds-match-sim">{matchResult.aws_similarity?.toFixed(1)}%</div>
                        <div className="ds-match-sim-label">AWS Rekognition Similarity</div>
                      </div>

                      {matchResult.local_similarity != null && (
                        <div style={{ fontSize: "0.78rem", color: "#71717a", marginBottom: 8 }}>
                          Local secondary similarity: {(matchResult.local_similarity * 100).toFixed(1)}%
                          ({matchResult.local_match_method})
                          <span style={{ color: "#52525b", marginLeft: 6 }}>(kept separate from AWS score)</span>
                        </div>
                      )}

                      <div style={{ marginBottom: 8 }}>
                        <MatchStatusBadge status={matchResult.match_status as MatchStatus} />
                      </div>

                      {/* Public Sources — the ONLY URLs shown, exactly as stored */}
                      {matchResult.public_sources.length > 0 ? (
                        <div className="ds-sources-list">
                          <div style={{ fontSize: "0.78rem", color: "#71717a", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Public Sources (participant-confirmed)
                          </div>
                          {matchResult.public_sources.map((src, i) => (
                            <div key={i} className="ds-source-item">
                              <span>{PLATFORM_ICONS[src.platform] || "🔗"}</span>
                              <span className="ds-source-platform" style={{ textTransform: "capitalize" }}>{src.platform}</span>
                              <a href={src.url} target="_blank" rel="noopener noreferrer" className="ds-source-link">
                                Open ↗
                              </a>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: "#52525b", fontSize: "0.82rem", margin: "12px 0" }}>
                          No participant-confirmed public sources on file.
                        </div>
                      )}

                      {/* Verify/Reject */}
                      {matchResult.match_status === "PENDING_REVIEW" && (
                        <div className="ds-verify-actions">
                          <button
                            className="ds-btn ds-btn-verify"
                            onClick={() => handleVerify("VERIFIED")}
                            disabled={verifying}
                          >
                            ✓ Verify Match
                          </button>
                          <button
                            className="ds-btn ds-btn-ghost"
                            onClick={() => handleVerify("UNCERTAIN")}
                            disabled={verifying}
                          >
                            ? Uncertain
                          </button>
                          <button
                            className="ds-btn ds-btn-reject"
                            onClick={() => handleVerify("REJECTED")}
                            disabled={verifying}
                          >
                            ✕ Reject
                          </button>
                        </div>
                      )}

                      {matchResult.match_status !== "PENDING_REVIEW" && (
                        <div style={{ marginTop: 12 }}>
                          <MatchStatusBadge status={matchResult.match_status as MatchStatus} />
                          <span style={{ color: "#52525b", fontSize: "0.78rem", marginLeft: 8 }}>
                            Verification recorded.
                          </span>
                        </div>
                      )}

                      <div style={{ marginTop: 16, padding: "10px 12px", background: "#18181b", borderRadius: 8, fontSize: "0.72rem", color: "#52525b" }}>
                        🔒 The participant's enrolled photograph is never displayed here.
                        Only participant-confirmed public URLs are shown above.
                      </div>
                    </>
                  )}
                </div>
              )}

              {!matchResult && !matching && (
                <div style={{ color: "#52525b", textAlign: "center", padding: "64px 32px" }}>
                  <div style={{ fontSize: "3rem", marginBottom: 16 }}>🧬</div>
                  <div>Upload a photo on the left and click <strong>Search Dataset</strong> to run a real AWS Rekognition face match.</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
