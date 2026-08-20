import React from 'react';

export interface ChapterHeaderProps {
  num: string;
  title: string;
  subtitle?: string;
  className?: string;
  badgeColor?: string;
}

export function ChapterHeader({
  num,
  title,
  subtitle,
  className = '',
  badgeColor = '#2563EB',
}: ChapterHeaderProps) {
  const formattedNum = num.startsWith('Chapter ')
    ? num
    : isNaN(Number(num))
    ? num
    : `Chapter ${num}`;

  return (
    <div className={`pt-12 pb-6 first:pt-2 ${className}`}>
      <div className="flex items-baseline gap-3">
        <span
          className="text-[11px] font-mono uppercase tracking-[0.22em]"
          style={{ color: badgeColor }}
        >
          {formattedNum}
        </span>
        <span className="flex-1 h-px bg-[#E6E8EE]" />
      </div>
      <h2 className="mt-3 text-[24px] md:text-[30px] font-semibold tracking-[-0.02em] text-[#0B1220] leading-[1.15]">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-2 text-[14px] text-[#5B6472] max-w-2xl leading-relaxed">{subtitle}</p>
      )}
    </div>
  );
}

export default ChapterHeader;
