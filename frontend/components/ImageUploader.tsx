"use client";

import { useRef, useState } from "react";

interface ImageUploaderProps {
  onFileSelect: (file: File) => void;
  onClear: () => void;
  previewUrl?: string | null;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png"];
const MAX_SIZE_MB = 10;

export function ImageUploader({ onFileSelect, onClear, previewUrl, disabled }: ImageUploaderProps) {
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) return "Please upload a PNG or JPG image.";
    if (file.size > MAX_SIZE_MB * 1024 * 1024) return `Image must be under ${MAX_SIZE_MB} MB.`;
    return null;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const file = e.target.files?.[0];
    if (!file) return;
    const err = validate(file);
    if (err) { setError(err); return; }
    onFileSelect(file);
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const err = validate(file);
    if (err) { setError(err); return; }
    onFileSelect(file);
  };

  return (
    <div className="w-full flex flex-col gap-2">
      {/* Label */}
      <div className="flex items-center justify-between">
        <h3 className="section-label">CHART / GRAPH</h3>
        {previewUrl && (
          <button
            onClick={onClear}
            disabled={disabled}
            className="text-[11px] text-[#EF4444] hover:text-red-300 transition-colors font-medium"
          >
            Remove image
          </button>
        )}
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && !previewUrl && inputRef.current?.click()}
        className={`relative rounded-lg border-2 border-dashed overflow-hidden transition-all duration-200 flex items-center justify-center
          ${previewUrl ? "min-h-[260px] cursor-default" : "min-h-[180px] cursor-pointer"}
          ${dragging ? "border-[#3B82F6] bg-blue-500/5 scale-[1.01]" : "border-white/10 hover:border-white/20"}
          ${disabled ? "opacity-60 pointer-events-none" : ""}
          bg-[#1E1E1E]
        `}
        style={{ minHeight: previewUrl ? "260px" : "180px" }}
      >
        {previewUrl ? (
          <>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Chart preview"
              className="w-full h-full object-contain p-3"
              style={{ maxHeight: "280px" }}
            />
            {/* Hover overlay */}
            <div className="absolute inset-0 bg-black/60 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
              <button
                onClick={(e) => { e.stopPropagation(); onClear(); }}
                disabled={disabled}
                className="px-4 py-2 text-xs font-semibold bg-red-600/80 hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                Remove
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
                disabled={disabled}
                className="px-4 py-2 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
              >
                Replace
              </button>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center gap-3 p-6 text-center select-none">
            {/* Upload icon */}
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center transition-colors ${dragging ? "bg-blue-500/20" : "bg-white/5"}`}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className={`transition-colors ${dragging ? "text-[#3B82F6]" : "text-[#525252]"}`}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div>
              <p className="text-sm font-medium text-[#D4D4D4]">
                {dragging ? "Drop it here!" : "Drop your chart or click to upload"}
              </p>
              <p className="text-xs text-[#525252] mt-1">PNG, JPG · up to {MAX_SIZE_MB} MB</p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-[#EF4444] flex items-center gap-1">
          <span>⚠</span> {error}
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFileChange}
        className="hidden"
        disabled={disabled}
      />
    </div>
  );
}
