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

// Vite only statically replaces direct `import.meta.env.KEY` member accesses.
// Aliasing or destructuring the object instead inlines EVERY VITE_* var present
// at build time into the shipped bundle — including credential-shaped ones like
// VITE_DEV_LOGIN_PASSWORD. Matches any `import.meta.env` NOT followed by `.key`.
const WHOLE_ENV_ACCESS = /import\.meta\.env(?!\s*\.\s*[A-Za-z_$])/g;

// Comments legitimately mention `import.meta.env` when explaining this very rule.
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
