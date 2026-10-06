import { describe, expect, it } from 'vitest';

import { duplicateShotNames } from './shot-names.mjs';

describe('duplicateShotNames', () => {
  it('reports a name used in two files', () => {
    expect(
      duplicateShotNames([
        { path: 'a.spec.ts', source: "shot(page, 'login')" },
        { path: 'b.spec.ts', source: "shot(page, 'login')" },
      ]),
    ).toEqual(['duplicate shot name "login" in a.spec.ts and b.spec.ts']);
  });
});
