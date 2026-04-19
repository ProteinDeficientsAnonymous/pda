import type { ToolbarProps } from 'react-big-calendar';
import { cn } from '@/utils/cn';
import { TodayIconButton } from './TodayIconButton';
import type { BigCalEvent } from './types';

export function CalendarToolbar({ label, onNavigate }: ToolbarProps<BigCalEvent>) {
  return (
    <div className="relative mb-2 flex items-center px-1">
      <TodayIconButton
        onClick={() => {
          onNavigate('TODAY');
        }}
      />
      <div className="pointer-events-none absolute inset-x-0 flex items-center justify-center">
        <div className="pointer-events-auto flex items-center gap-1">
          <ChevronButton
            label="previous"
            onClick={() => {
              onNavigate('PREV');
            }}
          >
            <ChevronLeft />
          </ChevronButton>
          <span className="text-center text-sm font-medium text-foreground">
            {label.toLowerCase()}
          </span>
          <ChevronButton
            label="next"
            onClick={() => {
              onNavigate('NEXT');
            }}
          >
            <ChevronRight />
          </ChevronButton>
        </div>
      </div>
    </div>
  );
}

function ChevronButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-md text-foreground-tertiary',
        'hover:text-brand-700 hover:bg-surface-dim',
      )}
    >
      {children}
    </button>
  );
}

function ChevronLeft() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}
