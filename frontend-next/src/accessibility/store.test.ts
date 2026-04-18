import { describe, it, expect, beforeEach, vi } from 'vitest';

// Provide a proper localStorage stub before the module loads — Zustand persist
// calls setItem on every setState, which fails with jsdom's default Storage.
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

// Import after localStorage is stubbed so persist middleware picks up our mock.
const { useAccessibilityStore } = await import('./store');

beforeEach(() => {
  storageMock.clear();
  useAccessibilityStore.setState({
    themeMode: 'system',
    dyslexiaFont: false,
    textScale: 1.0,
  });
});

describe('useAccessibilityStore', () => {
  it('defaults themeMode to system', () => {
    expect(useAccessibilityStore.getState().themeMode).toBe('system');
  });

  it('defaults dyslexiaFont to false', () => {
    expect(useAccessibilityStore.getState().dyslexiaFont).toBe(false);
  });

  it('defaults textScale to 1.0', () => {
    expect(useAccessibilityStore.getState().textScale).toBe(1.0);
  });

  it('setThemeMode updates themeMode to dark', () => {
    useAccessibilityStore.getState().setThemeMode('dark');
    expect(useAccessibilityStore.getState().themeMode).toBe('dark');
  });

  it('setThemeMode updates themeMode to light', () => {
    useAccessibilityStore.getState().setThemeMode('light');
    expect(useAccessibilityStore.getState().themeMode).toBe('light');
  });

  it('setThemeMode updates themeMode back to system', () => {
    useAccessibilityStore.getState().setThemeMode('dark');
    useAccessibilityStore.getState().setThemeMode('system');
    expect(useAccessibilityStore.getState().themeMode).toBe('system');
  });

  it('toggleDyslexiaFont enables dyslexia font', () => {
    useAccessibilityStore.getState().toggleDyslexiaFont();
    expect(useAccessibilityStore.getState().dyslexiaFont).toBe(true);
  });

  it('toggleDyslexiaFont toggles off again', () => {
    useAccessibilityStore.getState().toggleDyslexiaFont();
    useAccessibilityStore.getState().toggleDyslexiaFont();
    expect(useAccessibilityStore.getState().dyslexiaFont).toBe(false);
  });

  it('setTextScale updates textScale to 1.15', () => {
    useAccessibilityStore.getState().setTextScale(1.15);
    expect(useAccessibilityStore.getState().textScale).toBe(1.15);
  });

  it('setTextScale updates textScale to 1.3', () => {
    useAccessibilityStore.getState().setTextScale(1.3);
    expect(useAccessibilityStore.getState().textScale).toBe(1.3);
  });
});
