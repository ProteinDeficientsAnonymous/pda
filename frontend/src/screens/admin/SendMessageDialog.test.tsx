import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { SendMessageDialog } from './SendMessageDialog';

function renderDialog(onClose = vi.fn()) {
  render(
    <SendMessageDialog
      open
      onClose={onClose}
      fullName="Sage Blackwood"
      phoneNumber="+12025551234"
    />,
  );
  return onClose;
}

describe('SendMessageDialog', () => {
  it('offers sms and whatsapp links with no pre-filled body', () => {
    renderDialog();
    expect(screen.getByText('send via sms').closest('a')).toHaveAttribute(
      'href',
      'sms:+12025551234',
    );
    expect(screen.getByText('send via whatsapp').closest('a')).toHaveAttribute(
      'href',
      'https://wa.me/12025551234',
    );
  });

  it('closes after picking a channel', async () => {
    const onClose = renderDialog();
    await userEvent.click(screen.getByText('send via sms'));
    expect(onClose).toHaveBeenCalled();
  });
});
