import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Camera,
  Upload,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  FileImage,
} from "lucide-react";
import { formatErrorMessage, safeRenderText } from "../../utils/errorUtils";

export type CameraState =
  | "CAMERA_REQUESTING"
  | "CAMERA_READY"
  | "CAPTURING"
  | "CAPTURED"
  | "CAMERA_PERMISSION_DENIED"
  | "NO_CAMERA"
  | "CAMERA_ERROR";

interface CameraCaptureProps {
  onImageSelected: (file: File, previewUrl: string) => void;
  selectedPreviewUrl?: string | null;
  onClearImage?: () => void;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({
  onImageSelected,
  selectedPreviewUrl,
  onClearImage,
}) => {
  const [cameraState, setCameraState] = useState<CameraState>("CAMERA_REQUESTING");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"camera" | "upload">("camera");

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Stop camera stream safely
  const stopCameraStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  // Start browser camera stream
  const startCamera = useCallback(async () => {
    stopCameraStream();
    setErrorMessage(null);
    setCameraState("CAMERA_REQUESTING");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraState("NO_CAMERA");
      setErrorMessage("Camera access is not supported by your browser environment.");
      setActiveTab("upload");
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
          setCameraState("CAMERA_READY");
        };
      } else {
        setCameraState("CAMERA_READY");
      }
    } catch (err: any) {
      console.warn("Camera init failed:", err);
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setCameraState("CAMERA_PERMISSION_DENIED");
        setErrorMessage("Camera permission was denied. Please allow camera access in your browser or upload an image instead.");
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        setCameraState("NO_CAMERA");
        setErrorMessage("No camera hardware was detected on this device.");
      } else {
        setCameraState("CAMERA_ERROR");
        setErrorMessage(formatErrorMessage(err, "Failed to initialize device camera stream."));
      }
      setActiveTab("upload");
    }
  }, [stopCameraStream]);

  // Handle Capture Action
  const handleCaptureFrame = () => {
    if (!videoRef.current || cameraState !== "CAMERA_READY") return;

    setCameraState("CAPTURING");
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      setCameraState("CAMERA_ERROR");
      setErrorMessage("Failed to acquire 2D rendering canvas context.");
      return;
    }

    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setCameraState("CAMERA_ERROR");
          setErrorMessage("Failed to encode canvas frame to JPEG image.");
          return;
        }

        const capturedFile = new File(
          [blob],
          `camera_capture_${Date.now()}.jpg`,
          { type: "image/jpeg" }
        );
        const previewUrl = URL.createObjectURL(blob);

        stopCameraStream();
        setCameraState("CAPTURED");
        onImageSelected(capturedFile, previewUrl);
      },
      "image/jpeg",
      0.94
    );
  };

  // Handle Retake
  const handleRetake = () => {
    if (onClearImage) onClearImage();
    setActiveTab("camera");
    startCamera();
  };

  // Handle File Upload from disk
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setErrorMessage("Please select a supported image file (JPEG, PNG, WEBP).");
      return;
    }

    const previewUrl = URL.createObjectURL(file);
    stopCameraStream();
    setCameraState("CAPTURED");
    onImageSelected(file, previewUrl);
  };

  useEffect(() => {
    if (activeTab === "camera" && !selectedPreviewUrl) {
      startCamera();
    } else {
      stopCameraStream();
    }
    return () => {
      stopCameraStream();
    };
  }, [activeTab, selectedPreviewUrl, startCamera, stopCameraStream]);

  return (
    <div className="w-full space-y-4 text-left">
      {/* Tab Switcher */}
      {!selectedPreviewUrl && (
        <div className="flex items-center gap-1.5 p-1 bg-[#080808] border border-[#1A1A1A] rounded-md w-fit">
          <button
            type="button"
            onClick={() => {
              setActiveTab("camera");
              startCamera();
            }}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === "camera"
                ? "bg-[#1A1A1A] text-[#F5F5F5] font-semibold"
                : "text-[#777777] hover:text-[#F5F5F5]"
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Live Camera</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveTab("upload");
              stopCameraStream();
            }}
            className={`px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === "upload"
                ? "bg-[#1A1A1A] text-[#F5F5F5] font-semibold"
                : "text-[#777777] hover:text-[#F5F5F5]"
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload File</span>
          </button>
        </div>
      )}

      {/* Main View Area */}
      <div className="bg-[#0C0C0C] border border-[#1A1A1A] rounded-lg overflow-hidden min-h-[320px]">
        {/* CASE 1: Captured Preview */}
        {selectedPreviewUrl ? (
          <div className="p-5 flex flex-col items-center justify-center text-center">
            <div className="relative max-w-md w-full rounded bg-black border border-[#232323] overflow-hidden p-2">
              <img
                src={selectedPreviewUrl}
                alt="Reference capture"
                className="w-full h-auto max-h-[320px] object-contain mx-auto rounded"
              />
              <div className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded bg-black/85 border border-[#10B981]/30 text-[#10B981] text-[10px] font-mono flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>FRAME ACQUIRED</span>
              </div>
            </div>

            <div className="mt-3.5">
              <button
                type="button"
                onClick={handleRetake}
                className="px-3.5 py-1.5 text-xs font-medium border border-[#232323] text-[#B3B3B3] hover:text-[#F5F5F5] rounded bg-[#151515] hover:bg-[#1E1E1E] transition-colors flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Retake / Change Image</span>
              </button>
            </div>
          </div>
        ) : activeTab === "camera" && cameraState === "CAMERA_READY" ? (
          /* CASE 2: Live Camera Stream */
          <div className="p-4 flex flex-col items-center justify-center">
            <div className="relative w-full max-w-lg aspect-video rounded bg-black border border-[#232323] overflow-hidden">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover transform -scale-x-100"
              />

              <div className="absolute top-2.5 left-2.5 px-2 py-0.5 rounded bg-black/85 border border-[#232323] text-[#F5F5F5] text-[10px] font-mono flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                <span>STREAMING</span>
              </div>
            </div>

            <div className="mt-3.5">
              <button
                type="button"
                onClick={handleCaptureFrame}
                className="h-9 px-5 bg-[#F5F5F5] hover:bg-white text-[#000000] text-xs font-semibold rounded flex items-center gap-2 active:scale-95 transition-all"
              >
                <Camera className="w-3.5 h-3.5 text-black" />
                <span>Capture Frame</span>
              </button>
            </div>
          </div>
        ) : activeTab === "camera" && cameraState === "CAMERA_REQUESTING" ? (
          /* CASE 3: Camera Initializing */
          <div className="flex flex-col items-center justify-center p-12 text-center min-h-[300px]">
            <RefreshCw className="w-6 h-6 text-[#777777] animate-spin mb-3" />
            <p className="text-xs text-[#F5F5F5] font-medium">Connecting to Camera...</p>
            <p className="text-[11px] text-[#777777] mt-1">Please grant camera access in your browser.</p>
          </div>
        ) : (
          /* CASE 4: File Upload Drop Area */
          <div className="p-8 sm:p-12 flex flex-col items-center justify-center text-center">
            {errorMessage && (
              <div className="mb-4 p-3 rounded bg-[#111111] border border-[#ef4444]/40 max-w-md w-full flex items-start gap-2 text-xs text-[#ef4444] text-left">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{safeRenderText(errorMessage)}</span>
              </div>
            )}

            <div
              onClick={() => fileInputRef.current?.click()}
              className="w-full max-w-md border border-dashed border-[#232323] hover:border-[#383838] bg-[#080808] hover:bg-[#0E0E0E] rounded-lg p-8 cursor-pointer transition-all flex flex-col items-center justify-center"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-10 h-10 rounded bg-[#151515] border border-[#232323] flex items-center justify-center mb-2.5 text-[#B3B3B3]">
                <FileImage className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-[#F5F5F5]">Upload Authorized Reference Image</p>
              <p className="text-[11px] text-[#777777] mt-0.5">JPEG, PNG, or WebP up to 50 MB</p>

              <button
                type="button"
                className="mt-4 px-3.5 py-1.5 text-xs font-medium bg-[#151515] text-[#F5F5F5] border border-[#232323] rounded pointer-events-none"
              >
                Browse File
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
