import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from 'react';
import { useEffect, useRef } from 'react';

const LONG_PRESS_MS = 400;
const MOVE_CANCEL_PX = 10;

// typed as always-present, but absent in jsdom and older Safari
function supportsPointerCapture(el: Element): boolean {
  return typeof el.setPointerCapture === 'function';
}

export function useLongPress(onLongPress: () => void) {
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const origin = useRef<{ x: number; y: number } | null>(null);
  const fired = useRef(false);
  const callback = useRef(onLongPress);
  useEffect(() => {
    callback.current = onLongPress;
  });

  const cancel = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    origin.current = null;
  };

  useEffect(() => cancel, []);

  return {
    // the browser fires click after the press ends; the tap handler drops that click
    didLongPress: () => fired.current,
    handlers: {
      onPointerDown: (e: ReactPointerEvent) => {
        if (e.button !== 0) return;
        fired.current = false;
        origin.current = { x: e.clientX, y: e.clientY };
        // keep receiving move/up even if the cursor drifts off the button mid-hold
        if (supportsPointerCapture(e.currentTarget)) {
          e.currentTarget.setPointerCapture(e.pointerId);
        }
        timer.current = setTimeout(() => {
          fired.current = true;
          timer.current = null;
          callback.current();
        }, LONG_PRESS_MS);
      },
      onPointerMove: (e: ReactPointerEvent) => {
        if (!origin.current) return;
        const dx = e.clientX - origin.current.x;
        const dy = e.clientY - origin.current.y;
        if (Math.hypot(dx, dy) > MOVE_CANCEL_PX) cancel();
      },
      onPointerUp: (e: ReactPointerEvent) => {
        if (
          supportsPointerCapture(e.currentTarget) &&
          e.currentTarget.hasPointerCapture(e.pointerId)
        ) {
          e.currentTarget.releasePointerCapture(e.pointerId);
        }
        cancel();
      },
      onPointerCancel: cancel,
      onContextMenu: (e: ReactMouseEvent) => {
        // touch long-press otherwise raises the native context menu mid-gesture
        if (fired.current) e.preventDefault();
      },
    },
  };
}
