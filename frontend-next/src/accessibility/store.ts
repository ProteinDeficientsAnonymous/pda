// Accessibility preferences store.
//
// Three settings, persisted to localStorage via Zustand `persist`:
//   themeMode  — 'system' (default) | 'light' | 'dark'
//   dyslexiaFont — true toggles OpenDyslexic font family
//   textScale  — 1.0 | 1.15 | 1.3  (normal / medium / large)
//
// DOM sync: on every state change, the store applies CSS classes and
// custom properties to <html>.  A blocking <script> in index.html
// reads the same localStorage key before React hydrates to prevent FOUC.

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'system' | 'light' | 'dark';
export type TextScale = 1.0 | 1.15 | 1.3;

interface AccessibilityState {
  themeMode: ThemeMode;
  dyslexiaFont: boolean;
  textScale: TextScale;
  setThemeMode: (mode: ThemeMode) => void;
  toggleDyslexiaFont: () => void;
  setTextScale: (scale: TextScale) => void;
}

export const useAccessibilityStore = create<AccessibilityState>()(
  persist(
    (set) => ({
      themeMode: 'system',
      dyslexiaFont: false,
      textScale: 1.0,
      setThemeMode: (mode) => set({ themeMode: mode }),
      toggleDyslexiaFont: () => set((s) => ({ dyslexiaFont: !s.dyslexiaFont })),
      setTextScale: (scale) => set({ textScale: scale }),
    }),
    {
      name: 'pda-accessibility',
      partialize: (state) => ({
        themeMode: state.themeMode,
        dyslexiaFont: state.dyslexiaFont,
        textScale: state.textScale,
      }),
    },
  ),
);

// ---------------------------------------------------------------------------
// DOM synchronisation — runs on every store change + on system theme change.
// ---------------------------------------------------------------------------

function applyToDOM(state: AccessibilityState): void {
  const root = document.documentElement;

  root.classList.remove('light', 'dark');
  const resolved: 'light' | 'dark' =
    state.themeMode === 'system'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : state.themeMode;
  root.classList.add(resolved);

  root.classList.toggle('dyslexia', state.dyslexiaFont);
  root.style.setProperty('--text-scale-factor', String(state.textScale));
}

useAccessibilityStore.subscribe(applyToDOM);

window
  .matchMedia('(prefers-color-scheme: dark)')
  .addEventListener('change', () => {
    if (useAccessibilityStore.getState().themeMode === 'system') {
      applyToDOM(useAccessibilityStore.getState());
    }
  });
