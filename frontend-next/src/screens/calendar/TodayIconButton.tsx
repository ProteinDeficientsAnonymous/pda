// Calendar-icon "go to today" button — mirrors the Flutter calendar_nav_row
// design: an outlined calendar glyph with today's day-of-month overlaid inside.

interface Props {
  onClick: () => void;
}

export function TodayIconButton({ onClick }: Props) {
  const day = new Date().getDate();
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="go to today"
      title="go to today"
      className="text-brand-700 hover:bg-brand-50 relative inline-flex h-9 w-9 items-center justify-center rounded-md"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-7 w-7"
        aria-hidden="true"
      >
        <rect x="3" y="4" width="18" height="17" rx="2" />
        <path d="M3 9h18" />
        <path d="M8 2v4" />
        <path d="M16 2v4" />
      </svg>
      <span
        aria-hidden="true"
        className="absolute left-0 right-0 top-[55%] text-center text-[10px] font-bold leading-none"
      >
        {String(day)}
      </span>
    </button>
  );
}
