"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { captureFrame, detectBlur } from "@/lib/blurDetection";
import { queueCapture, getPendingCaptures, getCaptureCount } from "@/lib/db";
import { getApiKey } from "@/utils/api";
import Link from "next/link";

type SlotKey =
  | "left_side_profile"
  | "right_side_profile"
  | "rear_view"
  | "front_view"
  | "engine_bay"
  | "underbody";

interface SlotDef {
  key: SlotKey;
  label: string;
  required: boolean;
  guidance: string;
  overlay: string;
}

const SLOTS: SlotDef[] = [
  {
    key: "left_side_profile",
    label: "Left Side",
    required: true,
    guidance: "Full left side, level with chassis",
    overlay: "left_side_profile",
  },
  {
    key: "right_side_profile",
    label: "Right Side",
    required: true,
    guidance: "Full right side, level with chassis",
    overlay: "right_side_profile",
  },
  {
    key: "rear_view",
    label: "Rear View",
    required: true,
    guidance: "Direct rear, centered on plate",
    overlay: "rear_view",
  },
  {
    key: "front_view",
    label: "Front View",
    required: false,
    guidance: "Direct front, centered on grille",
    overlay: "front_view",
  },
  {
    key: "engine_bay",
    label: "Engine Bay",
    required: false,
    guidance: "Hood open, top-down view",
    overlay: "engine_bay",
  },
  {
    key: "underbody",
    label: "Underbody",
    required: false,
    guidance: "From rear, low angle looking forward",
    overlay: "underbody",
  },
];

const API_BASE = "http://localhost:8000/api/v1";

function drawOverlay(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  overlay: string
) {
  ctx.clearRect(0, 0, w, h);

  const marginX = w * 0.1;
  const marginY = h * 0.15;
  const boxW = w - marginX * 2;
  const boxH = h - marginY * 2;

  ctx.fillStyle = "rgba(0,0,0,0.35)";
  ctx.fillRect(0, 0, w, h);

  ctx.clearRect(marginX, marginY, boxW, boxH);

  ctx.strokeStyle = "rgba(255,255,255,0.8)";
  ctx.lineWidth = 2;
  ctx.setLineDash([]);
  ctx.strokeRect(marginX, marginY, boxW, boxH);

  ctx.fillStyle = "rgba(255,255,255,0.9)";
  ctx.font = "14px system-ui, sans-serif";
  ctx.fillText("Keep vehicle within guides", marginX + 12, marginY + 24);

  if (overlay === "left_side_profile" || overlay === "right_side_profile") {
    const centerX = w / 2;
    const cx = (boxW / 2) * 0.15;
    ctx.strokeStyle = "rgba(255,255,255,0.4)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 6]);
    ctx.beginPath();
    ctx.moveTo(centerX - cx, marginY);
    ctx.lineTo(centerX - cx, marginY + boxH);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(centerX + cx, marginY);
    ctx.lineTo(centerX + cx, marginY + boxH);
    ctx.stroke();
  }
}

