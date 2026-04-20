import { z } from 'zod';

// Mirrors backend users/_password_validation.py — keep the two in sync when
// either side changes. Error strings are split up so the client shows one
// message at a time instead of a wall of requirements.
export const passwordRule = z
  .string()
  .min(12, 'at least 12 characters')
  .max(72, 'too long')
  .refine((v) => /[A-Z]/.test(v), 'must include an uppercase letter')
  .refine((v) => /\d/.test(v), 'must include a number')
  .refine((v) => /[^A-Za-z0-9]/.test(v), 'must include a special character');

export interface PasswordCheck {
  label: string;
  ok: boolean;
}

export function passwordChecks(value: string): PasswordCheck[] {
  return [
    { label: 'at least 12 characters', ok: value.length >= 12 },
    { label: 'an uppercase letter', ok: /[A-Z]/.test(value) },
    { label: 'a number', ok: /\d/.test(value) },
    { label: 'a special character', ok: /[^A-Za-z0-9]/.test(value) },
  ];
}
