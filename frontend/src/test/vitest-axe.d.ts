import type { AxeMatchers } from 'vitest-axe/matchers';

declare module 'vitest' {
  interface Assertion<_T = unknown> extends AxeMatchers {
    // Marker so this is not an empty interface under oxlint.
    _axeAssertion?: _T;
  }
  interface AsymmetricMatchersContaining extends AxeMatchers {
    _axeAsymmetric?: true;
  }
}
