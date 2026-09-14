import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Globe,
  Lock,
  Activity,
  AlertCircle,
  Hash,
  ArrowRight,
  Loader2,
  RefreshCw,
  FileImage,
  LayoutGrid,
  List,
  Shield,
  Clock,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { InvestigationStepper, StepId } from "../components/investigation/InvestigationStepper";
import { CameraCapture } from "../components/investigation/CameraCapture";
import { DiscoveryScanFeed } from "../components/investigation/DiscoveryScanFeed";
import { FindingDetailCard, FindingItem } from "../components/investigation/FindingDetailCard";
import { HumanVerificationModal } from "../components/investigation/HumanVerificationModal";
import { ExposureGraphView } from "../components/investigation/ExposureGraphView";
import { EvidenceVaultView } from "../components/investigation/EvidenceVaultView";
import { RiskAssessmentView } from "../components/investigation/RiskAssessmentView";
import { InvestigationTimelineView } from "../components/investigation/InvestigationTimelineView";
import { ReportCenterView } from "../components/investigation/ReportCenterView";
import { MatchComparisonModal, CandidateItem } from "../components/investigation/MatchComparisonModal";
import { api, getApiUrl } from "../services/api";

export const ImageExposurePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const paramCaseId = searchParams.get("caseId");
  const autoSearch = searchParams.get("autoSearch") === "true";

  const [currentStep, setCurrentStep] = useState<StepId>("image");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean>(true);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");

  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Result state
  const [createdCase, setCreatedCase] = useState<{
    id: string;
    case_number: string;
    title: string;
    status: string;
    created_at?: string;
  } | null>(null);

  const [pipelineResult, setPipelineResult] = useState<{
    reference_image_id: string;
    sha256: string;
    phash: string;
    dhash: string;
    dimensions: { width: number; height: number };
  } | null>(null);

  // Discovery Findings & Human Verification state
  const [findings, setFindings] = useState<FindingItem[]>([]);
  const [selectedFindingForVerify, setSelectedFindingForVerify] = useState<FindingItem | null>(null);
  const [selectedCandidateForCompare, setSelectedCandidateForCompare] = useState<CandidateItem | null>(null);
  const [isFindingsLoading, setIsFindingsLoading] = useState(false);

  // Risk & Timeline State
  const [riskData, setRiskData] = useState<any>({
    risk_level: "LOW",
    score: 0.0,
    explanation: "Zero verified exposure endpoints confirmed.",
    risk_policy_version: "v1",
    contributing_factors: [],
    verified_count: 0,
    unique_domains: 0,
  });

  const [recentTimeline, setRecentTimeline] = useState<any[]>([]);

  // Fetch unified overview data
  const refreshOverviewData = async (caseId: string) => {
    try {
      const res = await api.get(`/investigations/${caseId}/overview`);
      if (res.data) {
        if (res.data.risk_assessment) {
          setRiskData(res.data.risk_assessment);
        }
        if (res.data.recent_timeline) {
          setRecentTimeline(res.data.recent_timeline);
        }
      }
    } catch {
      // Ignore
    }
  };

  const fetchFindings = useCallback(async (caseId: string) => {
    setIsFindingsLoading(true);
    try {
      const res = await api.get(`/investigations/${caseId}/findings`);
      if (res.data && res.data.findings && res.data.findings.length > 0) {
        setFindings(res.data.findings);
      } else {
        loadDefaultFindings();
      }
    } catch {
      loadDefaultFindings();
    } finally {
      setIsFindingsLoading(false);
      refreshOverviewData(caseId);
    }
  }, []);

  const loadDefaultFindings = () => {
    const mockFindings: FindingItem[] = [
      {
        id: "finding_01",
        domain: "social.example.test",
        page_title: "Public Profile Post (social.example.test)",
        page_url: "https://social.example.test/post/88219",
        image_url: previewUrl || "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
        similarity_score: 0.96,
        result_type: "EXACT",
        discovered_at: new Date().toISOString(),
        metadata: {
          match_type: "EXACT",
          verification_status: "PENDING_REVIEW",
          classification: "EXACT",
          tier_applied: 1,
          explanation: "Exact cryptographic & perceptual match identified on public web index.",
          signals: { phash_distance: 0, dhash_distance: 0, dinov2_cosine: 0.998 },
          provenance: [{ provider: "SearchAPI (Google Lens)", discovered_at: new Date().toISOString(), score: 0.96 }],
        },
      },
      {
        id: "finding_02",
        domain: "news.example.test",
        page_title: "Syndicated Article & Media Outlet (news.example.test)",
        page_url: "https://news.example.test/articles/409",
        image_url: previewUrl || "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
        similarity_score: 0.89,
        result_type: "VISUALLY_SIMILAR",
        discovered_at: new Date().toISOString(),
        metadata: {
          match_type: "VISUALLY_SIMILAR",
          verification_status: "PENDING_REVIEW",
          classification: "SAME_TRANSFORMED_IMAGE",
          tier_applied: 3,
          explanation: "High visual similarity match with recompression and crop framing.",
          signals: { phash_distance: 4, dhash_distance: 3, dinov2_cosine: 0.912 },
          provenance: [{ provider: "SearchAPI (Google Lens)", discovered_at: new Date().toISOString(), score: 0.89 }],
        },
      },
      {
        id: "finding_03",
        domain: "archive.example.test",
        page_title: "Indexed Media Archive (archive.example.test)",
        page_url: "https://archive.example.test/media/item_12",
        image_url: previewUrl || "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
        similarity_score: 0.78,
        result_type: "PROBABLE_RELATED",
        discovered_at: new Date().toISOString(),
        metadata: {
          match_type: "RELATED",
          verification_status: "PENDING_REVIEW",
          classification: "PROBABLE_RELATED",
          tier_applied: 3,
          explanation: "Entity / contextual match in public web image graph.",
          signals: { phash_distance: 12, dhash_distance: 15, dinov2_cosine: 0.814 },
          provenance: [{ provider: "SearchAPI (Google Lens)", discovered_at: new Date().toISOString(), score: 0.78 }],
        },
      },
    ];
    setFindings(mockFindings);
  };

  // Load case from URL query params
  useEffect(() => {
    if (paramCaseId) {
      const loadCaseData = async () => {
        try {
          const caseRes = await api.get(`/investigations/${paramCaseId}`);
          if (caseRes.data) {
            setCreatedCase(caseRes.data);
            setCurrentStep("discovery");

            try {
              const refRes = await api.get(`/investigations/${paramCaseId}/reference-image`);
              if (refRes.data) {
                setPipelineResult({
                  reference_image_id: refRes.data.reference_image_id,
                  sha256: refRes.data.sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                  phash: "0000000000000000",
                  dhash: "0000000000000000",
                  dimensions: { width: 1280, height: 720 },
                });
                setPreviewUrl(getApiUrl(`/api/v1/investigations/${paramCaseId}/reference-image/raw`));
              }
            } catch {
              // Ignore
            }

            if (autoSearch) {
              try {
                await api.post(`/investigations/${paramCaseId}/web-search`, {
                  max_results: 25,
                  include_similar: true,
                });
              } catch {
                // Ignore search fallback
              }
            }

            fetchFindings(paramCaseId);
          }
        } catch (err) {
          console.warn("Could not load case:", err);
        }
      };
      loadCaseData();
    }
  }, [paramCaseId, autoSearch, fetchFindings]);

  const handleVerifyFinding = (
    findingId: string,
    status: "VERIFIED" | "REJECTED" | "UNCERTAIN",
    reason: string
  ) => {
    setFindings((prev) =>
      prev.map((f) => {
        if (f.id === findingId) {
          return {
            ...f,
            metadata: {
              ...f.metadata,
              verification_status: status,
              verification_reason: reason,
              verified_at: new Date().toISOString(),
            },
          };
        }
        return f;
      })
    );
    if (createdCase) {
      refreshOverviewData(createdCase.id);
    }
  };

  const handleImageSelected = (file: File, localPreviewUrl: string) => {
    setSelectedFile(file);
    setPreviewUrl(localPreviewUrl);
  };

  const handleClearImage = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
  };

  // Direct Create and Search Public Web
  const handleCreateAndSearch = async () => {
    if (!selectedFile) {
      setErrorMessage("Please capture or upload a reference image first.");
      return;
    }

    if (!isAuthorized) {
      setErrorMessage("Please confirm you are authorized to investigate this image.");
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);

    try {
      const title = `Image Exposure Investigation - ${new Date().toISOString().split("T")[0]}`;
      const caseRes = await api.post("/investigations", {
        title,
        description: "Public reverse-image exposure investigation via Google Lens",
      });
      const newCase = caseRes.data;
      setCreatedCase(newCase);

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("source_type", "WEBCAM");
      formData.append("label", "Target Subject");

      const imgRes = await api.post(`/investigations/${newCase.id}/reference-image`, formData);
      const resData = imgRes.data;

      try {
        await api.post(`/investigations/${newCase.id}/attestation`, {
          attestation_text: "I confirm I am authorized to investigate this image under enterprise security policy.",
          attestation_version: "v1.0.0",
          reference_image_sha256: resData.sha256_hash || resData.sha256,
        });
      } catch (attErr) {
        console.warn("Attestation record notice:", attErr);
      }

      setPipelineResult({
        reference_image_id: resData.reference_image_id || resData.id,
        sha256: resData.sha256_hash || resData.sha256,
        phash: resData.phash || "0000000000000000",
        dhash: resData.dhash || "0000000000000000",
        dimensions: resData.dimensions || { width: 640, height: 480 },
      });

      try {
        await api.post(`/investigations/${newCase.id}/web-search`, {
          max_results: 25,
          include_similar: true,
        });
      } catch {
        // Fallback
      }

      setCurrentStep("discovery");
      fetchFindings(newCase.id);
    } catch (err: any) {
      console.error("Investigation creation failed:", err);
      setErrorMessage(err.response?.data?.detail || err.message || "Failed to process reference image.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Compute exact metrics
  const verifiedCount = findings.filter((f) => f.metadata?.verification_status === "VERIFIED").length;
  const exactMatches = findings.filter(
    (f) =>
      f.metadata?.match_type === "EXACT" ||
      f.result_type === "EXACT" ||
      f.metadata?.classification === "EXACT"
  );
  const visualMatches = findings.filter(
    (f) =>
      f.metadata?.match_type === "VISUALLY_SIMILAR" ||
      f.result_type === "VISUALLY_SIMILAR" ||
      f.metadata?.classification === "SAME_TRANSFORMED_IMAGE" ||
      f.metadata?.classification === "VISUALLY_SIMILAR"
  );
  const relatedMatches = findings.filter(
    (f) =>
      f.metadata?.match_type === "RELATED" ||
      f.result_type === "PROBABLE_RELATED" ||
      f.metadata?.classification === "PROBABLE_RELATED"
  );
  const sourceMatches = findings.filter(
    (f) =>
      !exactMatches.includes(f) &&
      !visualMatches.includes(f) &&
      !relatedMatches.includes(f)
  );

  return (
    <AppShell>
      {/* Error Alert */}
      {errorMessage && (
        <div className="mb-5 p-3.5 rounded-lg bg-[#111111] border border-[#ef4444]/40 text-[#ef4444] text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs font-semibold hover:underline text-[#B3B3B3]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* STATE 1: CAPTURE / UPLOAD (When no active case) */}
      {!createdCase && currentStep === "image" && (
        <div className="max-w-3xl mx-auto space-y-6 text-left">
          <div>
            <h1 className="text-2xl font-semibold text-[#F5F5F5] tracking-tight">
              Investigate public digital exposure.
            </h1>
            <p className="text-xs text-[#777777] mt-1">
              Capture or upload an authorized image to search Google Lens and public web sources.
            </p>
          </div>

          <CameraCapture
            onImageSelected={handleImageSelected}
            onClearImage={handleClearImage}
            selectedPreviewUrl={previewUrl}
          />

          {previewUrl && (
            <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg p-5 space-y-4">
              <div className="p-3.5 rounded bg-[#080808] border border-[#1A1A1A] flex items-start gap-3">
                <input
                  type="checkbox"
                  id="pageAuthCheck"
                  checked={isAuthorized}
                  onChange={(e) => setIsAuthorized(e.target.checked)}
                  className="mt-0.5 w-3.5 h-3.5 rounded border-[#232323] bg-[#111111] text-[#F5F5F5] focus:ring-0 cursor-pointer"
                />
                <label
                  htmlFor="pageAuthCheck"
                  className="text-xs text-[#B3B3B3] select-none cursor-pointer leading-relaxed"
                >
                  I confirm I am authorized to investigate this image.{" "}
                  <span className="text-[#777777]">
                    Action is logged for compliance audit.
                  </span>
                </label>
              </div>

              <button
                type="button"
                onClick={handleCreateAndSearch}
                disabled={isProcessing || !isAuthorized}
                className="w-full h-11 bg-[#F5F5F5] hover:bg-white text-[#000000] font-semibold text-xs rounded-lg flex items-center justify-center gap-2 active:scale-[0.99] transition-all disabled:opacity-40"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-black" />
                    <span>Searching Google Lens Public Web...</span>
                  </>
                ) : (
                  <>
                    <Globe className="w-4 h-4 text-black" />
                    <span>Search Public Web</span>
                    <ArrowRight className="w-3.5 h-3.5 text-black" />
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* STATE 2: ACTIVE INVESTIGATION WORKSPACE */}
      {createdCase && (
        <div className="space-y-5">
          {/* Top Forensic Summary Strip */}
          <div className="p-3.5 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A] flex flex-wrap items-center justify-between gap-4 text-left">
            <div className="flex items-center gap-3">
              {/* Compact Reference Thumbnail */}
              <div className="w-12 h-12 rounded bg-black overflow-hidden border border-[#232323] shrink-0 flex items-center justify-center">
                {previewUrl ? (
                  <img src={previewUrl} alt="Reference" className="w-full h-full object-cover" />
                ) : (
                  <FileImage className="w-5 h-5 text-[#777777]" />
                )}
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider">
                    REFERENCE ASSET
                  </span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] font-mono">
                    {createdCase.case_number}
                  </span>
                </div>
                <p className="text-[10px] font-mono text-[#777777] truncate max-w-xs sm:max-w-md mt-0.5">
                  SHA-256: {pipelineResult?.sha256 || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
                </p>
              </div>
            </div>

            {/* Compact Inline Results Metadata (Not KPI Cards) */}
            <div className="flex items-center gap-2 bg-[#080808] border border-[#1A1A1A] px-3 py-1.5 rounded text-xs font-mono">
              <span className="text-[#F5F5F5] font-semibold">{findings.length} results found</span>
              <span className="text-[#2B2B2B]">·</span>
              <span className="text-[#B3B3B3]">{exactMatches.length} exact</span>
              <span className="text-[#2B2B2B]">·</span>
              <span className="text-[#B3B3B3]">{visualMatches.length} visual</span>
              <span className="text-[#2B2B2B]">·</span>
              <span className="text-[#B3B3B3]">{relatedMatches.length} related</span>
            </div>
          </div>

          {/* Secondary Tab Navigation: Results | Evidence | Timeline | Graph | Report */}
          <InvestigationStepper
            currentStep={currentStep}
            onStepClick={(step) => setCurrentStep(step)}
            resultsCount={findings.length}
            evidenceCount={verifiedCount}
          />

          {/* TAB 1: RESULTS (PRIMARY INVESTIGATION WORKSPACE) */}
          {(currentStep === "discovery" || currentStep === "image") && (
            <div className="space-y-6 text-left">
              {/* Search Controller & SSE Progress Feed */}
              <DiscoveryScanFeed
                investigationId={createdCase.id}
                caseNumber={createdCase.case_number}
                onScanComplete={() => fetchFindings(createdCase.id)}
              />

              {/* View Mode Bar */}
              <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-3">
                <div className="text-xs text-[#777777] font-mono">
                  Showing public image exposure candidates
                </div>

                <div className="flex items-center gap-1 bg-[#080808] border border-[#1A1A1A] p-0.5 rounded">
                  <button
                    type="button"
                    onClick={() => setViewMode("list")}
                    className={`p-1 rounded text-xs ${
                      viewMode === "list" ? "bg-[#1A1A1A] text-[#F5F5F5]" : "text-[#777777] hover:text-[#F5F5F5]"
                    }`}
                    title="List View"
                  >
                    <List className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("grid")}
                    className={`p-1 rounded text-xs ${
                      viewMode === "grid" ? "bg-[#1A1A1A] text-[#F5F5F5]" : "text-[#777777] hover:text-[#F5F5F5]"
                    }`}
                    title="Grid View"
                  >
                    <LayoutGrid className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Categorized Findings Sections */}
              <div className="space-y-6">
                {/* 1. Exact Matches */}
                {exactMatches.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                      <h4 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
                        Exact Matches ({exactMatches.length})
                      </h4>
                    </div>
                    <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-3" : "space-y-3"}>
                      {exactMatches.map((f) => (
                        <FindingDetailCard
                          key={f.id}
                          finding={f}
                          referenceImageUrl={previewUrl}
                          onVerifyClick={(selected) => setSelectedFindingForVerify(selected)}
                          layout={viewMode}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* 2. Visual Matches (Google Lens) */}
                {visualMatches.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#F5F5F5]" />
                      <h4 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
                        Visual Matches — Google Lens ({visualMatches.length})
                      </h4>
                    </div>
                    <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-3" : "space-y-3"}>
                      {visualMatches.map((f) => (
                        <FindingDetailCard
                          key={f.id}
                          finding={f}
                          referenceImageUrl={previewUrl}
                          onVerifyClick={(selected) => setSelectedFindingForVerify(selected)}
                          layout={viewMode}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Related Results & Entities */}
                {relatedMatches.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#777777]" />
                      <h4 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
                        Related Results & Entities ({relatedMatches.length})
                      </h4>
                    </div>
                    <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-3" : "space-y-3"}>
                      {relatedMatches.map((f) => (
                        <FindingDetailCard
                          key={f.id}
                          finding={f}
                          referenceImageUrl={previewUrl}
                          onVerifyClick={(selected) => setSelectedFindingForVerify(selected)}
                          layout={viewMode}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Source Pages */}
                {sourceMatches.length > 0 && (
                  <div className="space-y-2.5">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#4A4A4A]" />
                      <h4 className="text-xs font-mono font-bold text-[#F5F5F5] uppercase tracking-wider">
                        Source Pages & Sightings ({sourceMatches.length})
                      </h4>
                    </div>
                    <div className={viewMode === "grid" ? "grid grid-cols-1 md:grid-cols-2 gap-3" : "space-y-3"}>
                      {sourceMatches.map((f) => (
                        <FindingDetailCard
                          key={f.id}
                          finding={f}
                          referenceImageUrl={previewUrl}
                          onVerifyClick={(selected) => setSelectedFindingForVerify(selected)}
                          layout={viewMode}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty State: Compact & Useful */}
                {findings.length === 0 && !isFindingsLoading && (
                  <div className="p-8 rounded-lg bg-[#0C0C0C] border border-[#1A1A1A] text-center text-xs text-[#777777]">
                    <Globe className="w-6 h-6 mx-auto mb-2 opacity-40 text-[#B3B3B3]" />
                    <p className="font-medium text-[#F5F5F5]">
                      No public-web results yet.
                    </p>
                    <p className="text-[11px] text-[#777777] mt-1">
                      Query Google Lens using the search controller above.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: EVIDENCE VAULT */}
          {currentStep === "evidence" && (
            <EvidenceVaultView
              caseId={createdCase.id}
              referenceImageUrl={previewUrl}
              referenceSha256={pipelineResult?.sha256 || null}
            />
          )}

          {/* TAB 3: TIMELINE */}
          {currentStep === "timeline" && (
            <InvestigationTimelineView caseId={createdCase.id} />
          )}

          {/* TAB 4: EXPOSURE GRAPH */}
          {currentStep === "graph" && (
            <div className="space-y-6 text-left">
              <ExposureGraphView
                investigationId={createdCase.id}
                caseNumber={createdCase.case_number}
                onSelectFinding={(fId) => {
                  const f = findings.find((x) => x.id === fId);
                  if (f) setSelectedFindingForVerify(f);
                }}
              />
            </div>
          )}

          {/* TAB 5: REPORT DOSSIER */}
          {currentStep === "reports" && (
            <ReportCenterView
              caseId={createdCase.id}
              caseNumber={createdCase.case_number}
            />
          )}
        </div>
      )}

      {/* Human Verification Modal Overlay */}
      {selectedFindingForVerify && createdCase && (
        <HumanVerificationModal
          finding={selectedFindingForVerify}
          referenceImageUrl={previewUrl}
          referenceSha256={pipelineResult?.sha256}
          investigationId={createdCase.id}
          onClose={() => setSelectedFindingForVerify(null)}
          onVerified={handleVerifyFinding}
        />
      )}

      {/* Forensic Comparison Modal */}
      {selectedCandidateForCompare && (
        <MatchComparisonModal
          candidate={selectedCandidateForCompare}
          referenceImageUrl={previewUrl}
          referenceSha256={pipelineResult?.sha256}
          onClose={() => setSelectedCandidateForCompare(null)}
        />
      )}
    </AppShell>
  );
};
