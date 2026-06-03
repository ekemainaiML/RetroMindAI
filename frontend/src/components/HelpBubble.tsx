"use client";

import { useState } from "react";
import OnboardingGuide from "./OnboardingGuide";

export default function HelpBubble() {
  const [showGuide, setShowGuide] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setShowGuide(true)}
        className="fixed bottom-4 right-4 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-zinc-800 text-white shadow-lg transition-transform hover:scale-105 active:scale-95 dark:bg-zinc-200 dark:text-zinc-900"
        title="Help & Guide"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
        </svg>
      </button>

      {showGuide && (
        <div
          className="fixed inset-0 z-50 cursor-pointer"
          onClick={() => setShowGuide(false)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <OnboardingGuide open onDismiss={() => setShowGuide(false)} />
          </div>
        </div>
      )}
    </>
  );
}
