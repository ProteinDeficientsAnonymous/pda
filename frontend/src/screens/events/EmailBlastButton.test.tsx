import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { EventStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

vi.mock('./EmailBlastDialog', () => ({
  EmailBlastDialog: ({ open }: { open: boolean }) =>
    open ? <div data-testid="email-blast-dialog" /> : null,
}));

import { EmailBlastButton } from './EmailBlastButton';

describe('EmailBlastButton', () => {
  it('renders the email-blast button when the event has guests', () => {
    render(<EmailBlastButton event={makeEvent()} />);
    expect(screen.getByRole('button', { name: /email blast/i })).toBeInTheDocument();
  });

  it('renders nothing when no one has rsvpd', () => {
    render(<EmailBlastButton event={makeEvent({ guests: [] })} />);
    expect(screen.queryByRole('button', { name: /email blast/i })).not.toBeInTheDocument();
  });

  it('renders nothing for a draft event', () => {
    render(<EmailBlastButton event={makeEvent({ status: EventStatus.Draft })} />);
    expect(screen.queryByRole('button', { name: /email blast/i })).not.toBeInTheDocument();
  });

  it('opens the dialog when clicked', async () => {
    render(<EmailBlastButton event={makeEvent()} />);
    expect(screen.queryByTestId('email-blast-dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /email blast/i }));
    expect(screen.getByTestId('email-blast-dialog')).toBeInTheDocument();
  });
});
