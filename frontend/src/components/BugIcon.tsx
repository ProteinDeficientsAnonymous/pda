export function BugIcon({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      data-testid="bug-icon"
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <g transform="rotate(35 12 12)">
        <path d="M10.6 4.6C10 3.2 9 2.5 7.8 2.4" />
        <path d="M13.4 4.6c.6-1.4 1.6-2.1 2.8-2.2" />
        <path d="M9.6 7.9a2.4 2.4 0 1 1 4.8 0z" />
        <ellipse cx="12" cy="14.2" rx="5.4" ry="6.3" />
        <path d="M12 7.9v12.6" />
        <path d="M7.1 11.2 4.4 9.6" />
        <path d="M6.6 14.2H3.6" />
        <path d="M7.1 17.2l-2.7 1.6" />
        <path d="m16.9 11.2 2.7-1.6" />
        <path d="M17.4 14.2h3" />
        <path d="m16.9 17.2 2.7 1.6" />
        <g fill="currentColor" stroke="none">
          <circle cx="9.7" cy="12.3" r="0.7" />
          <circle cx="14.3" cy="12.3" r="0.7" />
          <circle cx="9.9" cy="16.5" r="0.7" />
          <circle cx="14.1" cy="16.5" r="0.7" />
        </g>
      </g>
    </svg>
  );
}
