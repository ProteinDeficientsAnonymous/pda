// Accessibility preferences — font family (dyslexia-friendly on/off) and text
// size. Persisted in localStorage and applied to <html> via data-attributes so
// CSS in src/index.css can reshape font-family and the root font-size. Because
// Tailwind defaults sizes in rem, scaling the root size scales the whole app.

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type TextSize = 'small' | 'normal' | 'large' | 'xlarge';

interface AccessibilityState {
  dyslexiaFriendlyFont: boolean;
  textSize: TextSize;
  setDyslexiaFriendlyFont: (v: boolean) => void;
  setTextSize: (v: TextSize) => void;
}

export const useAccessibilityStore = create<AccessibilityState>()(
  persist(
    (set) => ({
      dyslexiaFriendlyFont: false,
      textSize: 'normal',
      setDyslexiaFriendlyFont: (v) => {
        set({ dyslexiaFriendlyFont: v });
      },
      setTextSize: (v) => {
        set({ textSize: v });
      },
    }),
    { name: 'pda-accessibility' },
  ),
);

function applyToDom(state: AccessibilityState) {
  const html = document.documentElement;
  html.dataset.pdaFont = state.dyslexiaFriendlyFont ? 'dyslexic' : 'default';
  html.dataset.pdaText = state.textSize;
}

// Apply current prefs at module load (runs after Zustand rehydrates from storage)
// and whenever they change.
applyToDom(useAccessibilityStore.getState());
useAccessibilityStore.subscribe((state) => {
  applyToDom(state);
});
