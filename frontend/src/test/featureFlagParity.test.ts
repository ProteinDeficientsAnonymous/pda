import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { Feature } from '@/models/featureFlags';

const CHOICES = join(__dirname, '../../..', 'backend/community/models/choices.py');

// Extract the string values of the backend `FeatureFlag(models.TextChoices)`
// members, e.g. `HOST_ATTENDANCE_REPORT = "host_attendance_report", "..."` → `host_attendance_report`.
function backendFlagKeys(): Set<string> {
  const source = readFileSync(CHOICES, 'utf8');
  const classMatch = /class FeatureFlag\(models\.TextChoices\):([\s\S]*?)(?:\n\S|$)/.exec(source);
  if (!classMatch) throw new Error('FeatureFlag class not found in choices.py');
  const memberRe = /^\s+[A-Z0-9_]+\s*=\s*"([^"]+)"/;
  const keys = new Set<string>();
  for (const line of (classMatch[1] ?? '').split('\n')) {
    const m = memberRe.exec(line);
    if (m?.[1]) keys.add(m[1]);
  }
  return keys;
}

describe('feature flag registry parity', () => {
  it('backend FeatureFlag keys match the frontend Feature mirror exactly', () => {
    const backend = backendFlagKeys();
    const frontend = new Set<string>(Object.values(Feature));
    expect([...frontend].sort()).toEqual([...backend].sort());
  });
});
