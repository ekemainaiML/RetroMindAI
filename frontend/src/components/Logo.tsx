import Link from "next/link";

export default function Logo({ showLabel = true, size = "sm" }: { showLabel?: boolean; size?: "sm" | "md" | "lg" }) {
  const iconSize = size === "sm" ? 7 : size === "md" ? 9 : 11;
  const textSize = size === "sm" ? "text-sm" : size === "md" ? "text-lg" : "text-2xl";

  return (
    <Link href="/" className="flex items-center gap-2.5 group">
      <div className={`relative flex h-${iconSize} w-${iconSize} items-center justify-center`}>
        <svg
          width={iconSize * 4}
          height={iconSize * 4}
          viewBox="0 0 28 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="shrink-0"
          style={{ width: iconSize * 4, height: iconSize * 4 }}
        >
          <circle cx="14" cy="14" r="13" className="stroke-brand" strokeWidth="1.5" />
          <circle cx="14" cy="14" r="8" className="fill-brand/10 stroke-brand" strokeWidth="1.2" />
          <path
            d="M14 6v16M6 14h16"
            className="stroke-brand"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <circle cx="14" cy="14" r="2.5" className="fill-accent" stroke="none" />
        </svg>
      </div>
      {showLabel && (
        <span className={`font-semibold tracking-tight text-text-primary ${textSize}`}>
          Retro<span className="text-accent">Mind</span>
          <span className="ml-1 font-mono text-[0.6em] font-normal text-text-tertiary">AI</span>
        </span>
      )}
    </Link>
  );
}
