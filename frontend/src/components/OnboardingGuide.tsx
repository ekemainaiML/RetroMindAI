"use client";

import { useCallback, useEffect, useState } from "react";

const SEEN_KEY = "retromind_onboarding_seen_v2";

const STEPS = [
  {
    num: 1,
    title: "Upload Photos",
    description:
      "Capture 4–6 views of the vehicle (left/right profile, front/rear, engine bay, underbody). The system validates image quality automatically.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.16a15.53 15.53 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z" />
      </svg>
    ),
  },
  {
    num: 2,
    title: "Vehicle Classification",
    description:
      "AI classifies the vehicle type (three-wheeler, four-wheeler, or motorcycle) using computer vision. Review and confirm the result.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" />
      </svg>
    ),
  },
  {
    num: 3,
    title: "Deviation Analysis",
    description:
      "AI measures key geometry parameters and detects deviations from reference standards. Identifies salvage potential and critical issues.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
      </svg>
    ),
  },
  {
    num: 4,
    title: "Battery & Wiring Optimization",
    description:
      "Spatial constraint solver selects optimal battery zones and wiring routes based on vehicle geometry and detected deviations.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    ),
  },
  {
    num: 5,
    title: "Compliance Report",
    description:
      "Get a 13-section compliance report with feasibility score, risk register, recommendations, and knowledge graph connections.",
    icon: (
      <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
      </svg>
    ),
  },
];

interface Props {
  open?: boolean;
  onDismiss?: () => void;
}

export default function OnboardingGuide({ open: externalOpen, onDismiss: externalDismiss }: Props = {}) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [dismissed, setDismissed] = useState(true);

  const isControlled = externalOpen !== undefined;

  useEffect(() => {
    if (isControlled) return;
    const seen = localStorage.getItem(SEEN_KEY);
    if (!seen) {
      setInternalOpen(true);
      setDismissed(false);
    }
  }, [isControlled]);

  const handleDismiss = useCallback(() => {
    if (isControlled && externalDismiss) {
      externalDismiss();
      return;
    }
    localStorage.setItem(SEEN_KEY, "1");
    setInternalOpen(false);
    setDismissed(true);
  }, [isControlled, externalDismiss]);

  const open = isControlled ? externalOpen : internalOpen;
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-xl border border-zinc-200 bg-white p-6 shadow-xl dark:border-zinc-700 dark:bg-zinc-950">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
            Welcome to RetroMind AI
          </h2>
          <button
            type="button"
            onClick={handleDismiss}
            className="rounded-md p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mb-5 text-xs text-zinc-500">
          This guided workflow helps workshops assess structural suitability for EV
          retrofits. Complete the steps below to generate a compliance report.
        </p>

        <div className="space-y-3">
          {STEPS.map((step) => (
            <div
              key={step.num}
              className="flex gap-3 rounded-lg border border-zinc-100 p-3 dark:border-zinc-800"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-[11px] font-bold text-white dark:bg-zinc-100 dark:text-zinc-900">
                {step.num}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-zinc-500 dark:text-zinc-400">{step.icon}</span>
                  <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                    {step.title}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-zinc-100 pt-4 dark:border-zinc-800">
          <p className="text-[10px] text-zinc-400">
            You can reopen this guide anytime from the help menu.
          </p>
          <button
            type="button"
            onClick={handleDismiss}
            className="rounded-lg bg-zinc-900 px-5 py-2 text-xs font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Get Started
          </button>
        </div>
      </div>
    </div>
  );
}
