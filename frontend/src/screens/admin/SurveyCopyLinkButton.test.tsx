import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { SurveyCopyLinkButton } from './SurveyCopyLinkButton';

const toastSuccess = vi.fn();
const toastError = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: (m: string) => {
      toastError(m);
    },
  },
}));

function mockClipboard(writeText: ReturnType<typeof vi.fn>) {
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
}

beforeEach(() => {
  toastSuccess.mockClear();
  toastError.mockClear();
});

describe('SurveyCopyLinkButton', () => {
  it('copies the participant url and toasts on success', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    mockClipboard(writeText);

    render(<SurveyCopyLinkButton slug="spring-potluck" />);
    fireEvent.click(screen.getByRole('button', { name: 'copy link' }));

    await vi.waitFor(() => {
      expect(toastSuccess).toHaveBeenCalledWith('link copied');
    });
    expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/surveys/spring-potluck`);
    expect(toastError).not.toHaveBeenCalled();
  });

  it('toasts an error when the clipboard write fails', async () => {
    mockClipboard(vi.fn().mockRejectedValue(new Error('denied')));

    render(<SurveyCopyLinkButton slug="spring-potluck" />);
    fireEvent.click(screen.getByRole('button', { name: 'copy link' }));

    await vi.waitFor(() => {
      expect(toastError).toHaveBeenCalledWith("couldn't copy — try again");
    });
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
