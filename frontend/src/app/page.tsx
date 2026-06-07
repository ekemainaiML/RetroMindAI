"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAssessment } from "@/hooks/useAssessment";
import { STAGE_LABELS, type OEMSearchResult, type OEMSearchResponse } from "@/types/assessment";
import { apiPost, apiGet, ensureApiKey, getApiKey, clearApiKey, setApiKey } from "@/utils/api";
import Tooltip from "@/components/ui/Tooltip";
import AssessmentResult from "@/components/assessment/AssessmentResult";
import type { IdentifyVehicleResponse } from "@/types/assessment";
import OnboardingGuide from "@/components/OnboardingGuide";
import HelpBubble from "@/components/HelpBubble";

const JOB_ID_STORAGE_KEY = "retromind_active_job_id";

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
}

interface SlotUploadInfo {
  attempt: number;
  blurry: boolean;
  occluded: boolean;
  filePath: string | null;
}

type SlotUploadMap = Record<SlotKey, SlotUploadInfo>;

const INITIAL_SLOT_INFO: SlotUploadInfo = {
  attempt: 0,
  blurry: false,
  occluded: false,
  filePath: null,
};

const SLOTS: SlotDef[] = [
  {
    key: "left_side_profile",
    label: "Left Side Profile",
    required: true,
    guidance: "Capture the full left side, level with the chassis — shows wheelbase, running boards, and panel alignment",
  },
  {
    key: "right_side_profile",
    label: "Right Side Profile",
    required: true,
    guidance: "Capture the full right side, level with the chassis — shows wheelbase, running boards, and panel alignment",
  },
  {
    key: "rear_view",
    label: "Rear View",
    required: true,
    guidance: "Direct rear view, centered on license plate area — shows bumper, tailgate, taillights, and chassis width",
  },
  {
    key: "front_view",
    label: "Front View",
    required: false,
    guidance: "Direct front view, centered on grille — shows bumper, headlights, hood, and front suspension",
  },
  {
    key: "engine_bay",
    label: "Engine Bay",
    required: false,
    guidance: "Hood fully open, top-down view — shows engine layout, battery tray area, and wiring harness routing",
  },
  {
    key: "underbody",
    label: "Underbody",
    required: false,
    guidance: "From rear, looking forward at a low angle — shows frame rails, fuel tank, exhaust, and axle assembly",
  },
];

const MAX_ATTEMPTS = 3;

