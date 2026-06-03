"use client";

import { useState } from "react";
import type { ConfirmationRequired } from "@/types/assessment";

interface Props {
  confirmation: ConfirmationRequired;
  onConfirm: (selection: string) => Promise<void>;
  onDismiss?: () => void;
}

export default function ConfirmDialog({
  confirmation,
  onConfirm,
  onDismiss,
}: Props) {
  const [selection, setSelection] = useState(
    confirmation.current_value ?? confirmation.options?.[0] ?? ""
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await onConfirm(selection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirmation failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-700 dark:bg-zinc-900">
        <div className="mb-4 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900">
            <svg
              className="h-5 w-5 text-amber-600 dark:text-amber-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </span>
          <div>
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
              Confirmation Required
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {confirmation.message || `Review and confirm ${confirmation.type.replace(/_/g, " ")}`}
            </p>
          </div>
        </div>

        <div className="mb-4">
          <label className="mb-1.5 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
            {confirmation.type.replace(/_/g, " ")}
          </label>

          {confirmation.options && confirmation.options.length > 0 ? (
            <div className="space-y-1.5">
              {confirmation.options.map((opt) => (
                <label
                  key={opt}
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 transition-colors ${
                    selection === opt
                      ? "border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950"
                      : "border-zinc-200 bg-white hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600"
                  }`}
                >
                  <input
                    type="radio"
                    name="confirmation-selection"
                    value={opt}
                    checked={selection === opt}
                    onChange={(e) => setSelection(e.target.value)}
                    className="h-4 w-4 text-amber-500 focus:ring-amber-400"
                  />
                  <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {opt.replace(/_/g, " ")}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p className="rounded-lg bg-zinc-50 p-3 text-sm text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
              {confirmation.current_value?.replace(/_/g, " ") || "Unknown"}
            </p>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-xs text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              disabled={submitting}
              className="flex-1 rounded-lg border border-zinc-300 px-4 py-2.5 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-40 dark:border-zinc-600 dark:text-zinc-300 dark:hover:bg-zinc-800"
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={handleConfirm}
            disabled={submitting || !selection}
            className="flex-1 rounded-lg bg-amber-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? "Confirming..." : "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}
