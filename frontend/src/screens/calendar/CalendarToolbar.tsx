import type { ToolbarProps } from 'react-big-calendar';
import { cn } from '@/utils/cn';
import { TodayIconButton } from './TodayIconButton';
import type { BigCalEvent } from './types';

export function CalendarToolbar({ label, onNavigate }: ToolbarProps<BigCalEvent>) {
  return (
    <div className="mb-2 grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-1">
      <div className="justify-self-start">
        <TodayIconButton
          onClick={() => {
            onNavigate('TODAY');
          }}
        />
      </div>

      <div className="flex items-center gap-1 justify-self-center">
        <ChevronButton
          label="previous"
          onClick={() => {
            onNavigate('PREV');
          }}
        >
          <ChevronLeft />
        </ChevronButton>
        <span className="min-w-[9rem] text-center text-sm font-medium text-foreground">
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

      <span aria-hidden="true" />
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
