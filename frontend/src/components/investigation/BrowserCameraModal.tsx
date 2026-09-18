import React, { useRef, useState, useEffect, useCallback } from "react";
import { Camera, X, RefreshCw, CheckCircle2, AlertCircle, Sparkles } from "lucide-react";

interface BrowserCameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
}

export const BrowserCameraModal: React.FC<BrowserCameraModalProps> = ({
  isOpen,
  onClose,
  onCapture,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [status, setStatus] = useState<
    "requesting" | "ready" | "captured" | "error"
  >("requesting");
  const [capturedBlobUrl, setCapturedBlobUrl] = useState<string | null>(null);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    stopCamera();
    setStatus("requesting");
    setErrorMessage(null);
    setCapturedBlobUrl(null);
    setCapturedFile(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("error");
      setErrorMessage("Camera access is not supported by your browser environment.");
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
          setStatus("ready");
        };
      } else {
        setStatus("ready");
      }
    } catch (err: any) {
      console.warn("Camera init failure:", err);
      setStatus("error");
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Camera permission denied. Please grant browser camera access.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setErrorMessage("No video capture device detected.");
      } else {
        setErrorMessage(err.message || "Failed to initialize camera stream.");
      }
    }
  }, [stopCamera]);

  useEffect(() => {
    if (isOpen) {
      startCamera();
    } else {
      stopCamera();
      setStatus("requesting");
      setCapturedBlobUrl(null);
      setCapturedFile(null);
    }
    return () => {
      stopCamera();
    };
  }, [isOpen, startCamera, stopCamera]);

  const handleCaptureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;

    const width = video.videoWidth || 1280;
    const height = video.videoHeight || 720;
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Draw raw camera frame
    ctx.drawImage(video, 0, 0, width, height);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `cyberhub_capture_${Date.now()}.jpg`, {
        type: "image/jpeg",
      });
      const url = URL.createObjectURL(blob);
      setCapturedBlobUrl(url);
      setCapturedFile(file);
      setStatus("captured");
      stopCamera();
    }, "image/jpeg", 0.95);
  };

  const handleRetake = () => {
    if (capturedBlobUrl) {
      URL.revokeObjectURL(capturedBlobUrl);
    }
    setCapturedBlobUrl(null);
    setCapturedFile(null);
    startCamera();
  };

  const handleConfirmPhoto = () => {
    if (capturedFile) {
      onCapture(capturedFile);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-[#0C0C0C] border border-[#1A1A1A] rounded-xl overflow-hidden shadow-2xl flex flex-col">
        {/* Modal Header */}
        <div className="h-12 px-4 border-b border-[#1A1A1A] flex items-center justify-between bg-[#080808]">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#F5F5F5]" />
            <span className="text-xs font-semibold text-[#F5F5F5] uppercase tracking-wider">
              Live Camera Capture
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Viewport Area */}
        <div className="relative aspect-video bg-[#000000] flex items-center justify-center overflow-hidden">
          {/* Live Video */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${status === "ready" ? "block" : "hidden"}`}
          />

          {/* Captured Preview */}
          {status === "captured" && capturedBlobUrl && (
            <img
              src={capturedBlobUrl}
              alt="Captured reference"
              className="w-full h-full object-contain bg-[#050505]"
            />
          )}

          {/* Hidden Canvas for Frame Grab */}
          <canvas ref={canvasRef} className="hidden" />

          {/* Framing Guide Overlay (When Live) */}
          {status === "ready" && (
            <div className="absolute inset-0 pointer-events-none flex flex-col items-center justify-center">
              {/* Subtle face/target oval */}
              <div className="w-56 h-72 rounded-[50%] border-2 border-dashed border-[#F5F5F5]/40 flex items-center justify-center shadow-[0_0_50px_rgba(0,0,0,0.8)]">
                <div className="w-2 h-2 rounded-full bg-[#10B981]/80 animate-ping" />
              </div>
              <span className="mt-4 px-2.5 py-1 rounded bg-black/80 border border-[#1A1A1A] text-[11px] font-mono text-[#B3B3B3]">
                Center face or target subject in frame
              </span>
            </div>
          )}

          {/* Requesting / Loading */}
          {status === "requesting" && (
            <div className="flex flex-col items-center gap-3 p-6 text-center">
              <RefreshCw className="w-6 h-6 text-[#777777] animate-spin" />
              <p className="text-xs text-[#B3B3B3]">Initializing camera device...</p>
            </div>
          )}

          {/* Error State */}
          {status === "error" && (
            <div className="flex flex-col items-center gap-3 p-6 max-w-md text-center">
              <AlertCircle className="w-8 h-8 text-[#ef4444]" />
              <p className="text-xs font-semibold text-[#F5F5F5]">Camera Initialization Failed</p>
              <p className="text-xs text-[#777777]">{errorMessage}</p>
              <button
                type="button"
                onClick={startCamera}
                className="mt-2 px-3 py-1.5 rounded-md bg-[#151515] border border-[#2B2B2B] text-xs text-[#F5F5F5] hover:bg-[#202020] transition-colors"
              >
                Retry Camera
              </button>
            </div>
          )}
        </div>

        {/* Modal Controls / Footer */}
        <div className="p-4 border-t border-[#1A1A1A] bg-[#080808] flex items-center justify-between">
          <div className="text-[11px] font-mono text-[#777777]">
            {status === "ready" && "Live Stream Active (1280x720)"}
            {status === "captured" && "Frame captured • Ready to search"}
            {status === "requesting" && "Connecting..."}
            {status === "error" && "Offline"}
          </div>

          <div className="flex items-center gap-2">
            {status === "ready" && (
              <button
                type="button"
                onClick={handleCaptureFrame}
                className="px-4 py-2 rounded-lg bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all flex items-center gap-2 shadow-sm"
              >
                <Camera className="w-3.5 h-3.5" />
                Capture Frame
              </button>
            )}

            {status === "captured" && (
              <>
                <button
                  type="button"
                  onClick={handleRetake}
                  className="px-3 py-2 rounded-lg bg-[#111111] border border-[#2B2B2B] text-xs text-[#B3B3B3] hover:text-[#F5F5F5] hover:bg-[#1A1A1A] transition-colors flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retake Photo
                </button>
                <button
                  type="button"
                  onClick={handleConfirmPhoto}
                  className="px-4 py-2 rounded-lg bg-[#F5F5F5] text-black text-xs font-semibold hover:bg-white transition-all flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-black" />
                  Use This Photo
                </button>
              </>
            )}

            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 rounded-lg text-xs text-[#777777] hover:text-[#F5F5F5] hover:bg-[#151515] transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
