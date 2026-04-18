import { z } from 'zod';

// Mirrors backend users/_password_validation.py — keep the two in sync when
// either side changes. Error strings are split up so the client shows one
// message at a time instead of a wall of requirements.
export const passwordRule = z
  .string()
  .min(8, 'at least 8 characters')
  .max(128, 'too long')
  .refine((v) => /[A-Za-z]/.test(v), 'must include at least one letter')
  .refine((v) => /\d/.test(v), 'must include at least one number');
