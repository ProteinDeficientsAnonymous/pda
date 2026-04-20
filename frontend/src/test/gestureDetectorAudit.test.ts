// Codebase audit: no interactive handlers on non-semantic elements.
// Mirrors widgets/gesture_detector_audit_test.dart from the Flutter suite —
// enforces that tap handlers live on <button>/<a>, not on <div> or <span>.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, it, expect } from 'vitest';

const SRC = join(__dirname, '..');

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
      continue;
    }
    if (full.endsWith('.tsx') && !full.endsWith('.test.tsx')) {
      yield full;
    }
  }
}

const NON_SEMANTIC = ['div', 'span', 'li', 'p', 'section', 'article'];
const HANDLERS = ['onClick', 'onMouseDown', 'onPointerDown', 'onKeyDown'];

function findViolations(source: string): string[] {
  const violations: string[] = [];
  for (const tag of NON_SEMANTIC) {
    for (const handler of HANDLERS) {
      // Match opening tags like `<div ... onClick={...}` but not component
      // usage like `<MyDiv onClick={...}` (checked by lowercase tag name).
      const re = new RegExp(`<${tag}\\b[^>]*\\s${handler}=`, 'g');
      if (re.test(source)) {
        violations.push(`<${tag}> with ${handler}`);
      }
    }
  }
  return violations;
}

describe('gesture detector audit', () => {
  it('no <div>/<span>/etc carry onClick handlers (use <button> instead)', () => {
    const offending: { file: string; violations: string[] }[] = [];
    for (const file of walk(SRC)) {
      const source = readFileSync(file, 'utf8');
      const violations = findViolations(source);
      if (violations.length) {
        offending.push({ file: relative(SRC, file), violations });
      }
    }
    expect(offending).toEqual([]);
  });
});
