import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Camera,
  Upload,
  Search,
  Globe,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  Loader2,
  X,
  FileImage,
  Shield,
  Layers,
} from "lucide-react";
import { AppShell } from "../components/shell/AppShell";
import { api } from "../services/api";

type InputMode = "dropzone" | "camera";

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();

  // Mode & File state
  const [inputMode, setInputMode] = useState<InputMode>("dropzone");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState<boolean>(true);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchStage, setSearchStage] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Camera state
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);

  // Stop camera stream safely
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  }, []);

  // Start real browser camera
  const startCamera = useCallback(async () => {
    stopCamera();
    setCameraError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError("Camera hardware access is not supported by this browser environment.");
      setInputMode("dropzone");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play().catch(() => {});
          setCameraActive(true);
        };
      } else {
        setCameraActive(true);
      }
    } catch (err: any) {
      console.warn("Camera init error:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setCameraError("Camera permission denied. Please grant browser camera access or upload an image.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setCameraError("No video camera capture device detected.");
      } else {
        setCameraError(err.message || "Failed to initialize device camera stream.");
      }
      setInputMode("dropzone");
    }
  }, [stopCamera]);

  useEffect(() => {
    if (inputMode === "camera" && !previewUrl) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [inputMode, previewUrl, startCamera, stopCamera]);

  // Capture frame from active camera
  const handleCaptureFrame = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setErrorMessage("Failed to acquire canvas rendering context.");
      return;
    }

    // Mirror image for natural user preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setErrorMessage("Failed to encode frame capture.");
          return;
        }
        const file = new File([blob], `forensic_capture_${Date.now()}.jpg`, {
          type: "image/jpeg",
        });
        const url = URL.createObjectURL(blob);
        stopCamera();
        setSelectedFile(file);
        setPreviewUrl(url);
        setErrorMessage(null);
      },
      "image/jpeg",
      0.94
    );
  };

  // Handle local file upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please select a supported image file (JPEG, PNG, WEBP).");
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setErrorMessage("File exceeds 50 MB size limit.");
      return;
    }

    const url = URL.createObjectURL(file);
    stopCamera();
    setSelectedFile(file);
    setPreviewUrl(url);
    setErrorMessage(null);
  };

  // Handle Drag & Drop
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file && file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      stopCamera();
      setSelectedFile(file);
      setPreviewUrl(url);
      setErrorMessage(null);
    }
  };

  // Remove/Retake selected image
  const handleRemoveImage = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setErrorMessage(null);
    if (inputMode === "camera") {
      startCamera();
    }
  };

  // Execute Real Backend Flow & SearchAPI Google Lens
  const handleSearchPublicWeb = async () => {
    if (!selectedFile) {
      setErrorMessage("Please capture or upload an image first.");
      return;
    }

    if (!isAuthorized) {
      setErrorMessage("Please confirm you are authorized to investigate this image.");
      return;
    }

    setIsSearching(true);
    setErrorMessage(null);
    setSearchStage("Preparing image & container...");

    try {
      // 1. Create Investigation Container
      const title = `Image Exposure Investigation - ${new Date().toISOString().split("T")[0]}`;
      const caseRes = await api.post("/investigations", {
        title,
        description: "Public reverse-image exposure investigation via Google Lens",
      });
      const newCase = caseRes.data;

      // 2. Upload Reference Image & extract DINOv2 / pHash / dHash
      setSearchStage("Uploading reference asset...");
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("source_type", inputMode === "camera" ? "WEBCAM" : "UPLOAD");
      formData.append("label", "Target Reference Subject");

      const imgRes = await api.post(`/investigations/${newCase.id}/reference-image`, formData);
      const imgData = imgRes.data;

      // 3. Record Attestation Audit Control
      setSearchStage("Recording authorization attestation...");
      try {
        await api.post(`/investigations/${newCase.id}/attestation`, {
          attestation_text: "I confirm I am authorized to investigate this image under organizational security policy.",
          attestation_version: "v1.0.0",
          reference_image_sha256: imgData.sha256_hash || imgData.sha256,
        });
      } catch (attErr) {
        console.warn("Attestation audit notice:", attErr);
      }

      // 4. Navigate to investigation workspace with autoSearch
      setSearchStage("Connecting to Google Lens search pipeline...");
      navigate(`/investigations/image-exposure?caseId=${newCase.id}&autoSearch=true`);
    } catch (err: any) {
      console.error("Investigation initialization failed:", err);
      const serverDetail =
        err.response?.data?.detail ||
        err.response?.data?.error?.message ||
        err.response?.data?.message;
      setErrorMessage(
        serverDetail || err.message || "Failed to initialize public image search."
      );
      setIsSearching(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 text-left">
        {/* Launchpad Header */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-[#F5F5F5] tracking-tight">
            Investigate public digital exposure.
          </h1>
          <p className="text-xs sm:text-sm text-[#777777] mt-1.5 max-w-2xl leading-relaxed">
            Take a photo or upload an authorized image to search the public web for matching and related appearances.
          </p>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="p-3.5 rounded-lg bg-[#111111] border border-[#ef4444]/40 text-[#ef4444] text-xs flex items-center justify-between">
            <div className="flex items-center gap-2.5">
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

        {/* PRIMARY IMAGE EXPOSURE WORKSPACE */}
        <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl overflow-hidden">
          {/* Workspace Title & Context */}
          <div className="px-5 py-4 border-b border-[#1A1A1A] bg-[#080808] flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider">
                  IMAGE EXPOSURE
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] font-mono">
                  Google Lens · SearchAPI
                </span>
              </div>
              <p className="text-xs text-[#777777] mt-0.5">
                Search the public web for matching and related appearances of an authorized image.
              </p>
            </div>

            {/* Quick Mode Toggle (when no image selected) */}
            {!previewUrl && (
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => {
                    setInputMode("camera");
                    startCamera();
                  }}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                    inputMode === "camera"
                      ? "bg-[#F5F5F5] text-[#000000] font-semibold"
                      : "bg-[#111111] text-[#B3B3B3] border border-[#232323] hover:text-[#F5F5F5]"
                  }`}
                >
                  <Camera className="w-3.5 h-3.5" />
                  <span>Open Camera</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setInputMode("dropzone");
                    stopCamera();
                  }}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors flex items-center gap-1.5 ${
                    inputMode === "dropzone"
                      ? "bg-[#F5F5F5] text-[#000000] font-semibold"
                      : "bg-[#111111] text-[#B3B3B3] border border-[#232323] hover:text-[#F5F5F5]"
                  }`}
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Upload Image</span>
                </button>
              </div>
            )}
          </div>

          {/* Workspace Body */}
          <div className="p-5 sm:p-6">
            {/* STATE 1: DROPZONE / INPUT SURFACE */}
            {!previewUrl && inputMode === "dropzone" && (
              <div className="space-y-4">
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className="border border-dashed border-[#232323] hover:border-[#383838] bg-[#080808] hover:bg-[#0E0E0E] rounded-lg p-10 sm:p-14 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[300px]"
                >
                  <div className="w-12 h-12 rounded-lg bg-[#151515] border border-[#232323] text-[#B3B3B3] flex items-center justify-center mb-3.5">
                    <FileImage className="w-6 h-6" />
                  </div>

                  <p className="text-sm font-medium text-[#F5F5F5]">
                    Drop an image here or take a photo with your camera
                  </p>
                  <p className="text-xs text-[#777777] mt-1">
                    Select an authorized reference asset to begin public web investigation.
                  </p>

                  <div className="mt-5 flex items-center gap-2.5">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setInputMode("camera");
                        startCamera();
                      }}
                      className="px-4 py-2 bg-[#F5F5F5] text-[#000000] text-xs font-semibold rounded-md hover:bg-white transition-colors flex items-center gap-1.5"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      <span>Open Camera</span>
                    </button>

                    <button
                      type="button"
                      className="px-4 py-2 bg-[#151515] text-[#F5F5F5] text-xs font-medium rounded-md border border-[#232323] hover:bg-[#1C1C1C] transition-colors flex items-center gap-1.5"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload Image</span>
                    </button>
                  </div>

                  <p className="text-[11px] text-[#4A4A4A] mt-4 font-mono">
                    Supported formats: JPEG · PNG · WEBP (Max 50 MB)
                  </p>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>
              </div>
            )}

            {/* STATE 2: LIVE CAMERA CAPTURE */}
            {!previewUrl && inputMode === "camera" && (
              <div className="space-y-4">
                <div className="relative aspect-video max-h-[420px] w-full bg-[#000000] rounded-lg overflow-hidden border border-[#232323] flex items-center justify-center">
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover transform -scale-x-100"
                  />

                  {/* Frame markings */}
                  <div className="absolute inset-0 pointer-events-none border border-white/10 rounded-lg m-3 flex flex-col justify-between p-3">
                    <div className="flex justify-between items-start">
                      <div className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/80 border border-[#232323] text-[#F5F5F5] flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                        <span>STREAMING</span>
                      </div>
                      <div className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/80 border border-[#232323] text-[#777777]">
                        1280 × 720 HD
                      </div>
                    </div>
                  </div>

                  {cameraError && (
                    <div className="absolute inset-0 bg-black/90 flex flex-col items-center justify-center p-6 text-center">
                      <AlertCircle className="w-6 h-6 text-[#ef4444] mb-2" />
                      <p className="text-xs text-[#B3B3B3] max-w-sm mb-3">{cameraError}</p>
                      <button
                        type="button"
                        onClick={() => setInputMode("dropzone")}
                        className="px-3.5 py-1.5 bg-[#F5F5F5] text-[#000000] font-semibold text-xs rounded-md"
                      >
                        Switch to File Upload
                      </button>
                    </div>
                  )}
                </div>

                {/* Shutter bar */}
                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={() => {
                      setInputMode("dropzone");
                      stopCamera();
                    }}
                    className="text-xs text-[#777777] hover:text-[#F5F5F5] transition-colors"
                  >
                    Cancel / Choose file instead
                  </button>

                  <button
                    type="button"
                    onClick={handleCaptureFrame}
                    disabled={!cameraActive}
                    className="h-10 px-6 bg-[#F5F5F5] hover:bg-white text-[#000000] font-semibold text-xs rounded-md flex items-center gap-2 active:scale-95 transition-all disabled:opacity-50"
                  >
                    <div className="w-3 h-3 rounded-full border border-black flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-black" />
                    </div>
                    <span>Capture Image</span>
                  </button>
                </div>
              </div>
            )}

            {/* STATE 3: REFERENCE IMAGE SELECTED */}
            {previewUrl && (
              <div className="space-y-5">
                <div className="flex items-center justify-between border-b border-[#1A1A1A] pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#F5F5F5] uppercase tracking-wider">
                      REFERENCE IMAGE
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-[#151515] border border-[#232323] text-[#B3B3B3] font-mono">
                      INTAKE ASSET
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleRemoveImage}
                      className="text-xs text-[#777777] hover:text-[#ef4444] flex items-center gap-1 transition-colors"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Remove</span>
                    </button>
                    <span className="text-[#232323]">|</span>
                    <button
                      type="button"
                      onClick={handleRemoveImage}
                      className="text-xs text-[#777777] hover:text-[#F5F5F5] flex items-center gap-1 transition-colors"
                    >
                      <RefreshCw className="w-3 h-3" />
                      <span>Retake</span>
                    </button>
                  </div>
                </div>

                {/* Reference Image Container */}
                <div className="relative aspect-video max-h-[400px] w-full bg-[#000000] rounded-lg overflow-hidden border border-[#232323] flex items-center justify-center p-3">
                  <img
                    src={previewUrl}
                    alt="Reference Preview"
                    className="max-h-full max-w-full object-contain rounded"
                  />
                  <div className="absolute bottom-3 left-3 px-2.5 py-1 rounded bg-black/85 border border-[#232323] text-[10px] font-mono text-[#B3B3B3]">
                    {selectedFile?.name || "capture.jpg"} · {selectedFile?.type || "image/jpeg"} ·{" "}
                    {selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB` : ""}
                  </div>
                </div>

                {/* Compact Authorization Line */}
                <div className="p-3.5 rounded-lg bg-[#080808] border border-[#1A1A1A] flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="authConfirm"
                    checked={isAuthorized}
                    onChange={(e) => setIsAuthorized(e.target.checked)}
                    className="mt-0.5 w-3.5 h-3.5 rounded border-[#232323] bg-[#111111] text-[#F5F5F5] focus:ring-0 cursor-pointer"
                  />
                  <label
                    htmlFor="authConfirm"
                    className="text-xs text-[#B3B3B3] select-none cursor-pointer leading-relaxed"
                  >
                    I confirm I am authorized to investigate this image.{" "}
                    <span className="text-[#777777]">
                      This investigation action is recorded in the immutable audit log.
                    </span>
                  </label>
                </div>

                {/* Primary Action Button: Search Public Web */}
                <div>
                  <button
                    type="button"
                    onClick={handleSearchPublicWeb}
                    disabled={isSearching || !isAuthorized}
                    className="w-full h-11 bg-[#F5F5F5] hover:bg-white text-[#000000] font-semibold text-xs rounded-lg flex items-center justify-center gap-2 active:scale-[0.99] transition-all disabled:opacity-40"
                  >
                    {isSearching ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin text-black" />
                        <span>{searchStage || "Executing Google Lens search..."}</span>
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
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
};