function UploadSlot({
  slot,
  preview,
  slotInfo,
  disabled,
  onSelect,
}: {
  slot: SlotDef;
  preview: string | null;
  slotInfo: SlotUploadInfo;
  disabled: boolean;
  onSelect: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const isUnusable = slot.required && slotInfo.attempt >= MAX_ATTEMPTS;

  return (
    <div
      className={`relative flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-colors ${
        isUnusable
          ? "border-red-300 bg-red-50 opacity-60 dark:border-red-700 dark:bg-red-950"
          : preview
            ? "border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950"
            : "border-dashed border-zinc-300 hover:border-zinc-400 dark:border-zinc-600 dark:hover:border-zinc-500"
      }`}
    >
      {!isUnusable && (
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          disabled={disabled}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onSelect(file);
          }}
        />
      )}

      {preview ? (
        <div
          className="relative w-full cursor-pointer"
          onClick={() => !isUnusable && inputRef.current?.click()}
        >
          <img
            src={preview}
            alt={slot.label}
            className="h-28 w-full rounded-lg object-cover"
          />
          {slotInfo.blurry && (
            <div className="absolute inset-x-0 bottom-0 rounded-b-lg bg-yellow-500/80 px-2 py-1 text-center text-[10px] font-medium text-white">
              Blurry — may reduce accuracy
            </div>
          )}
          {slotInfo.occluded && (
            <div className="absolute inset-x-0 bottom-0 rounded-b-lg bg-orange-500/80 px-2 py-1 text-center text-[10px] font-medium text-white">
              Occlusion detected — recapture for full accuracy
            </div>
          )}
        </div>
      ) : (
        <div
          className={`flex h-28 w-full cursor-pointer items-center justify-center rounded-lg ${
            isUnusable
              ? "bg-red-100 text-red-400 dark:bg-red-900"
              : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800"
          }`}
          onClick={() => !isUnusable && inputRef.current?.click()}
        >
          <svg
            className="h-8 w-8"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </div>
      )}

      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
          {slot.label}
          {slot.required && <span className="ml-1 text-red-500">*</span>}
          {!slot.required && (
            <span className="ml-1 text-zinc-400">(optional)</span>
          )}
        </span>
        {slotInfo.attempt > 0 && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              slotInfo.attempt >= MAX_ATTEMPTS
                ? "bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-300"
                : "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400"
            }`}
          >
            {isUnusable
              ? "View unusable"
              : `Attempt ${slotInfo.attempt}/${MAX_ATTEMPTS}`}
          </span>
        )}
      </div>

      <span className="flex items-center gap-1 text-center text-[10px] leading-tight text-zinc-400">
        {slot.guidance}
        <Tooltip text="Use diffuse daylight. Keep the camera level and steady. Ensure the entire vehicle section is in frame — avoid obstructions. Retake if the image is blurry or poorly lit.">
          <span className="inline-flex h-3.5 w-3.5 cursor-help items-center justify-center rounded-full border border-zinc-300 text-[8px] font-bold text-zinc-400 dark:border-zinc-600 dark:text-zinc-500">
            ?
          </span>
        </Tooltip>
      </span>

      {preview && !isUnusable && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            inputRef.current?.click();
          }}
          className="text-[10px] font-medium text-blue-500 underline underline-offset-2 hover:text-blue-700"
        >
          Replace photo
        </button>
      )}
    </div>
  );
}

function MissingViewRecoveryDialog({
  missingViews,
  lowQualityViews,
  swapSuspected,
  onUploadNow,
  onContinueLimited,
  onSwapNow,
  onKeepAsIs,
}: {
  missingViews: string[];
  lowQualityViews: string[];
  swapSuspected: boolean;
  onUploadNow: () => void;
  onContinueLimited: () => void;
  onSwapNow: () => void;
  onKeepAsIs: () => void;
}) {
  return (
    <div className="mt-6 space-y-4 rounded-xl border border-yellow-300 bg-yellow-50 p-6 dark:border-yellow-700 dark:bg-yellow-950">
      <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-200">
        Some views need attention
      </h3>

      {missingViews.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-yellow-700 dark:text-yellow-300">
            Missing required views:
          </p>
          {missingViews.map((v) => (
            <div
              key={v}
              className="flex items-center justify-between rounded-lg border border-yellow-200 bg-white p-3 dark:border-yellow-800 dark:bg-yellow-900"
            >
              <span className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                {v.replace(/_/g, " ")} not submitted
              </span>
              <button
                type="button"
                onClick={onUploadNow}
                className="rounded-md bg-yellow-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-yellow-700"
              >
                Upload Now
              </button>
            </div>
          ))}
        </div>
      )}

      {lowQualityViews.length > 0 && (
        <div>
          <p className="text-xs text-yellow-700 dark:text-yellow-300">
            Low quality views (may reduce accuracy):{" "}
            {lowQualityViews.map((v) => v.replace(/_/g, " ")).join(", ")}
          </p>
        </div>
      )}

      {swapSuspected && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 dark:border-purple-800 dark:bg-purple-950">
          <p className="text-xs font-medium text-purple-700 dark:text-purple-300">
            Left and right views may be swapped.
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={onKeepAsIs}
              className="rounded-md border border-purple-300 bg-white px-3 py-1 text-[10px] font-medium text-purple-700 hover:bg-purple-50 dark:border-purple-700 dark:bg-purple-900 dark:text-purple-300"
            >
              Keep as is
            </button>
            <button
              type="button"
              onClick={onSwapNow}
              className="rounded-md bg-purple-600 px-3 py-1 text-[10px] font-medium text-white hover:bg-purple-700"
            >
              Swap them
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <button
          type="button"
          onClick={onUploadNow}
          className="flex-1 rounded-lg bg-yellow-600 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-700"
        >
          Upload Now
        </button>
        <button
          type="button"
          onClick={onContinueLimited}
          className="flex-1 rounded-lg border border-yellow-400 bg-white px-4 py-2 text-sm font-medium text-yellow-700 hover:bg-yellow-50 dark:border-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
        >
          Continue with Limited Analysis
        </button>
      </div>
    </div>
  );
}

export default function Home() {
  const [files, setFiles] = useState<Record<SlotKey, File | null>>(
    {} as Record<SlotKey, File | null>
  );
  const [previews, setPreviews] = useState<Record<SlotKey, string | null>>(
    {} as Record<SlotKey, string | null>
  );
  const [slotInfo, setSlotInfo] = useState<Record<SlotKey, SlotUploadInfo>>(
    {} as Record<SlotKey, SlotUploadInfo>
  );
  const [intakeId, setIntakeId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryData, setRecoveryData] = useState<{
    missingViews: string[];
    lowQualityViews: string[];
    swapSuspected: boolean;
  } | null>(null);
  const [reuploadingSlot, setReuploadingSlot] = useState<SlotKey | null>(null);

  const {
    job: jobState,
    assessment,
    error: pollError,
    loading: assessmentLoading,
    confirm: handleConfirm,
    softTimedOut,
  } = useAssessment(jobId);

  const allRequiredFilled = SLOTS.filter((s) => s.required).every(
    (s) => files[s.key]
  );

  const [oemSearchQuery, setOemSearchQuery] = useState("");
  const [oemSearchResults, setOemSearchResults] = useState<OEMSearchResult[]>([]);
  const [oemSearchOpen, setOemSearchOpen] = useState(false);
  const [oemSearching, setOemSearching] = useState(false);
  const [oemSelectedModel, setOemSelectedModel] = useState<OEMSearchResult | null>(null);
  const [vehicleIdentification, setVehicleIdentification] = useState<IdentifyVehicleResponse | null>(null);
  const [identifying, setIdentifying] = useState(false);

  const oemSearchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!oemSearchQuery.trim() || oemSelectedModel) {
      setOemSearchResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setOemSearching(true);
      try {
        const data = await apiGet<OEMSearchResponse>(
          `/oem/search?model=${encodeURIComponent(oemSearchQuery.trim())}&limit=8`
        );
        setOemSearchResults(data.models);
        setOemSearchOpen(data.models.length > 0);
      } catch {
        setOemSearchResults([]);
      } finally {
        setOemSearching(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [oemSearchQuery, oemSelectedModel]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (oemSearchRef.current && !oemSearchRef.current.contains(e.target as Node)) {
        setOemSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (jobId) {
      localStorage.setItem(JOB_ID_STORAGE_KEY, jobId);
    }
  }, [jobId]);

  useEffect(() => {
    const stored = localStorage.getItem(JOB_ID_STORAGE_KEY);
    const urlParams = new URLSearchParams(window.location.search);
    const paramJobId = urlParams.get("job_id");

    const recoveredId = paramJobId || stored;
    if (recoveredId && !jobId && !intakeId) {
      setJobId(recoveredId);
    }
  }, []);

  const handleClearJob = useCallback(() => {
    localStorage.removeItem(JOB_ID_STORAGE_KEY);
    setJobId(null);
  }, []);

  const handleFileSelect = useCallback(
    (slotKey: SlotKey, file: File) => {
      setFiles((prev) => ({ ...prev, [slotKey]: file }));
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviews((prev) => ({
          ...prev,
          [slotKey]: (e.target?.result as string) ?? null,
        }));
      };
      reader.readAsDataURL(file);
    },
    []
  );

  const buildFormData = useCallback(() => {
    const formData = new FormData();
    formData.append("workshop_id", "demo-workshop");
    if (oemSelectedModel) {
      formData.append("oem_model_id", oemSelectedModel.id);
    }
    for (const slot of SLOTS) {
      const file = files[slot.key];
      if (file) {
        formData.append(slot.key, file);
      }
    }
    return formData;
  }, [files, oemSelectedModel]);

  const [concurrentBlocking, setConcurrentBlocking] = useState<{
    existing_job_id: string;
    existing_intake_id: string;
  } | null>(null);

  interface DemoVehicle {
    index: number;
    name: string;
    vehicle_type: string;
    description: string;
  }
  const [demoList, setDemoList] = useState<DemoVehicle[] | null>(null);
  const [demoListLoading, setDemoListLoading] = useState(false);
  const [demoLaunching, setDemoLaunching] = useState<number | null>(null);

  const fetchDemoList = useCallback(async () => {
    setDemoListLoading(true);
    try {
      const data = await apiGet<{ vehicles: DemoVehicle[] }>("/demo/list");
      setDemoList(data.vehicles);
    } catch {
      setDemoList(null);
    } finally {
      setDemoListLoading(false);
    }
  }, []);

  const launchDemo = useCallback(async (index: number) => {
    setDemoLaunching(index);
    setUploadError(null);
    try {
      const data = await apiPost<{ job_id: string }>(`/demo/${index}`);
      setJobId(data.job_id);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Unknown error"
      );
    } finally {
      setDemoLaunching(null);
    }
  }, []);

  const handleAnalyzeTrigger = useCallback(
    async (targetIntakeId: string) => {
      setUploading(true);
      setUploadError(null);
      setConcurrentBlocking(null);

      try {
        const key = await ensureApiKey();
        const h: Record<string, string> = {};
        if (key) h["X-API-Key"] = key;
        const res = await fetch(
          `http://localhost:8000/api/v1/intake/${targetIntakeId}/analyze`,
          { method: "POST", headers: h }
        );

        if (res.status === 409) {
          const errBody = await res.json();
          const detail = errBody.detail || errBody;
          setConcurrentBlocking({
            existing_job_id: detail.existing_job_id || "unknown",
            existing_intake_id: detail.existing_intake_id || intakeId || "unknown",
          });
          setUploading(false);
          return;
        }

        if (!res.ok) {
          const errBody = await res.text();
          throw new Error(
            `Analysis trigger failed (${res.status}): ${errBody}`
          );
        }
        const analyzeData = await res.json();
        setJobId(analyzeData.job_id);
      } catch (err) {
        setUploadError(
          err instanceof Error ? err.message : "Unknown error"
        );
      } finally {
        setUploading(false);
      }
    },
    []
  );

  const handleCancelAndRestart = useCallback(async () => {
    if (!intakeId) return;
    setUploading(true);
    try {
      const h: Record<string, string> = {};
      const key = await ensureApiKey();
      if (key) h["X-API-Key"] = key;
      const cancelTarget = concurrentBlocking
        ? concurrentBlocking.existing_intake_id
        : intakeId;
      await fetch(
        `http://localhost:8000/api/v1/intake/${cancelTarget}/cancel-analysis`,
        { method: "POST", headers: h }
      );
      setConcurrentBlocking(null);
      await handleAnalyzeTrigger(intakeId);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Cancel failed"
      );
    } finally {
      setUploading(false);
    }
  }, [intakeId, handleAnalyzeTrigger, concurrentBlocking]);

  const selectOemModel = useCallback((model: OEMSearchResult | null) => {
    setOemSelectedModel(model);
    if (intakeId) {
      apiPost(`/intake/${intakeId}/oem-model`, { oem_model_id: model?.id ?? null }).catch(() => {});
    }
  }, [intakeId]);

  const handleStartAnalysis = async () => {
    setUploading(true);
    setUploadError(null);

    try {
      const h: Record<string, string> = {};
      const key = await ensureApiKey();
      if (key) h["X-API-Key"] = key;
      const res = await fetch("http://localhost:8000/api/v1/intake", {
        method: "POST",
        headers: h,
        body: buildFormData(),
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Upload failed (${res.status}): ${errBody}`);
      }
      const intakeData = await res.json();
      setIntakeId(intakeData.intake_id);

      apiPost<IdentifyVehicleResponse>(`/intake/${intakeData.intake_id}/identify-vehicle`).then((idData) => {
        setVehicleIdentification(idData);
        if (idData.suggestions.length === 1 && !oemSelectedModel) {
          selectOemModel(idData.suggestions[0]);
        }
      }).catch(() => {});

      const newSlotInfo = { ...slotInfo };
      for (const slot of SLOTS) {
        if (files[slot.key]) {
          newSlotInfo[slot.key] = {
            attempt: intakeData.attempts?.[slot.key] ?? 0,
            blurry: intakeData.low_quality_views?.includes(slot.key) ?? false,
            occluded: intakeData.occluded_views?.includes(slot.key) ?? false,
            filePath: intakeData.intake_id,
          };
        }
      }
      setSlotInfo(newSlotInfo);

      if (
        intakeData.missing_views &&
        intakeData.missing_views.length > 0
      ) {
        setShowRecovery(true);
        setRecoveryData({
          missingViews: intakeData.missing_views,
          lowQualityViews: intakeData.low_quality_views || [],
          swapSuspected: intakeData.swap_suspected || false,
        });
        setUploading(false);
        return;
      }

      await handleAnalyzeTrigger(intakeData.intake_id);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Unknown error"
      );
    } finally {
      setUploading(false);
    }
  };

  const handleContinueLimited = async () => {
    if (!intakeId) return;
    setShowRecovery(false);
    await handleAnalyzeTrigger(intakeId);
  };

  const handleReupload = async (slotKey: SlotKey, file: File) => {
    if (!intakeId) return;
    setReuploadingSlot(slotKey);

    try {
      const h: Record<string, string> = {};
      const key = await ensureApiKey();
      if (key) h["X-API-Key"] = key;
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(
        `http://localhost:8000/api/v1/intake/${intakeId}/views/${slotKey}`,
        { method: "PUT", headers: h, body: formData }
      );

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Re-upload failed (${res.status}): ${errBody}`);
      }

      const data = await res.json();

      setSlotInfo((prev) => ({
        ...prev,
        [slotKey]: {
        attempt: data.attempt ?? 0,
        blurry: data.blurry ?? false,
        occluded: data.occluded ?? false,
        filePath: intakeId,
        },
      }));

      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviews((prev) => ({
          ...prev,
          [slotKey]: (e.target?.result as string) ?? null,
        }));
      };
      reader.readAsDataURL(file);

      if (data.status === "failed") {
        setUploadError(
          data.failure_reason || "View upload failed"
        );
      }

      if (data.swap_suspected || false) {
        setRecoveryData((prev) =>
          prev
            ? { ...prev, swapSuspected: true }
            : {
                missingViews: data.missing_views || [],
                lowQualityViews: data.low_quality_views || [],
                swapSuspected: true,
              }
        );
      }

      if (data.missing_views && data.missing_views.length > 0) {
        setShowRecovery(true);
        setRecoveryData((prev) => ({
          missingViews: data.missing_views,
          lowQualityViews: data.low_quality_views || [],
          swapSuspected: data.swap_suspected || false,
        }));
      } else {
        setShowRecovery(false);
      }
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Unknown error"
      );
    } finally {
      setReuploadingSlot(null);
    }
  };

  const handleSwapNow = async () => {
    if (!intakeId) return;
    try {
      const h: Record<string, string> = {};
      const key = getApiKey();
      if (key) h["X-API-Key"] = key;
      await fetch(`http://localhost:8000/api/v1/intake/${intakeId}/swap-views`, {
        method: "POST",
        headers: h,
      });
      setRecoveryData((prev) =>
        prev ? { ...prev, swapSuspected: false } : prev
      );
    } catch {
      // Swallow — the user can retry if needed
    }
  };

  const handleKeepAsIs = () => {
    setRecoveryData((prev) =>
      prev ? { ...prev, swapSuspected: false } : prev
    );
  };

  const handleReuploadFromDialog = () => {
    setShowRecovery(false);
  };

  const handleReset = () => {
    setFiles({} as Record<SlotKey, File | null>);
    setPreviews({} as Record<SlotKey, string | null>);
    setSlotInfo({} as Record<SlotKey, SlotUploadInfo>);
    setIntakeId(null);
    setJobId(null);
    setUploadError(null);
    setShowRecovery(false);
    setRecoveryData(null);
    setConcurrentBlocking(null);
    setOemSearchQuery("");
    setOemSearchResults([]);
    setOemSelectedModel(null);
    setOemSearchOpen(false);
    setVehicleIdentification(null);
    localStorage.removeItem(JOB_ID_STORAGE_KEY);
  };

  const isLoading =
    uploading || (jobId !== null && !jobState?.result);
  const isComplete =
    jobState?.result !== null && jobState?.result !== undefined;

  return (
    <div className="flex flex-1 flex-col items-center px-4 py-12">
      <div className="w-full max-w-4xl">
        <div className="mb-8 text-center animate-fade-in">
          <h1 className="text-3xl font-bold tracking-tight text-text-primary">
            New Retrofit Assessment
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            Upload vehicle imagery to begin the assessment pipeline
          </p>
        </div>

        {!isLoading && !isComplete && (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {SLOTS.map((slot) => {
                const info = slotInfo[slot.key] || INITIAL_SLOT_INFO;
                const isDisabled =
                  uploading ||
                  (slot.required && info.attempt >= MAX_ATTEMPTS) ||
                  reuploadingSlot === slot.key;
                return (
                  <UploadSlot
                    key={slot.key}
                    slot={slot}
                    preview={previews[slot.key] ?? null}
                    slotInfo={info}
                    disabled={isDisabled}
                    onSelect={(file) => {
                      if (intakeId) {
                        handleReupload(slot.key, file);
                      } else {
                        handleFileSelect(slot.key, file);
                      }
                    }}
                  />
                );
              })}
            </div>

            {showRecovery && recoveryData && !jobId && (
              <MissingViewRecoveryDialog
                missingViews={recoveryData.missingViews}
                lowQualityViews={recoveryData.lowQualityViews}
                swapSuspected={recoveryData.swapSuspected}
                onUploadNow={handleReuploadFromDialog}
                onContinueLimited={handleContinueLimited}
                onSwapNow={handleSwapNow}
                onKeepAsIs={handleKeepAsIs}
              />
            )}

            {uploadError && (
              <div className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-200">
                {uploadError}
              </div>
            )}

            {concurrentBlocking && (
              <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm dark:border-amber-700 dark:bg-amber-950">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    <svg className="h-5 w-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                      Assessment already in progress
                    </p>
                    <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
                      An assessment is already running for this workshop. You can view its progress or cancel it and start a new one.
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setJobId(concurrentBlocking.existing_job_id);
                          setIntakeId(null);
                          setFiles({} as Record<SlotKey, File | null>);
                          setPreviews({} as Record<SlotKey, string | null>);
                          setSlotInfo({} as Record<SlotKey, SlotUploadInfo>);
                          setConcurrentBlocking(null);
                        }}
                        className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50 transition-colors dark:border-amber-700 dark:bg-amber-900 dark:text-amber-200 dark:hover:bg-amber-800"
                      >
                        View Current
                      </button>
                      <button
                        type="button"
                        onClick={async () => {
                          setUploading(true);
                          try {
                            const h: Record<string, string> = {};
                            const key = await ensureApiKey();
                            if (key) h["X-API-Key"] = key;
                            await fetch(
                              `http://localhost:8000/api/v1/intake/${concurrentBlocking.existing_intake_id}/cancel-analysis`,
                              { method: "POST", headers: h }
                            );
                            setConcurrentBlocking(null);
                            await handleAnalyzeTrigger(intakeId!);
                          } catch (err) {
                            setUploadError(
                              err instanceof Error ? err.message : "Cancel failed"
                            );
                          } finally {
                            setUploading(false);
                          }
                        }}
                        disabled={uploading}
                        className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50 transition-colors dark:bg-amber-600 dark:hover:bg-amber-500"
                      >
                        {uploading ? "Cancelling…" : "Cancel & Start New"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {vehicleIdentification && !oemSelectedModel && vehicleIdentification.suggestions.length > 0 && (
              <div className="mt-4 rounded-xl border border-brand/20 bg-brand/5 p-4">
                <div className="flex items-start gap-3">
                  <span className="mt-0.5 shrink-0 text-brand text-lg">🔍</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-primary">
                      Detected vehicle type:{" "}
                      <span className="text-brand">{vehicleIdentification.classification.vehicle_type.replace(/_/g, " ")}</span>
                      <span className="ml-1.5 text-xs text-text-tertiary">
                        ({(vehicleIdentification.classification.confidence * 100).toFixed(0)}% confidence)
                      </span>
                    </p>
                    <p className="mb-2 mt-0.5 text-xs text-text-secondary">
                      Did you mean one of these? Selecting the correct model improves accuracy.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {vehicleIdentification.suggestions.map((s) => (
                        <button
                          key={s.id}
                          type="button"
                          onClick={() => selectOemModel(s)}
                          className="rounded-lg border border-border bg-surface-card px-3 py-1.5 text-left text-xs hover:bg-surface-hover hover:border-brand/40 transition-colors"
                        >
                          <span className="font-medium text-text-primary">{s.manufacturer_name}</span>{" "}
                          <span className="text-text-secondary">{s.model_name}</span>
                          {s.year_start && (
                            <span className="ml-1 text-text-tertiary">· {s.year_start}</span>
                          )}
                        </button>
                      ))}
                      <button
                        type="button"
                        onClick={() => setVehicleIdentification(null)}
                        className="rounded-lg border border-border px-3 py-1.5 text-xs text-text-tertiary hover:text-text-secondary hover:border-zinc-300 transition-colors"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={oemSearchRef} className="mt-6">
              <label className="mb-1.5 block text-xs font-semibold text-text-secondary">
                Vehicle Make / Model <span className="font-normal text-text-tertiary">(optional — improves accuracy)</span>
              </label>
              {oemSelectedModel ? (
                <div className="flex items-center gap-2 rounded-xl border border-border bg-surface-card px-4 py-2.5">
                  <span className="flex-1 text-sm text-text-primary">
                    {oemSelectedModel.manufacturer_name} {oemSelectedModel.model_name}
                    {oemSelectedModel.generation ? ` (${oemSelectedModel.generation})` : ""}
                    {oemSelectedModel.year_start ? ` · ${oemSelectedModel.year_start}${oemSelectedModel.year_end ? `-${oemSelectedModel.year_end}` : ""}` : ""}
                  </span>
                  <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium uppercase text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                    {oemSelectedModel.vehicle_type.replace(/_/g, " ")}
                  </span>
                  <button
                    type="button"
                    onClick={() => { selectOemModel(null); setOemSearchQuery(""); }}
                    className="text-xs text-text-tertiary underline underline-offset-2 hover:text-text-primary transition-colors"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <input
                    type="text"
                    value={oemSearchQuery}
                    onChange={(e) => setOemSearchQuery(e.target.value)}
                    placeholder="Search by model name (e.g., Super XL, Alto, Activa)..."
                    className="w-full rounded-xl border border-border bg-surface-card px-4 py-2.5 text-sm text-text-primary placeholder:text-text-tertiary outline-none focus:border-brand focus:ring-1 focus:ring-brand transition-colors"
                  />
                  {oemSearching && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2">
                      <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-zinc-300 border-t-brand" />
                    </span>
                  )}
                  {oemSearchOpen && oemSearchResults.length > 0 && (
                    <div className="absolute z-20 mt-1 w-full rounded-xl border border-border bg-surface-card py-1 shadow-lg">
                      {oemSearchResults.map((r) => (
                        <button
                          key={r.id}
                          type="button"
                          onClick={() => {
                            selectOemModel(r);
                            setOemSearchOpen(false);
                            setOemSearchQuery("");
                          }}
                          className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm hover:bg-surface-hover transition-colors"
                        >
                          <span className="flex-1 text-text-primary">
                            <span className="font-medium">{r.manufacturer_name}</span>{" "}
                            {r.model_name}
                            {r.generation ? ` (${r.generation})` : ""}
                          </span>
                          <span className="text-[10px] text-text-tertiary">
                            {r.vehicle_type.replace(/_/g, " ")}
                          </span>
                          {r.year_start && (
                            <span className="text-[10px] text-text-tertiary">
                              {r.year_start}{r.year_end ? `-${r.year_end}` : ""}
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {!intakeId && (
              <>
                <div className="mt-10">
                  <div className="mb-3 flex items-center gap-3">
                    <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
                    <span className="text-xs font-medium text-zinc-400">or</span>
                    <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-700" />
                  </div>

                  <h3 className="mb-3 text-center text-sm font-semibold text-zinc-500 dark:text-zinc-400">
                    Load Demo Vehicle
                  </h3>

                  {!demoList && !demoListLoading && (
                    <div className="flex justify-center">
                      <button
                        type="button"
                        onClick={fetchDemoList}
                        className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-card px-6 py-2 text-xs font-medium text-text-secondary hover:bg-surface-hover transition-colors"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Show Demo Vehicles
                      </button>
                    </div>
                  )}

                  {demoListLoading && (
                    <p className="text-center text-xs text-zinc-400">Loading...</p>
                  )}

                  {demoList && demoList.length > 0 && (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                      {demoList.map((v) => (
                        <button
                          key={v.index}
                          type="button"
                          disabled={demoLaunching === v.index}
                          onClick={() => launchDemo(v.index)}
                          className={`rounded-xl border-2 p-4 text-left transition-all ${
                            demoLaunching === v.index
                              ? "cursor-wait border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950"
                              : "border-zinc-200 bg-white hover:border-zinc-400 hover:shadow-sm dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-500"
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                              {v.name}
                            </span>
                            <span className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium uppercase text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
                              {v.vehicle_type.replace(/_/g, " ")}
                            </span>
                          </div>
                          <p className="mt-1 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
                            {v.description}
                          </p>
                          {demoLaunching === v.index && (
                            <span className="mt-2 inline-block text-xs font-medium text-blue-600 dark:text-blue-400">
                              Loading...
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="mt-8 flex justify-center">
                  <button
                    type="button"
                    disabled={!allRequiredFilled || uploading}
                    onClick={handleStartAnalysis}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-8 py-3 text-sm font-medium text-white transition-all duration-150 hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40 shadow-sm"
                  >
                    {uploading ? (
                      <>
                        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Uploading...
                      </>
                    ) : "Start Analysis"}
                  </button>
                </div>
              </>
            )}

              {intakeId && !showRecovery && !jobId && (
                <div className="mt-8 flex justify-center">
                  <button
                    type="button"
                    disabled={uploading}
                    onClick={handleContinueLimited}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-8 py-3 text-sm font-medium text-white transition-all duration-150 hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40 shadow-sm"
                  >
                    {uploading ? (
                      <>
                        <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Starting...
                      </>
                    ) : "Start Analysis"}
                  </button>
                </div>
              )}
          </>
        )}

        {(isLoading || isComplete) && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-text-primary">
                    Assessment Progress
                  </h2>
                  {!isComplete && (
                    <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-border border-t-brand" />
                  )}
                </div>
                <button
                  type="button"
                  onClick={handleReset}
                  className="text-xs text-text-tertiary underline underline-offset-2 hover:text-text-primary transition-colors"
                >
                  New Assessment
                </button>
              </div>

            {jobState && !isComplete && (
              <>
                <div className="h-2 w-full rounded-full bg-zinc-200 dark:bg-zinc-700">
                  <div
                    className="h-2 rounded-full bg-blue-500 transition-all duration-500"
                    style={{ width: `${jobState.progress_pct}%` }}
                  />
                </div>
                <p className="text-center text-sm font-medium text-zinc-600 dark:text-zinc-400">
                  {STAGE_LABELS[jobState.current_stage ?? ""] ??
                    (jobState.current_stage
                      ? `Processing: ${jobState.current_stage.replace(/_/g, " ")}`
                      : "Initializing...")}
                </p>
                {softTimedOut && (
                  <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 text-sm dark:border-yellow-700 dark:bg-yellow-950">
                    <p className="font-medium text-yellow-800 dark:text-yellow-200">
                      Analysis is taking longer than expected
                    </p>
                    <p className="mt-1 text-yellow-700 dark:text-yellow-300">
                      Continuing in the background. You can wait or check back
                      later.
                    </p>
                  </div>
                )}
              </>
            )}

            {jobState && jobState.completed_stages.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {jobState.completed_stages.map((stage) => (
                  <span
                    key={stage}
                    className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900 dark:text-green-200"
                  >
                    {STAGE_LABELS[stage] ? "✓ " : ""}
                    {STAGE_LABELS[stage]?.replace("...", "") ?? stage.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            )}

            {jobState && !isComplete && jobState.current_stage && (
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-200">
                  {STAGE_LABELS[jobState.current_stage] ??
                    `Processing: ${jobState.current_stage.replace(/_/g, " ")}`}
                </span>
              </div>
            )}

            {pollError && (
              <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-3 text-sm text-yellow-700 dark:border-yellow-700 dark:bg-yellow-950 dark:text-yellow-200">
                Poll error: {pollError}
              </div>
            )}

            {isComplete && assessment && jobId && (
              <AssessmentResult
                assessment={assessment}
                jobId={jobId}
                onConfirm={handleConfirm}
              />
            )}
          </div>
        )}
      </div>

      <OnboardingGuide />
      <HelpBubble />
    </div>
  );
}
