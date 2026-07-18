import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAutosave } from './useAutosave';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useAutosave', () => {
  it('flush saves the latest value immediately instead of dropping it', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() => useAutosave({ onSave }));

    act(() => {
      result.current.schedule('draft with unsaved edits');
    });

    await act(async () => {
      await result.current.flush('draft with unsaved edits');
    });

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith('draft with unsaved edits');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('flush coalesces with a save already in flight instead of firing a duplicate', async () => {
    let resolveSave: (() => void) | undefined;
    const onSave = vi.fn().mockReturnValue(
      new Promise<void>((resolve) => {
        resolveSave = resolve;
      }),
    );
    const { result } = renderHook(() => useAutosave({ onSave }));

    act(() => {
      result.current.schedule('draft with unsaved edits');
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(onSave).toHaveBeenCalledTimes(1);

    const flushPromise = act(async () => {
      await result.current.flush('draft with unsaved edits');
    });
    resolveSave?.();
    await flushPromise;

    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it('flushes a pending debounced edit on unmount instead of dropping it', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { result, unmount } = renderHook(() => useAutosave({ onSave }));

    act(() => {
      result.current.schedule('draft with unsaved edits');
    });
    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith('draft with unsaved edits');
  });
});
