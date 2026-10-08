import type { AxeMatchers } from 'vitest-axe/matchers';

declare module 'vitest' {
  // oxlint-disable-next-line typescript/no-empty-object-type
  interface Assertion<_T = unknown> extends AxeMatchers {}
  // oxlint-disable-next-line typescript/no-empty-object-type
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}
