import '@testing-library/jest-dom/vitest';
import 'vitest-axe/extend-expect';

import { cleanup } from '@testing-library/react';
import { afterEach, expect } from 'vitest';
import * as axeMatchers from 'vitest-axe/matchers';

import { setPhoneCountriesForTesting } from '@/components/ui/phoneCountries';

expect.extend(axeMatchers);

setPhoneCountriesForTesting(['US', 'CA', 'GB', 'AU']);

// jsdom's default Storage isn't wired up for get/set round-trips — stub a real one.
const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string): string | null => store[key] ?? null,
    setItem: (key: string, value: string): void => {
      store[key] = value;
    },
    removeItem: (key: string): void => {
      delete store[key];
    },
    clear: (): void => {
      store = {};
    },
    get length(): number {
      return Object.keys(store).length;
    },
    key: (index: number): string | null => Object.keys(store)[index] ?? null,
  };
})();
Object.defineProperty(window, 'localStorage', { value: storageMock, writable: true });

afterEach(() => {
  cleanup();
  localStorage.clear();
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
