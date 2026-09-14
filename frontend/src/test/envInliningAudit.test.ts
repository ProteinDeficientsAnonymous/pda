import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = join(__dirname, '..');

function* walk(dir: string): Generator<string> {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
      continue;
    }
    if (/\.tsx?$/.test(full) && !/\.test\.tsx?$/.test(full)) yield full;
  }
}

// Aliasing the object instead of a direct .KEY access inlines every VITE_* var
// into the bundle, secrets included.
const WHOLE_ENV_ACCESS = /import\.meta\.env(?!\s*\.\s*[A-Za-z_$])/g;

// Prose about this rule would otherwise trip it.
function stripComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

describe('import.meta.env inlining', () => {
  it('is never aliased or destructured as a whole object', () => {
    const violations: string[] = [];
    for (const file of walk(SRC)) {
      if (WHOLE_ENV_ACCESS.test(stripComments(readFileSync(file, 'utf8')))) {
        violations.push(relative(SRC, file));
      }
      WHOLE_ENV_ACCESS.lastIndex = 0;
    }
    expect(violations).toEqual([]);
  });
});
