import { cn } from '@/utils/cn';

export function Chevron({ open, className }: { open: boolean; className?: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={cn('shrink-0 transition-transform duration-200', open && 'rotate-180', className)}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}