export default function CapturePage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const [activeSlot, setActiveSlot] = useState<SlotKey>("left_side_profile");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [captured, setCaptured] = useState<Partial<Record<SlotKey, string>>>(
    {}
  );
  const [blurryWarning, setBlurryWarning] = useState<SlotKey | null>(null);
  const [uploading, setUploading] = useState<SlotKey | null>(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [offline, setOffline] = useState(false);
  const [intakeId, setIntakeId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  useEffect(() => {
    setOffline(!navigator.onLine);
    const handleOffline = () => setOffline(true);
    const handleOnline = () => setOffline(false);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  useEffect(() => {
    getCaptureCount().then(setPendingCount);
  }, []);

  const startCamera = useCallback(async (facingMode: string = "environment") => {
    try {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = s;
      setStream(s);
      if (videoRef.current) {
        videoRef.current.srcObject = s;
      }
      setError(null);
    } catch (err) {
      setError(
        `Camera access denied: ${err instanceof Error ? err.message : "unknown"}`
      );
    }
  }, []);

  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    startCamera("environment");
    return () => {
      const s = streamRef.current;
      if (s) {
        s.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (stream) {
      const video = videoRef.current;
      if (!video) return;

      const handleCanPlay = () => {
        const overlay = overlayRef.current;
        if (overlay && overlay.parentElement) {
          overlay.width = overlay.parentElement.clientWidth;
          overlay.height = overlay.parentElement.clientHeight;
          const ctx = overlay.getContext("2d");
          if (ctx) {
            drawOverlay(ctx, overlay.width, overlay.height, activeSlot);
          }
        }
      };

      video.addEventListener("canplay", handleCanPlay);
      return () => video.removeEventListener("canplay", handleCanPlay);
    }
  }, [stream, activeSlot]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay || !stream) return;
    const parent = overlay.parentElement;
    if (!parent) return;
    overlay.width = parent.clientWidth;
    overlay.height = parent.clientHeight;
    const ctx = overlay.getContext("2d");
    if (ctx) drawOverlay(ctx, overlay.width, overlay.height, activeSlot);
  }, [activeSlot, stream]);

  const handleCapture = useCallback(async () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;

    const blob = await captureFrame(video);
    if (!blob) return;

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const { isBlurry } = detectBlur(imageData);

    if (isBlurry) {
      setBlurryWarning(activeSlot);
      return;
    }
    setBlurryWarning(null);

    const url = URL.createObjectURL(blob);
    setCaptured((prev) => ({ ...prev, [activeSlot]: url }));

    setUploading(activeSlot);

    try {
      if (offline || !navigator.onLine) {
        await queueCapture(activeSlot, blob);
        setPendingCount((c) => c + 1);
        setUploading(null);
        return;
      }

      const fd = new FormData();

      if (!intakeId) {
        fd.append("workshop_id", "demo-workshop");
        fd.append(activeSlot, blob, `${activeSlot}.jpg`);

        const key = getApiKey();
        const headers: Record<string, string> = {};
        if (key) headers["X-API-Key"] = key;

        const res = await fetch(`${API_BASE}/intake`, {
          method: "POST",
          headers,
          body: fd,
        });

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`Upload failed (${res.status}): ${text}`);
        }

        const data = await res.json();
        setIntakeId(data.intake_id);

        if (data.attempts?.[activeSlot] >= 3) {
          // mark as exhausted
        }
      } else {
        fd.append("file", blob, `${activeSlot}.jpg`);
        const key = getApiKey();
        const headers: Record<string, string> = {};
        if (key) headers["X-API-Key"] = key;

        const res = await fetch(
          `${API_BASE}/intake/${intakeId}/views/${activeSlot}`,
          { method: "PUT", headers, body: fd }
        );

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`Re-upload failed (${res.status}): ${text}`);
        }
      }
    } catch {
      await queueCapture(activeSlot, blob);
      setPendingCount((c) => c + 1);
      if (!offline && navigator.onLine && intakeId) {
        const requiredKeys: SlotKey[] = ["left_side_profile", "right_side_profile", "rear_view"];
        const nextCaptured = { ...captured, [activeSlot]: url };
        const allRequiredDone = requiredKeys.every((k) => nextCaptured[k]);
        if (allRequiredDone) {
          try {
            const key = getApiKey();
            const h: Record<string, string> = {};
            if (key) h["X-API-Key"] = key;
            const analyzeRes = await fetch(
              `${API_BASE}/intake/${intakeId}/analyze`,
              { method: "POST", headers: h }
            );
            if (analyzeRes.ok) {
              const analyzeData = await analyzeRes.json();
              setJobId(analyzeData.job_id);
            }
          } catch {
            // user can trigger from main page
          }
        }
      }
    } finally {
      setUploading(null);
    }
  }, [activeSlot, intakeId, offline, captured]);

  const retake = useCallback(() => {
    setBlurryWarning(null);
    setCaptured((prev) => {
      const next = { ...prev };
      delete next[activeSlot];
      return next;
    });
  }, [activeSlot]);

  const switchSlot = useCallback(
    (key: SlotKey) => {
      setActiveSlot(key);
      setBlurryWarning(null);
    },
    []
  );

  const requiredDone = SLOTS.filter((s) => s.required).every(
    (s) => captured[s.key]
  );
  const allDone = SLOTS.every((s) => captured[s.key]);
  const isAnalyzing = jobId !== null && captured.left_side_profile && captured.right_side_profile && captured.rear_view;

  return (
    <div className="flex flex-1 flex-col bg-black text-white">
      <div className="flex items-center justify-between px-3 py-2">
        <Link
          href="/"
          className="text-sm text-white/70 hover:text-white transition-colors"
        >
          ← Back
        </Link>
        <h1 className="text-sm font-semibold">Field Capture</h1>
        {offline && (
          <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-medium text-amber-400">
            Offline
          </span>
        )}
        {!offline && pendingCount > 0 && (
          <span className="rounded-full bg-blue-500/20 px-2 py-0.5 text-[10px] font-medium text-blue-400">
            {pendingCount} pending
          </span>
        )}
        {!offline && pendingCount === 0 && <div className="w-14" />}
      </div>

      <div className="relative flex-1 mx-2 mb-2 rounded-xl overflow-hidden bg-zinc-900">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 h-full w-full object-cover"
        />
        <canvas
          ref={overlayRef}
          className="absolute inset-0 h-full w-full pointer-events-none"
        />
        {!stream && (
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              onClick={() => startCamera("environment")}
              className="rounded-xl bg-white/10 px-6 py-3 text-sm font-medium backdrop-blur hover:bg-white/20 transition-colors"
            >
              Start Camera
            </button>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center px-6">
            <div className="rounded-xl bg-red-500/20 p-4 text-center backdrop-blur">
              <p className="text-sm text-red-300">{error}</p>
              <button
                onClick={() => { setError(null); startCamera("environment"); }}
                className="mt-3 rounded-lg bg-white/10 px-4 py-1.5 text-xs font-medium hover:bg-white/20 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {blurryWarning && (
          <div className="absolute bottom-4 left-4 right-4 rounded-xl bg-amber-500/20 p-4 backdrop-blur text-center">
            <p className="text-sm font-medium text-amber-300">
              Photo is blurry — please retake
            </p>
            <p className="mt-0.5 text-xs text-amber-400/80">
              Hold the phone steady and ensure good lighting
            </p>
            <button
              onClick={retake}
              className="mt-3 rounded-lg bg-amber-500 px-6 py-1.5 text-xs font-medium text-white hover:bg-amber-600 transition-colors"
            >
              Retake
            </button>
          </div>
        )}

        {stream && (
          <button
            onClick={handleCapture}
            disabled={uploading !== null}
            className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center justify-center w-16 h-16 rounded-full border-4 border-white/80 bg-white/10 backdrop-blur hover:bg-white/20 transition-colors disabled:opacity-40"
          >
            {uploading ? (
              <span className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <span className="block h-8 w-8 rounded-full bg-white" />
            )}
          </button>
        )}
      </div>

      <div className="flex gap-1 px-2 pb-2 overflow-x-auto">
        {SLOTS.map((slot) => {
          const isActive = activeSlot === slot.key;
          const isCaptured = !!captured[slot.key];
          return (
            <button
              key={slot.key}
              onClick={() => !isActive && switchSlot(slot.key)}
              disabled={isActive}
              className={`shrink-0 rounded-lg px-3 py-2 text-[10px] font-medium transition-colors ${
                isActive
                  ? "bg-white/20 text-white"
                  : isCaptured
                    ? "bg-green-500/20 text-green-300"
                    : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              {slot.label}
              {slot.required && <span className="ml-0.5 text-red-400">*</span>}
              {isCaptured && <span className="ml-1 text-green-300">✓</span>}
            </button>
          );
        })}
      </div>

      <div className="px-3 py-2 border-t border-white/10">
        <div className="flex items-center justify-between text-xs text-white/50">
          <span>
            {requiredDone
              ? allDone
                ? "All views captured"
                : "Required views complete"
              : `${SLOTS.filter((s) => s.required && captured[s.key]).length}/${SLOTS.filter((s) => s.required).length} required`}
          </span>
          {(jobId || intakeId) && (
            <Link
              href={jobId ? `/reports/${jobId}` : `/?job_id=${intakeId}`}
              className="text-brand hover:text-brand-dark transition-colors"
            >
              {jobId ? "View Report →" : "View Progress →"}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
