"use client";

import { forwardRef, type InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string | null;
  helperText?: string;
};

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = "", id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-text-secondary">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`w-full rounded-lg border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary transition-colors
            focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand
            disabled:cursor-not-allowed disabled:opacity-40
            ${error ? "border-danger focus:ring-danger/30 focus:border-danger" : "border-border hover:border-border/80"}
            ${className}`}
          {...props}
        />
        {error && <p className="text-xs text-danger">{error}</p>}
        {!error && helperText && <p className="text-xs text-text-tertiary">{helperText}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
