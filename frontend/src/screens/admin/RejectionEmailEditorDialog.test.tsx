import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as RejectionEmailApi from '@/api/rejectionEmail';
import type { RejectionEmail } from '@/api/rejectionEmail';

import { RejectionEmailEditorDialog } from './RejectionEmailEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/rejectionEmail', async (importOriginal) => ({
  ...(await importOriginal<typeof RejectionEmailApi>()),
  useUpdateRejectionEmail: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const TEMPLATE: RejectionEmail = {
  body: 'sorry',
  reasons: {
    vegetarian: 'veg text',
    not_vegan: 'not vegan text',
    questions_not_answered: 'unanswered text',
  },
  updatedAt: '2026-01-01',
};

function renderEditor() {
  const onClose = vi.fn();
  render(<RejectionEmailEditorDialog open onClose={onClose} template={TEMPLATE} />);
  return { onClose };
}

describe('RejectionEmailEditorDialog', () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue(TEMPLATE);
  });

  it('saves the body and each reason text', async () => {
    const { onClose } = renderEditor();
    const veg = screen.getByLabelText('person is vegetarian');
    await userEvent.clear(veg);
    await userEvent.type(veg, 'new veg text');
    await userEvent.click(screen.getByRole('button', { name: 'save' }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        body: 'sorry',
        reasons: { ...TEMPLATE.reasons, vegetarian: 'new veg text' },
      });
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('blocks saving a blank reason', async () => {
    renderEditor();
    await userEvent.clear(screen.getByLabelText('questions not answered'));
    await userEvent.click(screen.getByRole('button', { name: 'save' }));
    expect(screen.getByRole('alert')).toHaveTextContent('each reason needs email text');
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });

  it('lists the reason placeholder', () => {
    renderEditor();
    expect(screen.getByText('${REASON}')).toBeInTheDocument();
  });
});
