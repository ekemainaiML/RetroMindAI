'use client';

import { useEffect, useRef } from 'react';
import QRCode from 'qrcode';

interface Props {
  url: string;
  label: string;
  onClose: () => void;
}

export default function QRCodeModal({ url, label, onClose }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (canvasRef.current) {
      QRCode.toCanvas(canvasRef.current, url, {
        width: 200,
        margin: 2,
        color: { dark: '#18181b', light: '#ffffff' },
      });
    }
  }, [url]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="rounded-xl bg-white p-6 shadow-2xl dark:bg-zinc-800">
        <canvas ref={canvasRef} className="mx-auto block" />
        <p className="mt-3 text-center text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {label}
        </p>
        <p className="mt-1 text-center text-[10px] text-zinc-400">
          Scan with your phone to view the 3D model
        </p>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-lg bg-zinc-200 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-600"
        >
          Close
        </button>
      </div>
    </div>
  );
}
