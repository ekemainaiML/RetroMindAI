"use client";

interface Props {
  severity: "low" | "medium" | "high" | "critical";
  label?: string;
  tooltip?: string;
}

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-zinc-100 text-zinc-700 border-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-600",
  medium:
    "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900 dark:text-yellow-200 dark:border-yellow-700",
  high: "bg-orange-100 text-orange-800 border-orange-300 dark:bg-orange-900 dark:text-orange-200 dark:border-orange-700",
  critical:
    "bg-red-100 text-red-800 border-red-300 dark:bg-red-900 dark:text-red-200 dark:border-red-700",
};

const DEFAULT_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

const DOT_COLORS: Record<string, string> = {
  low: "bg-zinc-400 dark:bg-zinc-500",
  medium: "bg-yellow-500 dark:bg-yellow-400",
  high: "bg-orange-500 dark:bg-orange-400",
  critical: "bg-red-500 dark:bg-red-400",
};

export default function RiskBadge({
  severity,
  label,
  tooltip,
}: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium ${SEVERITY_STYLES[severity]}`}
      title={tooltip}
    >
      <span
        className={`inline-block h-1.5 w-1.5 rounded-full ${DOT_COLORS[severity]}`}
      />
      {label ?? DEFAULT_LABELS[severity]}
    </span>
  );
}
