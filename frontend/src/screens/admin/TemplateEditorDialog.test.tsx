import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { TemplateEditorDialog } from './TemplateEditorDialog';

vi.mock('@/api/client');

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderEditor(body: string, mutateAsync = vi.fn().mockResolvedValue({})) {
  const onClose = vi.fn();
  renderWithProviders(
    <TemplateEditorDialog
      open
      onClose={onClose}
      title="edit test email"
      description="sent in tests"
      placeholders={[
        { name: 'FIRST_NAME', hint: "recipient's first name" },
        { name: 'WHATSAPP_LINK' },
      ]}
      ariaLabel="test email body"
      template={{ body }}
      update={{ mutateAsync, isPending: false }}
      noun="email"
    />,
  );
  return { onClose, mutateAsync };
}

describe('TemplateEditorDialog', () => {
  it('seeds the textarea, saves edits and closes', async () => {
    const { onClose, mutateAsync } = renderEditor('original');
    const textarea = screen.getByLabelText('test email body') as HTMLTextAreaElement;
    expect(textarea.value).toBe('original');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'updated');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith('updated');
    });
    expect(toast.success).toHaveBeenCalledWith('email saved 🌱');
    expect(onClose).toHaveBeenCalled();
  });

  it('lists the placeholders with their hints', () => {
    renderEditor('hi');
    expect(screen.getByText('${FIRST_NAME}')).toBeInTheDocument();
    expect(screen.getByText('${WHATSAPP_LINK}')).toBeInTheDocument();
    expect(screen.getByText(/recipient's first name/)).toBeInTheDocument();
  });

  it('blocks save when the body is empty', async () => {
    const { mutateAsync } = renderEditor('');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect((await screen.findByRole('alert')).textContent).toContain('test email body is required');
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('disables save over the length limit', () => {
    renderEditor('x'.repeat(4001));
    expect(screen.getByRole('button', { name: /save/i })).toBeDisabled();
  });

  it('falls back to a friendly error when the save fails', async () => {
    renderEditor('hi', vi.fn().mockRejectedValue(new Error('boom')));
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect((await screen.findByRole('alert')).textContent).toContain(
      "couldn't save the email — try again",
    );
  });
});
