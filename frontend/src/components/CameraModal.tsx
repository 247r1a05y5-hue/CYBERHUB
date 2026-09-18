import React, { useRef, useState, useEffect, useCallback } from "react";
import { Camera, X, RotateCw, CheckCircle2, AlertCircle } from "lucide-react";

interface CameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
}

export const CameraModal: React.FC<CameraModalProps> = ({
  isOpen,
  onClose,
  onCapture,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [status, setStatus] = useState<"requesting" | "ready" | "captured" | "error">("requesting");
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
      setErrorMessage("Camera access is not supported by your browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
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
      setStatus("error");
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setErrorMessage("Camera permission denied. Please allow camera access in browser settings.");
      } else {
        setErrorMessage(err.message || "Failed to initialize camera.");
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
    return () => stopCamera();
  }, [isOpen, startCamera, stopCamera]);

  const handleCapture = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const w = video.videoWidth || 1280;
    const h = video.videoHeight || 720;
    canvas.width = w;
    canvas.height = h;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `cyberhub_cam_${Date.now()}.jpg`, { type: "image/jpeg" });
      const url = URL.createObjectURL(blob);
      setCapturedBlobUrl(url);
      setCapturedFile(file);
      setStatus("captured");
      stopCamera();
    }, "image/jpeg", 0.95);
  };

  const handleRetake = () => {
    if (capturedBlobUrl) URL.revokeObjectURL(capturedBlobUrl);
    setCapturedBlobUrl(null);
    setCapturedFile(null);
    startCamera();
  };

  const handleConfirm = () => {
    if (capturedFile) {
      onCapture(capturedFile);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-2xl max-w-xl w-full overflow-hidden flex flex-col">
        {/* Header */}
        <div className="h-12 px-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
          <div className="flex items-center gap-2">
            <Camera className="w-4 h-4 text-gray-700" />
            <span className="text-xs font-bold text-gray-900 uppercase tracking-wider">
              Camera Capture
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Video Frame */}
        <div className="relative aspect-video bg-gray-900 flex items-center justify-center overflow-hidden">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className={`w-full h-full object-cover ${status === "ready" ? "block" : "hidden"}`}
          />

          {status === "captured" && capturedBlobUrl && (
            <img
              src={capturedBlobUrl}
              alt="Camera preview"
              className="w-full h-full object-contain bg-black"
            />
          )}

          <canvas ref={canvasRef} className="hidden" />

          {/* Guide Overlay */}
          {status === "ready" && (
            <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
              <div className="w-48 h-64 rounded-[50%] border-2 border-dashed border-white/60 shadow-lg" />
            </div>
          )}

          {status === "requesting" && (
            <div className="text-center text-white p-6 space-y-2">
              <RotateCw className="w-6 h-6 animate-spin mx-auto text-indigo-400" />
              <p className="text-xs">Connecting to device camera...</p>
            </div>
          )}

          {status === "error" && (
            <div className="text-center text-white p-6 max-w-sm space-y-2">
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
              <p className="text-xs font-semibold text-red-200">{errorMessage}</p>
              <button
                type="button"
                onClick={startCamera}
                className="mt-2 px-3 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-xs font-semibold"
              >
                Retry
              </button>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between">
          <span className="text-[11px] text-gray-500 font-mono">
            {status === "ready" && "Ready to capture"}
            {status === "captured" && "Photo captured"}
            {status === "requesting" && "Initializing..."}
          </span>

          <div className="flex items-center gap-2">
            {status === "ready" && (
              <button
                type="button"
                onClick={handleCapture}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm cursor-pointer"
              >
                <Camera className="w-3.5 h-3.5 text-white" />
                <span>Capture Frame</span>
              </button>
            )}

            {status === "captured" && (
              <>
                <button
                  type="button"
                  onClick={handleRetake}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-100 text-gray-700 text-xs font-semibold cursor-pointer"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                  <span>Retake</span>
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm cursor-pointer"
                >
                  <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  <span>Use Photo</span>
                </button>
              </>
            )}

            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 rounded-xl text-xs text-gray-500 hover:text-gray-800 cursor-pointer"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
