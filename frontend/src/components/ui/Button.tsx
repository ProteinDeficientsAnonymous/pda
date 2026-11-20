import type { ButtonHTMLAttributes } from 'react';

import { cn } from '@/utils/cn';

import { buttonClass, type ButtonVariant } from './buttonClass';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  fullWidth?: boolean;
}

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
      className={buttonClass(variant, cn(fullWidth && 'w-full', className))}
      {...rest}
    />
  );
}
