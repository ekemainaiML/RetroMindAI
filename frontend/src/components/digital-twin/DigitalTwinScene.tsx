'use client';

import dynamic from 'next/dynamic';
import type { DigitalTwinData } from '@/types/assessment';

const SceneContent = dynamic(() => import('./DigitalTwinSceneContent'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[400px] items-center justify-center rounded-lg bg-zinc-100 dark:bg-zinc-800">
      <div className="flex flex-col items-center gap-2">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-300 border-t-blue-500" />
        <span className="text-xs text-zinc-400">Loading 3D scene...</span>
      </div>
    </div>
  ),
});

interface Props {
  twinData: DigitalTwinData;
  className?: string;
}

export default function DigitalTwinScene({ twinData, className = '' }: Props) {
  if (!twinData) {
    return (
      <div className={`flex h-[200px] items-center justify-center rounded-lg bg-zinc-50 dark:bg-zinc-800 ${className}`}>
        <p className="text-sm text-zinc-400 italic">No digital twin data available</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <SceneContent twinData={twinData} />
    </div>
  );
}
