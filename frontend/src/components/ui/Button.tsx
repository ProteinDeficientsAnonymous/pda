import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

type Variant = 'primary' | 'secondary' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  fullWidth?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-600 text-brand-on hover:bg-brand-700 disabled:bg-toggle-off',
  secondary:
    'bg-surface text-foreground border border-border-strong hover:bg-background disabled:opacity-50',
  ghost: 'text-foreground-secondary hover:bg-surface-dim disabled:opacity-50',
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
