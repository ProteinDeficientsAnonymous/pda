import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

type Variant = 'primary' | 'secondary' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  fullWidth?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-neutral-400',
  secondary:
    'bg-white text-neutral-900 border border-neutral-300 hover:bg-neutral-50 disabled:opacity-50',
  ghost: 'text-neutral-700 hover:bg-neutral-100 disabled:opacity-50',
};

export function Button({
  variant = 'primary',
  fullWidth,
  className,
  type = 'button',
  ...rest
}: Props) {
  return (
    <button
      type={type}
      className={cn(
        'focus-visible:ring-brand-200 inline-flex h-10 items-center justify-center rounded-md px-4 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed',
        VARIANTS[variant],
        fullWidth && 'w-full',
        className,
      )}
      {...rest}
    />
  );
}
