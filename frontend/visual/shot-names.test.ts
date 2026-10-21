import { describe, expect, it } from 'vitest';

import { duplicateShotNames } from './shot-names.mjs';

describe('duplicateShotNames', () => {
  it('reports a screen name that repeats a shot name', () => {
    expect(
      duplicateShotNames([
        { path: 'a.spec.ts', source: "screen('home', '/')" },
        { path: 'b.spec.ts', source: "shot(page, 'home')" },
      ]),
    ).toEqual(['duplicate shot name "home" in a.spec.ts and b.spec.ts']);
  });

  it('reports a name used in two files', () => {
    expect(
      duplicateShotNames([
        { path: 'a.spec.ts', source: "shot(page, 'login')" },
        { path: 'b.spec.ts', source: "shot(page, 'login')" },
      ]),
    ).toEqual(['duplicate shot name "login" in a.spec.ts and b.spec.ts']);
  });
});
