import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import MemberEmailBlastScreen from './MemberEmailBlastScreen';

const { preview, send, test, sendPending, toastSuccess } = vi.hoisted(() => ({
  preview: vi.fn(),
  send: vi.fn(),
  test: vi.fn(),
  toastSuccess: vi.fn(),
  sendPending: { value: false },
}));
vi.mock('@/api/memberBlast', () => ({
  useBlastPreview: () => ({ mutateAsync: preview, isPending: false }),
  useSendTestBlast: () => ({ mutateAsync: test, isPending: false }),
  useSendMemberBlast: () => ({ mutateAsync: send, isPending: sendPending.value }),
  useMemberBlasts: () => ({ data: [], refetch: vi.fn() }),
}));
vi.mock('sonner', () => ({ toast: { success: toastSuccess } }));
vi.mock('@/components/RichEditor/RichEditor', () => ({
  RichEditor: ({ onHtmlChange }: { onHtmlChange?: (h: string) => void }) => (
    <textarea aria-label="body" onChange={(e) => onHtmlChange?.(e.target.value)} />
  ),
}));

async function fill() {
  renderWithProviders(<MemberEmailBlastScreen />);
  await userEvent.type(screen.getByLabelText('subject'), 'hello');
  await userEvent.type(screen.getByLabelText('body'), '<p>hi</p>');
}

const click = async (name: string) => userEvent.click(await screen.findByRole('button', { name }));

async function confirmSend() {
  await fill();
  await click('send to all members');
  await click('send');
}

beforeEach(() => {
  vi.clearAllMocks();
  sendPending.value = false;
  preview.mockResolvedValue({ html: '<p>hi</p>', recipient_count: 3, skipped_count: 1 });
});

describe('MemberEmailBlastScreen', () => {
  it('preview renders iframe with server html', async () => {
    await fill();
    await click('preview');
    expect((await screen.findByTitle('email preview')).getAttribute('srcdoc')).toBe('<p>hi</p>');
    expect(screen.getByText(/this will go to 3 members \(1 skipped/)).toBeTruthy();
  });

  it('send asks for confirmation before calling api', async () => {
    send.mockResolvedValue({ status: 'sent', sent_count: 3 });
    await fill();
    await click('send to all members');
    expect(await screen.findByText('send "hello" to 3 members?')).toBeTruthy();
    expect(send).not.toHaveBeenCalled();
    await click('send');
    expect(await screen.findByText('sent to 3 members')).toBeTruthy();
  });

  it('send button disabled while sending', async () => {
    sendPending.value = true;
    await fill();
    expect(screen.getByRole('button', { name: 'send to all members' })).toHaveProperty(
      'disabled',
      true,
    );
  });

  it('shows unknown warning', async () => {
    send.mockResolvedValue({ status: 'unknown', sent_count: 0 });
    await confirmSend();
    expect(await screen.findByText(/brevo didn't confirm delivery/)).toBeTruthy();
  });

  it('duplicate error shows message', async () => {
    const data = { detail: [{ code: 'notification.blast_duplicate', field: null }] };
    send.mockRejectedValue(
      new AxiosError('x', '409', undefined, undefined, { status: 409, data } as never),
    );
    await confirmSend();
    expect(await screen.findByText('this was already sent in the last 15 minutes')).toBeTruthy();
  });

  it('double click sends once', async () => {
    send.mockResolvedValue({ status: 'sent', sent_count: 3 });
    await fill();
    const all = await screen.findByRole('button', { name: 'send to all members' });
    await userEvent.dblClick(all);
    await click('send');
    await screen.findByText('sent to 3 members');
    expect(send).toHaveBeenCalledTimes(1);
  });

  it('test send rejected by brevo shows error, not success', async () => {
    test.mockResolvedValue({ sent: false });
    await fill();
    await click('send test to me');
    expect(await screen.findByText("brevo didn't accept the test — nothing was sent")).toBeTruthy();
    expect(toastSuccess).not.toHaveBeenCalled();
  });

  it('partial failure warns against resending', async () => {
    send.mockResolvedValue({ status: 'failed', sent_count: 3, failed_count: 2 });
    await confirmSend();
    expect(
      await screen.findByText("sent to 3 members, 2 failed — don't resend without checking brevo"),
    ).toBeTruthy();
  });

  it('500 on send warns the blast may have gone out', async () => {
    send.mockRejectedValue(
      new AxiosError('x', '500', undefined, undefined, { status: 500, data: {} } as never),
    );
    await confirmSend();
    expect(
      await screen.findByText(
        'something went wrong — the blast may have gone out. check the history below before resending.',
      ),
    ).toBeTruthy();
  });

  it('cancelling confirm makes no send call and re-enables button', async () => {
    await fill();
    await click('send to all members');
    await click('cancel');
    expect(send).not.toHaveBeenCalled();
    expect(
      screen.getByRole('button', { name: 'send to all members' }).hasAttribute('disabled'),
    ).toBe(false);
  });
});
