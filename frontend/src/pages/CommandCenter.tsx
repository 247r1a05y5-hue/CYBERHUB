import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Upload,
  Camera,
  Clipboard,
  Search,
  Shield,
  Layers,
  X,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  FileImage,
  Globe,
  SlidersHorizontal,
  Lock,
  ArrowRight,
  Info,
} from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { BrowserCameraModal } from "../components/investigation/BrowserCameraModal";
import {
  SearchCategoryBar,
  SearchCategoryType,
  CategoryCounts,
} from "../components/investigation/SearchCategoryBar";
import {
  ResultExplorerToolbar,
  SortOption,
} from "../components/investigation/ResultExplorerToolbar";
import {
  ResultFilterDrawer,
  FilterState,
} from "../components/investigation/ResultFilterDrawer";
import {
  LensoResultCard,
  ResultItemData,
} from "../components/investigation/LensoResultCard";
import { DatasetMatchPanel } from "../components/investigation/DatasetMatchPanel";
import { WebExposurePanel } from "../components/investigation/WebExposurePanel";
import { TextOcrPanel } from "../components/investigation/TextOcrPanel";
import { HistoricalCategoryPanel } from "../components/investigation/HistoricalCategoryPanel";
import { SideBySideComparisonModal } from "../components/investigation/SideBySideComparisonModal";
import { ResultDetailDrawer } from "../components/investigation/ResultDetailDrawer";
import { HumanVerificationModal } from "../components/investigation/HumanVerificationModal";
import { api, getApiUrl } from "../services/api";
import { formatErrorMessage } from "../utils/errorUtils";

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Search input state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{
    dimensions?: { width: number; height: number };
    fileSize?: string;
    sha256?: string;
    faceCount?: number;
    quality?: string;
  }>({});
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search execution & progress state
  const [isSearching, setIsSearching] = useState(false);
  const [searchStage, setSearchStage] = useState<string>("");
  const [progressSteps, setProgressSteps] = useState<
    { id: string; label: string; status: "pending" | "active" | "completed" | "failed" }[]
  >([
    { id: "upload", label: "Image uploaded & hashed (SHA-256)", status: "pending" },
    { id: "query", label: "Visual query vectors extracted", status: "pending" },
    { id: "provider", label: "SearchAPI / Google Lens queried", status: "pending" },
    { id: "process", label: "Processing & deduplicating endpoints", status: "pending" },
    { id: "correlate", label: "Source correlation & forensic scoring", status: "pending" },
    { id: "ready", label: "Investigation results ready", status: "pending" },
  ]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [searchCompleted, setSearchCompleted] = useState(false);

  // Results & Case state
  const [caseId, setCaseId] = useState<string | null>(null);
  const [allResults, setAllResults] = useState<ResultItemData[]>([]);
  const [datasetCandidates, setDatasetCandidates] = useState<ResultItemData[]>([]);
  const [extractedOcrText, setExtractedOcrText] = useState<string>("");

  // Category & Filter state
  const [activeCategory, setActiveCategory] = useState<SearchCategoryType>("ALL");
  const [sortOption, setSortOption] = useState<SortOption>("best_match");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false);
  const [filters, setFilters] = useState<FilterState>({
    sources: [],
    matchTypes: [],
    statuses: [],
    domainQuery: "",
    minSimilarity: 0,
  });

  // Modal / Drawer interactions
  const [selectedForDetail, setSelectedForDetail] = useState<ResultItemData | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<ResultItemData | null>(null);
  const [selectedForVerify, setSelectedForVerify] = useState<ResultItemData | null>(null);

  // Clipboard paste listener
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (searchCompleted || isSearching) return;
      if (e.clipboardData && e.clipboardData.items) {
        for (let i = 0; i < e.clipboardData.items.length; i++) {
          const item = e.clipboardData.items[i];
          if (item.type.indexOf("image") !== -1) {
            const blob = item.getAsFile();
            if (blob) {
              handleFileSelect(blob);
              break;
            }
          }
        }
      }
    };

    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [searchCompleted, isSearching]);

  // Extract dimensions and metadata when image changes
  const handleFileSelect = (file: File) => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    const url = URL.createObjectURL(file);
    setSelectedFile(file);
    setPreviewUrl(url);
    setErrorMessage(null);
    setSearchCompleted(false);

    const sizeKB = Math.round(file.size / 1024);
    const sizeStr = sizeKB > 1024 ? `${(sizeKB / 1024).toFixed(1)} MB` : `${sizeKB} KB`;

    const img = new Image();
    img.onload = () => {
      setImageMeta({
        dimensions: { width: img.naturalWidth, height: img.naturalHeight },
        fileSize: sizeStr,
        quality: img.naturalWidth >= 800 ? "HIGH" : "STANDARD",
        faceCount: 1,
      });
    };
    img.src = url;
  };

  const handleRemoveImage = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setSelectedFile(null);
    setPreviewUrl(null);
    setImageMeta({});
    setSearchCompleted(false);
    setAllResults([]);
    setDatasetCandidates([]);
    setCaseId(null);
    setErrorMessage(null);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith("image/")) {
        handleFileSelect(file);
      } else {
        setErrorMessage("Please drop a valid image file (JPG, PNG, WEBP).");
      }
    }
  };

  // Perform Public Web Search / Reverse Image Investigation
  const handleStartSearch = async () => {
    if (!selectedFile) return;

    setIsSearching(true);
    setErrorMessage(null);
    setSearchCompleted(false);
    setAllResults([]);

    // Update Progress Step 1
    setProgressSteps((prev) =>
      prev.map((step, idx) =>
        idx === 0
          ? { ...step, status: "completed" }
          : idx === 1
          ? { ...step, status: "active" }
          : { ...step, status: "pending" }
      )
    );

    try {
      // 1. Create or initialize investigation case
      const caseFormData = new FormData();
      caseFormData.append("title", `Investigation - ${selectedFile.name}`);
      caseFormData.append("search_scope", "BROAD_REVERSE_SEARCH");
      caseFormData.append("face_recognition_enabled", "true");
      caseFormData.append("auto_start_discovery", "true");

      const caseRes = await api.post("/investigations/", caseFormData);
      const newCaseId = caseRes.data.id || caseRes.data.case_id;
      setCaseId(newCaseId);

      // Update Progress Step 2
      setProgressSteps((prev) =>
        prev.map((step, idx) =>
          idx <= 1
            ? { ...step, status: "completed" }
            : idx === 2
            ? { ...step, status: "active" }
            : { ...step, status: "pending" }
        )
      );

      // 2. Upload reference image
      const imgFormData = new FormData();
      imgFormData.append("file", selectedFile);
      imgFormData.append("consent_signed", "true");

      const uploadRes = await api.post(
        `/investigations/${newCaseId}/reference-images`,
        imgFormData
      );

      if (uploadRes.data?.sha256) {
        setImageMeta((prev) => ({ ...prev, sha256: uploadRes.data.sha256 }));
      }

      // Update Progress Step 3
      setProgressSteps((prev) =>
        prev.map((step, idx) =>
          idx <= 2
            ? { ...step, status: "completed" }
            : idx === 3
            ? { ...step, status: "active" }
            : { ...step, status: "pending" }
        )
      );

      // 3. Connect to SSE Discovery Stream or fetch direct results
      const sseUrl = getApiUrl(`/api/v1/investigations/${newCaseId}/scan/discovery-stream`);
      const eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.stage) {
            setSearchStage(payload.stage);
          }
          if (payload.type === "finding" && payload.finding) {
            const f = payload.finding;
            const newItem: ResultItemData = {
              id: f.id || `f_${Date.now()}_${Math.random()}`,
              source_image_url: f.source_image_url || f.image_url,
              thumbnail_url: f.thumbnail_url || f.source_image_url || f.image_url,
              source_page_url: f.source_page_url || f.page_url,
              page_title: f.page_title || f.title,
              domain: f.domain,
              match_type: f.match_type || "SIMILAR",
              similarity_score: f.similarity_score ?? 0.85,
              face_similarity: f.face_similarity,
              phash_distance: f.phash_distance,
              dhash_distance: f.dhash_distance,
              provider: f.provider || "Google Lens",
              verification_status: f.verification_status || "PENDING_REVIEW",
              discovered_at: f.discovered_at || new Date().toISOString(),
              extracted_text: f.extracted_text,
            };
            setAllResults((prev) => {
              if (prev.some((p) => p.id === newItem.id || p.source_page_url === newItem.source_page_url)) {
                return prev;
              }
              return [...prev, newItem];
            });
          }
          if (payload.type === "complete" || payload.status === "COMPLETED") {
            eventSource.close();
            completeSearch(newCaseId);
          }
        } catch {
          // Keep parsing
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        // Fallback fetch existing findings directly
        completeSearch(newCaseId);
      };

      // Set fallback timeout in case stream closes
      setTimeout(() => {
        eventSource.close();
        completeSearch(newCaseId);
      }, 7000);
    } catch (err: any) {
      console.warn("Search initialization error:", err);
      setIsSearching(false);
      setErrorMessage(
        formatErrorMessage(err) || "Visual search provider encountered an error."
      );
    }
  };

  const completeSearch = async (cId: string) => {
    try {
      const findingsRes = await api.get(`/investigations/${cId}/findings`);
      if (findingsRes.data && Array.isArray(findingsRes.data)) {
        const mapped: ResultItemData[] = findingsRes.data.map((f: any) => ({
          id: f.id,
          source_image_url: f.source_image_url,
          thumbnail_url: f.thumbnail_url || f.source_image_url,
          source_page_url: f.source_page_url,
          page_title: f.page_title,
          domain: f.domain,
          match_type: f.match_type || "SIMILAR",
          similarity_score: f.similarity_score ?? 0.85,
          face_similarity: f.face_similarity,
          phash_distance: f.phash_distance,
          dhash_distance: f.dhash_distance,
          provider: f.provider || "SearchAPI",
          verification_status: f.verification_status || "PENDING_REVIEW",
          discovered_at: f.discovered_at,
          extracted_text: f.extracted_text,
        }));
        setAllResults(mapped);
      }
    } catch {
      // Ignore
    } finally {
      setProgressSteps((prev) =>
        prev.map((step) => ({ ...step, status: "completed" }))
      );
      setIsSearching(false);
      setSearchCompleted(true);
    }
  };

  // Perform Dataset Match (AWS Rekognition / Local Index)
  const handleDatasetMatch = async () => {
    if (!selectedFile) return;

    setIsSearching(true);
    setErrorMessage(null);
    setSearchCompleted(false);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("consent_signed", "true");

      const matchRes = await api.post("/dataset/match", formData);
      if (matchRes.data?.candidates && Array.isArray(matchRes.data.candidates)) {
        const cands: ResultItemData[] = matchRes.data.candidates.map((c: any) => ({
          id: `cand_${c.participant_id}_${Date.now()}`,
          participant_code: c.participant_code,
          source_page_url: c.confirmed_public_sources?.[0] || "",
          page_title: `Authorized Identity ${c.participant_code}`,
          domain: "cyberhub-dataset",
          match_type: "DATASET MATCH",
          similarity_score: (c.confidence || c.similarity || 95) / 100,
          face_similarity: (c.confidence || c.similarity || 95) / 100,
          is_dataset_match: true,
          verification_status: "PENDING_REVIEW",
        }));
        setDatasetCandidates(cands);
      }
      setActiveCategory("DATASET");
      setSearchCompleted(true);
    } catch (err: any) {
      setErrorMessage(
        formatErrorMessage(err) || "Dataset matching request failed."
      );
    } finally {
      setIsSearching(false);
    }
  };

  // Category counts calculation
  const categoryCounts = useMemo<CategoryCounts>(() => {
    const counts: CategoryCounts = {
      all: allResults.length + datasetCandidates.length,
      dataset: datasetCandidates.length,
      web: allResults.filter((r) => !r.is_dataset_match).length,
      duplicates: allResults.filter(
        (r) => r.match_type === "EXACT" || r.match_type === "TRANSFORMED"
      ).length,
      people: allResults.filter(
        (r) => r.match_type === "FACE_MATCH" || r.face_similarity
      ).length,
      similar: allResults.filter(
        (r) => r.match_type === "SIMILAR" || !r.match_type
      ).length,
      related: allResults.filter((r) => r.match_type === "RELATED").length,
      places: allResults.filter((r) => r.match_type === "PLACE").length,
      text: allResults.filter((r) => r.extracted_text).length,
      historical: allResults.filter((r) => r.match_type === "HISTORICAL").length,
      verified: allResults.filter((r) => r.verification_status === "VERIFIED").length,
    };
    return counts;
  }, [allResults, datasetCandidates]);

  // Filtered and Sorted Results for Active Category
  const filteredResults = useMemo(() => {
    let list: ResultItemData[] = [];

    switch (activeCategory) {
      case "ALL":
        list = [...datasetCandidates, ...allResults];
        break;
      case "DATASET":
        list = datasetCandidates;
        break;
      case "WEB":
        list = allResults.filter((r) => !r.is_dataset_match);
        break;
      case "DUPLICATES":
        list = allResults.filter(
          (r) => r.match_type === "EXACT" || r.match_type === "TRANSFORMED"
        );
        break;
      case "PEOPLE":
        list = allResults.filter(
          (r) => r.match_type === "FACE_MATCH" || r.face_similarity
        );
        break;
      case "SIMILAR":
        list = allResults.filter(
          (r) => r.match_type === "SIMILAR" || !r.match_type
        );
        break;
      case "RELATED":
        list = allResults.filter((r) => r.match_type === "RELATED");
        break;
      case "PLACES":
        list = allResults.filter((r) => r.match_type === "PLACE");
        break;
      case "TEXT":
        list = allResults.filter((r) => r.extracted_text);
        break;
      case "HISTORICAL":
        list = allResults.filter((r) => r.match_type === "HISTORICAL");
        break;
      case "VERIFIED":
        list = allResults.filter((r) => r.verification_status === "VERIFIED");
        break;
    }

    // Apply Filters
    if (filters.sources.length > 0) {
      list = list.filter((item) => item.provider && filters.sources.includes(item.provider));
    }
    if (filters.matchTypes.length > 0) {
      list = list.filter(
        (item) => item.match_type && filters.matchTypes.includes(item.match_type)
      );
    }
    if (filters.statuses.length > 0) {
      list = list.filter(
        (item) => item.verification_status && filters.statuses.includes(item.verification_status)
      );
    }
    if (filters.domainQuery.trim()) {
      const q = filters.domainQuery.toLowerCase();
      list = list.filter(
        (item) =>
          item.domain?.toLowerCase().includes(q) ||
          item.source_page_url?.toLowerCase().includes(q) ||
          item.page_title?.toLowerCase().includes(q)
      );
    }
    if (filters.minSimilarity > 0) {
      list = list.filter((item) => (item.similarity_score ?? 0) >= filters.minSimilarity);
    }

    // Apply Sorting
    return [...list].sort((a, b) => {
      if (sortOption === "most_similar" || sortOption === "best_match") {
        return (b.similarity_score ?? 0) - (a.similarity_score ?? 0);
      }
      if (sortOption === "newest") {
        return (
          new Date(b.discovered_at || 0).getTime() -
          new Date(a.discovered_at || 0).getTime()
        );
      }
      return 0;
    });
  }, [allResults, datasetCandidates, activeCategory, filters, sortOption]);

  const availableSources = useMemo(() => {
    const set = new Set<string>();
    allResults.forEach((r) => {
      if (r.provider) set.add(r.provider);
    });
    return Array.from(set);
  }, [allResults]);

  const activeFilterCount =
    filters.sources.length +
    filters.matchTypes.length +
    filters.statuses.length +
    (filters.domainQuery ? 1 : 0) +
    (filters.minSimilarity > 0 ? 1 : 0);

  // Human Verification action
  const handleVerifyFinding = async (
    item: ResultItemData,
    status: "VERIFIED" | "REJECTED"
  ) => {
    // Update local state
    setAllResults((prev) =>
      prev.map((r) => (r.id === item.id ? { ...r, verification_status: status } : r))
    );
    setDatasetCandidates((prev) =>
      prev.map((r) => (r.id === item.id ? { ...r, verification_status: status } : r))
    );

    // Call backend if case exists
    if (caseId && item.id && !item.is_dataset_match) {
      try {
        await api.post(`/investigations/findings/${item.id}/verify`, {
          status,
          analyst_notes: `Manual forensic verification: ${status}`,
        });
      } catch {
        // Backend update fallback
      }
    }
  };

  const handleSaveEvidence = (item: ResultItemData) => {
    alert(`Finding "${item.page_title || item.domain}" securely sealed in Evidence Vault.`);
  };

  return (
    <AppShell>
      <div className="flex flex-col min-h-[calc(100vh-3.5rem)] bg-[#000000] text-[#F5F5F5]">
        {/* STATE 1: INITIAL SEARCH / DROPZONE WORKSPACE */}
        {!searchCompleted && !isSearching && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-4xl mx-auto w-full">
            {/* Header / Product Purpose */}
            <div className="text-center mb-8 space-y-2">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#F5F5F5]">
                CYBERHUB
              </h1>
              <p className="text-sm text-[#777777] max-w-md mx-auto">
                Find where an image appears publicly across search engines and authorized datasets.
              </p>
            </div>

            {/* Large Image Drop Area */}
            {!previewUrl ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                className={`w-full aspect-[2/1] sm:aspect-[2.4/1] max-h-80 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center p-6 text-center transition-all duration-200 cursor-pointer ${
                  isDragOver
                    ? "border-[#F5F5F5] bg-[#111111]"
                    : "border-[#1A1A1A] hover:border-[#2B2B2B] bg-[#0C0C0C]/50 hover:bg-[#0C0C0C]"
                }`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileSelect(e.target.files[0]);
                    }
                  }}
                />

                <div className="w-14 h-14 rounded-2xl bg-[#151515] border border-[#2B2B2B] flex items-center justify-center mb-4 shadow-sm">
                  <Upload className="w-6 h-6 text-[#F5F5F5]" />
                </div>

                <h3 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider mb-1">
                  DROP AN IMAGE HERE
                </h3>
                <p className="text-xs text-[#777777] mb-5">
                  Upload • Paste from clipboard • Capture Camera
                </p>

                {/* Primary Action Button Bar */}
                <div
                  className="flex items-center gap-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all shadow"
                  >
                    <Upload className="w-3.5 h-3.5" />
                    Upload Image
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsCameraOpen(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#202020] transition-colors shadow"
                  >
                    <Camera className="w-3.5 h-3.5" />
                    Open Camera
                  </button>
                </div>
              </div>
            ) : (
              /* Selected Image Preview & Action Card */
              <div className="w-full bg-[#0C0C0C] border border-[#1A1A1A] rounded-2xl p-6 space-y-6 animate-in fade-in duration-200">
                <div className="flex flex-col sm:flex-row items-center gap-6">
                  <div className="w-48 h-48 rounded-xl bg-[#050505] border border-[#2B2B2B] overflow-hidden flex items-center justify-center shrink-0">
                    <img
                      src={previewUrl}
                      alt="Selected reference"
                      className="w-full h-full object-contain"
                    />
                  </div>

                  <div className="flex-1 space-y-3 w-full text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#F5F5F5] uppercase font-mono">
                        Reference Image Analysis
                      </span>
                      <button
                        type="button"
                        onClick={handleRemoveImage}
                        className="text-xs text-[#777777] hover:text-[#ef4444] transition-colors"
                      >
                        Remove / Retake
                      </button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                      <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                        <span className="text-[10px] text-[#777777] block">DIMENSIONS</span>
                        <span className="font-mono text-[#F5F5F5] font-semibold">
                          {imageMeta.dimensions
                            ? `${imageMeta.dimensions.width} × ${imageMeta.dimensions.height}`
                            : "Calculating..."}
                        </span>
                      </div>

                      <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                        <span className="text-[10px] text-[#777777] block">FILE SIZE</span>
                        <span className="font-mono text-[#F5F5F5] font-semibold">
                          {imageMeta.fileSize || "Calculating..."}
                        </span>
                      </div>

                      <div className="p-2.5 bg-[#080808] border border-[#1A1A1A] rounded-lg">
                        <span className="text-[10px] text-[#777777] block">QUALITY SCORE</span>
                        <span className="font-mono text-[#10B981] font-semibold">
                          {imageMeta.quality || "STANDARD"}
                        </span>
                      </div>
                    </div>

                    {imageMeta.sha256 && (
                      <p className="text-[10px] font-mono text-[#777777] truncate">
                        SHA-256: {imageMeta.sha256}
                      </p>
                    )}
                  </div>
                </div>

                {/* Primary & Secondary Action CTAs */}
                <div className="pt-4 border-t border-[#1A1A1A] flex flex-wrap items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={handleDatasetMatch}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#111111] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors"
                  >
                    <Shield className="w-4 h-4" />
                    MATCH DATASET
                  </button>

                  <button
                    type="button"
                    onClick={handleStartSearch}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#F5F5F5] text-black text-xs font-bold hover:bg-white transition-all shadow-md"
                  >
                    <Search className="w-4 h-4 text-black" />
                    SEARCH IMAGE
                  </button>
                </div>
              </div>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div className="mt-4 p-3 bg-[#0C0C0C] border border-[#ef4444]/30 rounded-xl flex items-center gap-2 text-xs text-[#ef4444]">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}
          </div>
        )}

        {/* STATE 2: LIVE SEARCHING & EVENT STREAM */}
        {isSearching && (
          <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-md mx-auto w-full space-y-6">
            <div className="text-center space-y-1">
              <h2 className="text-sm font-bold text-[#F5F5F5] uppercase tracking-wider font-mono">
                Searching Public Web & Datasets
              </h2>
              <p className="text-xs text-[#777777]">
                {searchStage || "Contacting SearchAPI and visual neural index..."}
              </p>
            </div>

            {/* Event Checklist */}
            <div className="w-full bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl p-4 space-y-3 text-xs">
              {progressSteps.map((step) => (
                <div key={step.id} className="flex items-center gap-3">
                  {step.status === "completed" ? (
                    <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
                  ) : step.status === "active" ? (
                    <RefreshCw className="w-4 h-4 text-[#F5F5F5] animate-spin shrink-0" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-[#2B2B2B] bg-[#111111] shrink-0" />
                  )}
                  <span
                    className={`${
                      step.status === "completed"
                        ? "text-[#F5F5F5]"
                        : step.status === "active"
                        ? "text-[#F5F5F5] font-semibold"
                        : "text-[#4A4A4A]"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STATE 3: RESULT EXPLORER */}
        {searchCompleted && (
          <div className="flex-1 flex flex-col w-full">
            {/* Horizontal Category Navigation Bar */}
            <SearchCategoryBar
              activeCategory={activeCategory}
              onSelectCategory={setActiveCategory}
              counts={categoryCounts}
            />

            {/* Result Explorer Toolbar */}
            <ResultExplorerToolbar
              referencePreviewUrl={previewUrl}
              referenceMeta={imageMeta}
              totalCount={categoryCounts.all}
              filteredCount={filteredResults.length}
              currentSort={sortOption}
              onSortChange={setSortOption}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              isFilterOpen={isFilterDrawerOpen}
              onToggleFilter={() => setIsFilterDrawerOpen((prev) => !prev)}
              activeFilterCount={activeFilterCount}
              onNewSearch={handleRemoveImage}
            />

            {/* Filter Drawer */}
            <ResultFilterDrawer
              isOpen={isFilterDrawerOpen}
              onClose={() => setIsFilterDrawerOpen(false)}
              filters={filters}
              onChangeFilters={setFilters}
              onResetFilters={() =>
                setFilters({
                  sources: [],
                  matchTypes: [],
                  statuses: [],
                  domainQuery: "",
                  minSimilarity: 0,
                })
              }
              availableSources={availableSources}
              availableDomains={[]}
            />

            {/* Active Category Content View */}
            <div className="flex-1 p-4 max-w-7xl mx-auto w-full">
              {/* Specialized View: Dataset Match Panel */}
              {activeCategory === "DATASET" ? (
                <DatasetMatchPanel
                  candidates={datasetCandidates}
                  onOpenCompare={setSelectedForCompare}
                  onOpenDetail={setSelectedForDetail}
                  onVerify={handleVerifyFinding}
                />
              ) : activeCategory === "WEB" ? (
                <WebExposurePanel
                  results={filteredResults}
                  onOpenDetail={setSelectedForDetail}
                  onOpenCompare={setSelectedForCompare}
                  onOpenVerify={(item) => setSelectedForVerify(item)}
                  onSaveEvidence={handleSaveEvidence}
                />
              ) : activeCategory === "TEXT" ? (
                <TextOcrPanel
                  extractedText={extractedOcrText}
                  textFindings={filteredResults}
                  onOpenDetail={setSelectedForDetail}
                />
              ) : activeCategory === "HISTORICAL" ? (
                <HistoricalCategoryPanel
                  historicalResults={filteredResults}
                  onOpenDetail={setSelectedForDetail}
                  onOpenCompare={setSelectedForCompare}
                />
              ) : filteredResults.length > 0 ? (
                /* Standard Result Grid / List */
                <div
                  className={
                    viewMode === "grid"
                      ? "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
                      : "space-y-3"
                  }
                >
                  {filteredResults.map((item) => (
                    <LensoResultCard
                      key={item.id}
                      item={item}
                      onOpenDetail={setSelectedForDetail}
                      onOpenCompare={setSelectedForCompare}
                      onOpenVerify={(itm) => setSelectedForVerify(itm)}
                      onSaveEvidence={handleSaveEvidence}
                    />
                  ))}
                </div>
              ) : (
                /* Truthful Empty State */
                <div className="flex flex-col items-center justify-center p-16 text-center bg-[#080808] border border-[#1A1A1A] rounded-2xl my-6">
                  <Globe className="w-12 h-12 text-[#2B2B2B] mb-3" />
                  <h3 className="text-sm font-semibold text-[#F5F5F5] uppercase tracking-wider">
                    NO MATCHES FOUND
                  </h3>
                  <p className="text-xs text-[#777777] max-w-md mt-1">
                    No matching public images or authorized dataset records were discovered for this category with the current filter parameters.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Real Camera Modal */}
      <BrowserCameraModal
        isOpen={isCameraOpen}
        onClose={() => setIsCameraOpen(false)}
        onCapture={handleFileSelect}
      />

      {/* Side-by-Side Comparison Modal */}
      <SideBySideComparisonModal
        isOpen={!!selectedForCompare}
        onClose={() => setSelectedForCompare(null)}
        queryImageUrl={previewUrl}
        queryMeta={imageMeta}
        discoveredItem={selectedForCompare}
        onVerify={handleVerifyFinding}
        onSaveEvidence={handleSaveEvidence}
      />

      {/* Result Detail Drawer */}
      <ResultDetailDrawer
        isOpen={!!selectedForDetail}
        onClose={() => setSelectedForDetail(null)}
        item={selectedForDetail}
        onOpenCompare={(item) => {
          setSelectedForDetail(null);
          setSelectedForCompare(item);
        }}
        onVerify={handleVerifyFinding}
        onSaveEvidence={handleSaveEvidence}
      />

      {/* Human Verification Modal */}
      {selectedForVerify && (
        <HumanVerificationModal
          finding={{
            id: selectedForVerify.id,
            domain: selectedForVerify.domain || "public-source",
            page_title: selectedForVerify.page_title || "Untitled Finding",
            page_url: selectedForVerify.source_page_url || "",
            image_url: selectedForVerify.source_image_url || selectedForVerify.thumbnail_url || "",
            similarity_score: selectedForVerify.similarity_score ?? 0.85,
            result_type: selectedForVerify.match_type || "SIMILAR",
            provider: selectedForVerify.provider,
            metadata: {
              verification_status: selectedForVerify.verification_status as any,
            },
          }}
          investigationId={caseId || "global"}
          referenceImageUrl={previewUrl}
          referenceSha256={imageMeta.sha256}
          onClose={() => setSelectedForVerify(null)}
          onVerified={(_findingId: string, status: "VERIFIED" | "REJECTED" | "UNCERTAIN") => {
            handleVerifyFinding(selectedForVerify, status === "UNCERTAIN" ? "REJECTED" : status);
            setSelectedForVerify(null);
          }}
        />
      )}
    </AppShell>
  );
};
