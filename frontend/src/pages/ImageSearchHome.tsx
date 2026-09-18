import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  Upload,
  Camera,
  Search,
  RefreshCw,
  X,
  AlertCircle,
  Layers,
  Globe,
  User,
  Copy,
  FolderSync,
} from "lucide-react";
import { SearchHeader } from "../components/SearchHeader";
import { CategoryTabs, CategoryKey } from "../components/CategoryTabs";
import { ReferencePanel } from "../components/ReferencePanel";
import { ResultCard, SearchResultItem } from "../components/ResultCard";
import { SortModal, SortChoice } from "../components/SortModal";
import { FilterModal, FilterOptions } from "../components/FilterModal";
import { CameraModal } from "../components/CameraModal";
import { CompareModal } from "../components/CompareModal";
import { ResultDetailModal } from "../components/ResultDetailModal";
import { ResearchModeModal } from "../components/ResearchModeModal";
import { AlertModal } from "../components/AlertModal";
import { api, getApiUrl } from "../services/api";
import { formatErrorMessage } from "../utils/errorUtils";

export const ImageSearchHome: React.FC = () => {
  // Search input state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [textQuery, setTextQuery] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Search & Results state
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchStage, setSearchStage] = useState<string>("");
  const [searchCompleted, setSearchCompleted] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [datasetResults, setDatasetResults] = useState<SearchResultItem[]>([]);

  // Navigation & Category state
  const [activeCategory, setActiveCategory] = useState<CategoryKey>("all");
  const [sortChoice, setSortChoice] = useState<SortChoice>("default");
  const [filters, setFilters] = useState<FilterOptions>({
    websiteQuery: "",
    keywordQuery: "",
  });

  // Modals state
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isSortModalOpen, setIsSortModalOpen] = useState(false);
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);
  const [isResearchModalOpen, setIsResearchModalOpen] = useState(false);
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [selectedDetailResult, setSelectedDetailResult] = useState<SearchResultItem | null>(null);
  const [selectedCompareResult, setSelectedCompareResult] = useState<SearchResultItem | null>(null);

  // Global Clipboard paste listener
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (isSearching) return;
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
  }, [isSearching]);

  // Handle file selection
  const handleFileSelect = (file: File) => {
    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please select a valid image file (JPEG, PNG, WEBP).");
      return;
    }
    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    setErrorMessage(null);
    // Trigger real reverse search
    executeSearch(file, objectUrl);
  };

  // Trigger search with real backend integration
  const executeSearch = async (imageFile: File, objUrl?: string) => {
    setIsSearching(true);
    setSearchStage("Uploading and analyzing visual query...");
    setErrorMessage(null);
    setResults([]);
    setDatasetResults([]);
    setActiveCategory("all");

    try {
      // 1. Create Investigation Case
      const caseRes = await api.post("/investigations/", {
        title: `Visual Search - ${new Date().toLocaleTimeString()}`,
        description: "AI Reverse Image Investigation",
        classification: "UNCLASSIFIED",
      });
      const newCaseId = caseRes.data?.id || caseRes.data?.investigation_id;
      setCaseId(newCaseId);

      // 2. Upload Reference Image
      setSearchStage("Extracting visual features and biometric embeddings...");
      const formData = new FormData();
      formData.append("file", imageFile);
      formData.append("label", "Query Reference");

      await api.post(`/investigations/${newCaseId}/reference-images`, formData);

      // 3. Parallel calls: Controlled Dataset Match + Web Discovery
      setSearchStage("Querying public web & biometric dataset index...");

      // Parallel: Dataset Match
      const datasetPromise = api
        .post(`/investigations/${newCaseId}/dataset-match`)
        .catch(() => api.post("/dataset/match", formData))
        .then((res) => {
          if (res?.data) {
            const candidates = res.data.candidates || (res.data.match ? [res.data.match] : []);
            const datasetItems: SearchResultItem[] = candidates.map((c: any, i: number) => ({
              id: `dataset-${i}-${c.participant_id || c.id || "match"}`,
              page_title: c.name || c.participant_name || `Dataset Participant: ${c.participant_id || "Candidate"}`,
              domain: "cyberhub.internal",
              source_page_url: c.confirmed_urls?.[0] || "#",
              thumbnail_url: c.thumbnail_url || c.preview_url || objUrl || "",
              source_image_url: c.preview_url || objUrl || "",
              match_type: "DATASET MATCH",
              similarity_score: c.similarity || c.confidence || 0.95,
              face_similarity: c.face_similarity || c.confidence,
              phash_distance: c.phash,
              dhash_distance: c.dhash,
              is_dataset_match: true,
              participant_code: c.participant_id || "Candidate",
            }));
            setDatasetResults(datasetItems);
          }
        })
        .catch((err) => {
          console.warn("Dataset match non-fatal error:", err);
        });

      // Stream / Discovery scan
      const streamUrl = getApiUrl(`/api/v1/investigations/${newCaseId}/scan/discovery-stream`);
      const eventSource = new EventSource(streamUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.stage) setSearchStage(data.stage);
          if (data.finding || data.result) {
            const f = data.finding || data.result;
            const newItem: SearchResultItem = {
              id: f.id || `res-${Date.now()}-${Math.random()}`,
              page_title: f.title || f.context || "Visual Match",
              domain: f.domain || "web",
              source_page_url: f.url || f.link || "#",
              thumbnail_url: f.thumbnail_url || f.image_url || f.url || "",
              source_image_url: f.image_url || f.url || "",
              match_type: (f.match_type || f.category || "SIMILAR").toUpperCase(),
              similarity_score: f.similarity_score || f.confidence || 0.88,
              face_similarity: f.face_similarity,
              phash_distance: f.phash,
              dhash_distance: f.dhash,
            };
            setResults((prev) => [...prev, newItem]);
          }
          if (data.status === "completed" || data.stage === "completed") {
            eventSource.close();
            setIsSearching(false);
            setSearchCompleted(true);
          }
        } catch (e) {
          // ignore stream parse errors
        }
      };

      eventSource.onerror = async () => {
        eventSource.close();
        // Fallback: poll findings endpoint directly
        try {
          const findingsRes = await api.get(`/investigations/${newCaseId}/findings`);
          const items: SearchResultItem[] = (findingsRes.data || []).map((f: any) => ({
            id: f.id,
            page_title: f.title || f.context || "Discovered Match",
            domain: f.domain || "web",
            source_page_url: f.url || "#",
            thumbnail_url: f.thumbnail_url || f.image_url || "",
            source_image_url: f.image_url || "",
            match_type: (f.match_type || f.category || "SIMILAR").toUpperCase(),
            similarity_score: f.similarity_score || 0.85,
            face_similarity: f.face_similarity,
            phash_distance: f.phash,
            dhash_distance: f.dhash,
          }));
          setResults(items);
        } catch (err) {
          console.warn("Direct findings fetch:", err);
        }
        setIsSearching(false);
        setSearchCompleted(true);
      };

      // Safety timeout for SSE stream
      setTimeout(() => {
        if (eventSource.readyState !== EventSource.CLOSED) {
          eventSource.close();
          setIsSearching(false);
          setSearchCompleted(true);
        }
      }, 8000);

      await datasetPromise;
    } catch (err: any) {
      console.error("Search execution failed:", err);
      setErrorMessage(formatErrorMessage(err) || "Visual search failed. Please try again.");
      setIsSearching(false);
      setSearchCompleted(true);
    }
  };

  // Reset to Home Search
  const handleNewSearch = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setTextQuery("");
    setResults([]);
    setDatasetResults([]);
    setSearchCompleted(false);
    setIsSearching(false);
    setErrorMessage(null);
    setCaseId(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Filter and Sort results
  const displayedResults = useMemo(() => {
    let combined = [...results, ...datasetResults];

    // Filter by Category
    if (activeCategory !== "all") {
      combined = combined.filter((r) => {
        const cat = (r.match_type || "").toLowerCase();
        if (activeCategory === "people") return cat.includes("people") || cat.includes("face") || (r.face_similarity && r.face_similarity > 0.7);
        if (activeCategory === "duplicates") return cat.includes("duplicate") || (r.similarity_score && r.similarity_score > 0.95);
        if (activeCategory === "dataset") return r.is_dataset_match || r.domain === "cyberhub.internal";
        if (activeCategory === "related") return cat.includes("related");
        if (activeCategory === "similar") return cat.includes("similar") || !cat;
        return true;
      });
    }

    // Filter by Website Query
    if (filters.websiteQuery.trim()) {
      const query = filters.websiteQuery.toLowerCase().trim();
      combined = combined.filter(
        (r) => (r.domain && r.domain.toLowerCase().includes(query)) || (r.source_page_url && r.source_page_url.toLowerCase().includes(query))
      );
    }

    // Filter by Keyword Query
    if (filters.keywordQuery.trim()) {
      const query = filters.keywordQuery.toLowerCase().trim();
      combined = combined.filter(
        (r) =>
          (r.page_title && r.page_title.toLowerCase().includes(query)) ||
          (r.match_type && r.match_type.toLowerCase().includes(query))
      );
    }

    // Sort
    if (sortChoice === "best_to_worst") {
      combined.sort((a, b) => (b.similarity_score || 0) - (a.similarity_score || 0));
    } else if (sortChoice === "worst_to_best") {
      combined.sort((a, b) => (a.similarity_score || 0) - (b.similarity_score || 0));
    } else if (sortChoice === "random") {
      combined.sort(() => Math.random() - 0.5);
    }

    return combined;
  }, [results, datasetResults, activeCategory, filters, sortChoice]);

  // Counts for category tabs
  const categoryCounts: Record<CategoryKey, number> = useMemo(() => {
    const all = results.length + datasetResults.length;
    const people = results.filter((r) => (r.match_type || "").toLowerCase().includes("people") || (r.face_similarity && r.face_similarity > 0.7)).length;
    const duplicates = results.filter((r) => (r.match_type || "").toLowerCase().includes("duplicate") || (r.similarity_score && r.similarity_score > 0.95)).length;
    const related = results.filter((r) => (r.match_type || "").toLowerCase().includes("related")).length;
    const similar = results.filter((r) => (r.match_type || "").toLowerCase().includes("similar") || !(r.match_type)).length;
    const dataset = datasetResults.length;
    return { all, people, duplicates, related, similar, dataset };
  }, [results, datasetResults]);

  const isHomeView = !previewUrl && !isSearching && !searchCompleted;

  return (
    <div className="min-h-screen bg-[#FAFAFA] text-slate-900 flex flex-col font-sans selection:bg-indigo-500/20 selection:text-indigo-900">
      {/* 1. Header (Navbar matching visual reference) */}
      <SearchHeader onNewSearch={handleNewSearch} />

      {/* 2. Main Container */}
      <main className="flex-1 max-w-[1520px] w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Error Alert if any */}
        {errorMessage && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-rose-800 text-sm">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="p-1 text-rose-500 hover:text-rose-700 hover:bg-rose-100 rounded-lg"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ============================================================ */}
        {/* VIEW 1: HOME SEARCH EXPERIENCE (Frame 020) */}
        {/* ============================================================ */}
        {isHomeView ? (
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-140px)] max-w-4xl mx-auto text-center px-4">
            {/* Hero Title */}
            <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-slate-900 tracking-tight mb-8">
              AI Reverse Image Search with CYBERHUB
            </h1>

            {/* Central Upload Dropzone Box */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  handleFileSelect(e.dataTransfer.files[0]);
                }
              }}
              className={`w-full max-w-2xl bg-white border-2 border-dashed rounded-3xl p-8 sm:p-12 shadow-sm transition-all duration-200 ${
                isDragOver
                  ? "border-indigo-500 bg-indigo-50/20 scale-[1.01]"
                  : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileSelect(e.target.files[0]);
                  }
                }}
              />

              <div className="flex flex-col items-center justify-center space-y-5">
                <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center shadow-inner">
                  <Upload className="w-7 h-7" />
                </div>

                <div className="space-y-1">
                  <h3 className="text-xl font-bold text-slate-800">
                    Drop, paste or upload an image
                  </h3>
                  <p className="text-sm text-slate-500">
                    Supports JPG, PNG, WEBP up to 25MB • Paste anytime with Ctrl+V
                  </p>
                </div>

                {/* Main Action Buttons */}
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl shadow-sm hover:shadow transition flex items-center gap-2 cursor-pointer"
                  >
                    <Upload className="w-4 h-4" /> Upload Image
                  </button>
                  <button
                    onClick={() => setIsCameraOpen(true)}
                    className="px-6 py-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-sm rounded-xl transition flex items-center gap-2 cursor-pointer"
                  >
                    <Camera className="w-4 h-4 text-slate-600" /> Camera
                  </button>
                </div>
              </div>
            </div>

            {/* Example Search Category Pills */}
            <div className="flex flex-wrap items-center justify-center gap-2.5 mt-8">
              <span className="text-xs font-semibold text-slate-500 mr-1 uppercase tracking-wider">
                Explore Categories:
              </span>
              {[
                { name: "people", icon: User, color: "text-rose-500 bg-rose-50 border-rose-200" },
                { name: "duplicates", icon: Copy, color: "text-blue-500 bg-blue-50 border-blue-200" },
                { name: "places", icon: Globe, color: "text-emerald-500 bg-emerald-50 border-emerald-200" },
                { name: "related", icon: Layers, color: "text-amber-500 bg-amber-50 border-amber-200" },
                { name: "by-dataset", icon: FolderSync, color: "text-purple-500 bg-purple-50 border-purple-200" },
              ].map((cat) => {
                const Icon = cat.icon;
                return (
                  <button
                    key={cat.name}
                    onClick={() => fileInputRef.current?.click()}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium border shadow-2xs hover:scale-105 transition-all cursor-pointer ${cat.color}`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{cat.name}</span>
                  </button>
                );
              })}
            </div>

            {/* Bottom Text Search Bar */}
            <div className="w-full max-w-xl mt-6">
              <div className="relative flex items-center">
                <Search className="w-4 h-4 text-slate-400 absolute left-4" />
                <input
                  type="text"
                  value={textQuery}
                  onChange={(e) => setTextQuery(e.target.value)}
                  placeholder="or type keyword / image URL to search..."
                  className="w-full pl-11 pr-24 py-3 bg-white border border-slate-200 rounded-full text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-2xs"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && textQuery.trim()) {
                      fileInputRef.current?.click();
                    }
                  }}
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute right-2 px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-full transition cursor-pointer"
                >
                  Search
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* ============================================================ */
          /* VIEW 2: SEARCH RESULTS PAGE (Frame 025/030/035) */
          /* ============================================================ */
          <div className="flex flex-col lg:flex-row gap-8 items-start">
            {/* Left Column: Sticky Reference Image Panel (w-80) */}
            <aside className="w-full lg:w-80 shrink-0 sticky top-20">
              <ReferencePanel
                previewUrl={previewUrl}
                onNewSearch={handleNewSearch}
                onRefresh={() => {
                  if (selectedFile) executeSearch(selectedFile, previewUrl || undefined);
                }}
                onOpenAlert={() => setIsAlertModalOpen(true)}
                onOpenResearchMode={() => setIsResearchModalOpen(true)}
              />
            </aside>

            {/* Right Column: Category Tabs, Toolbar, Results Explorer Grid */}
            <section className="flex-1 w-full min-w-0">
              {/* Category Tabs & Toolbar Header */}
              <div className="bg-white p-3 rounded-2xl border border-slate-200/80 shadow-2xs mb-6">
                <CategoryTabs
                  activeCategory={activeCategory}
                  onSelectCategory={setActiveCategory}
                  counts={categoryCounts}
                  onOpenSort={() => setIsSortModalOpen(true)}
                  onOpenFilter={() => setIsFilterModalOpen(true)}
                  onOpenResearchMode={() => setIsResearchModalOpen(true)}
                />
              </div>

              {/* Active Filter Chips (if any) */}
              {(filters.websiteQuery || filters.keywordQuery || sortChoice !== "default") && (
                <div className="flex flex-wrap items-center gap-2 mb-4 px-1">
                  <span className="text-xs font-medium text-slate-500">Active filters:</span>
                  {filters.websiteQuery && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                      Site: {filters.websiteQuery}
                      <button
                        onClick={() => setFilters((prev) => ({ ...prev, websiteQuery: "" }))}
                        className="hover:text-indigo-900"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {filters.keywordQuery && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                      Keyword: {filters.keywordQuery}
                      <button
                        onClick={() => setFilters((prev) => ({ ...prev, keywordQuery: "" }))}
                        className="hover:text-slate-900"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  {sortChoice !== "default" && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                      Sort: {sortChoice.replace(/_/g, " ")}
                      <button onClick={() => setSortChoice("default")} className="hover:text-amber-900">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  )}
                  <button
                    onClick={() => {
                      setFilters({ websiteQuery: "", keywordQuery: "" });
                      setSortChoice("default");
                    }}
                    className="text-xs text-indigo-600 hover:text-indigo-800 underline ml-2 cursor-pointer"
                  >
                    Clear all
                  </button>
                </div>
              )}

              {/* Searching Progress Indicator */}
              {isSearching && (
                <div className="p-8 mb-6 bg-white border border-indigo-100 rounded-2xl shadow-2xs flex flex-col items-center text-center space-y-4 animate-pulse">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                    <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Scanning Public Web & Biometric Vectors...
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">{searchStage}</p>
                  </div>
                </div>
              )}

              {/* Results Grid / Masonry */}
              {displayedResults.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-4">
                  {displayedResults.map((item) => (
                    <ResultCard
                      key={item.id}
                      item={item}
                      onInspect={setSelectedDetailResult}
                      onCompare={(res) => setSelectedCompareResult(res)}
                    />
                  ))}
                </div>
              ) : (
                !isSearching && (
                  <div className="p-16 bg-white border border-slate-200 rounded-3xl text-center flex flex-col items-center justify-center space-y-4">
                    <div className="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center">
                      <Search className="w-8 h-8" />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold text-slate-800">
                        No results found for this category
                      </h3>
                      <p className="text-sm text-slate-500 max-w-sm mt-1">
                        Try switching to "All", clearing active filters, or enabling Research Mode for deep archive discovery.
                      </p>
                    </div>
                    <div className="flex items-center gap-3 pt-2">
                      <button
                        onClick={() => {
                          setActiveCategory("all");
                          setFilters({ websiteQuery: "", keywordQuery: "" });
                        }}
                        className="px-4 py-2 bg-indigo-50 text-indigo-700 font-semibold text-xs rounded-xl hover:bg-indigo-100 transition cursor-pointer"
                      >
                        Reset Categories & Filters
                      </button>
                      <button
                        onClick={() => setIsResearchModalOpen(true)}
                        className="px-4 py-2 bg-indigo-600 text-white font-semibold text-xs rounded-xl hover:bg-indigo-700 transition cursor-pointer"
                      >
                        Launch Research Mode
                      </button>
                    </div>
                  </div>
                )
              )}
            </section>
          </div>
        )}
      </main>

      {/* ============================================================ */}
      {/* MODALS & DRAWERS */}
      {/* ============================================================ */}

      {/* Camera Modal */}
      <CameraModal
        isOpen={isCameraOpen}
        onClose={() => setIsCameraOpen(false)}
        onCapture={(file) => {
          setIsCameraOpen(false);
          handleFileSelect(file);
        }}
      />

      {/* Sort Modal */}
      <SortModal
        isOpen={isSortModalOpen}
        onClose={() => setIsSortModalOpen(false)}
        selectedSort={sortChoice}
        onSelectSort={setSortChoice}
      />

      {/* Filter Modal */}
      <FilterModal
        isOpen={isFilterModalOpen}
        onClose={() => setIsFilterModalOpen(false)}
        filters={filters}
        onApplyFilters={setFilters}
        onResetFilters={() => setFilters({ websiteQuery: "", keywordQuery: "" })}
      />

      {/* Result Detail Modal */}
      <ResultDetailModal
        isOpen={!!selectedDetailResult}
        onClose={() => setSelectedDetailResult(null)}
        item={selectedDetailResult}
        onCompare={(res) => {
          setSelectedDetailResult(null);
          setSelectedCompareResult(res);
        }}
      />

      {/* Side-by-Side Compare Modal */}
      <CompareModal
        isOpen={!!selectedCompareResult}
        onClose={() => setSelectedCompareResult(null)}
        referenceUrl={previewUrl}
        discoveredItem={selectedCompareResult}
      />

      {/* Research Mode Modal */}
      <ResearchModeModal
        isOpen={isResearchModalOpen}
        onClose={() => setIsResearchModalOpen(false)}
        onStartResearch={({ deepWeb, darkWeb, osintArchive }) => {
          if (caseId) {
            api
              .post(`/investigations/${caseId}/research-mode`, {
                deepWeb,
                darkWeb,
                osintArchive,
              })
              .catch((err) => console.warn("Research mode trigger:", err));
          }
        }}
      />

      {/* Alert Modal */}
      <AlertModal
        isOpen={isAlertModalOpen}
        onClose={() => setIsAlertModalOpen(false)}
        referenceImage={previewUrl || undefined}
        onSaveAlert={({ email, webhookUrl, notifyOnNewAppearance }) => {
          if (caseId) {
            api
              .post(`/investigations/${caseId}/alerts`, {
                email,
                webhookUrl,
                notifyOnNewAppearance,
              })
              .catch((err) => console.warn("Alert save:", err));
          }
        }}
      />
    </div>
  );
};
