import '@testing-library/jest-dom/vitest';
import 'vitest-axe/extend-expect';

import { cleanup } from '@testing-library/react';
import { afterEach, expect } from 'vitest';
import * as axeMatchers from 'vitest-axe/matchers';

expect.extend(axeMatchers);

afterEach(() => {
  cleanup();
});

// jsdom doesn't implement ResizeObserver — provide a no-op stub so components
// that rely on it (e.g. WideWeekView's layout measurement, react-image-crop)
// render cleanly.
class ResizeObserverStub implements ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub;

// jsdom doesn't implement matchMedia — provide a minimal stub.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// jsdom doesn't implement HTMLCanvasElement.getContext — return null so
// jsdom stops emitting "Not implemented" warnings during component rendering.
// No test currently inspects canvas output.
HTMLCanvasElement.prototype.getContext = (() => null) as never;
