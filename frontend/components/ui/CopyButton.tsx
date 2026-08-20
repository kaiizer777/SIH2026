'use client';

import React, { useState } from 'react';

export interface CopyButtonProps {
  text: string;
  className?: string;
}

export function CopyButton({ text, className = '' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        if (typeof navigator !== 'undefined' && navigator.clipboard) {
          navigator.clipboard.writeText(text).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1400);
          });
        }
      }}
      className={`text-[10px] font-mono uppercase tracking-[0.18em] px-2.5 py-1 rounded-full border border-[#E6E8EE] bg-white text-[#5B6472] hover:text-[#2563EB] hover:border-[#2563EB] transition ${className}`}
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

export default CopyButton;
