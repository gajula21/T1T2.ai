import React from 'react';

interface QuotaPipsProps {
  limit: number;
  remaining: number;
}

export function QuotaPips({ limit, remaining }: QuotaPipsProps) {
  const used = limit - remaining;
  
  return (
    <div className="flex gap-1.5 flex-wrap">
      {Array.from({ length: limit }).map((_, i) => (
        <div 
          key={i}
          className={`h-1.5 w-8 rounded-full ${i < used ? 'bg-[#EAB308]' : 'bg-neutral-800'}`}
        />
      ))}
    </div>
  );
}
