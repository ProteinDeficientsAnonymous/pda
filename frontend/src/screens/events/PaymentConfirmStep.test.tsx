import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Event } from '@/models/event';

import { PaymentConfirmStep } from './PaymentConfirmStep';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    price: '$10',
    venmoLink: 'https://venmo.com/u/host',
    cashappLink: '',
    zelleInfo: '',
    ...overrides,
  } as Event;
}

describe('PaymentConfirmStep', () => {
  it('shows the price', () => {
    render(<PaymentConfirmStep event={makeEvent()} onConfirm={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByText(/\$10/)).toBeInTheDocument();
  });

  it('renders a venmo link', () => {
    render(<PaymentConfirmStep event={makeEvent()} onConfirm={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByRole('link', { name: /venmo/i })).toHaveAttribute(
      'href',
      'https://venmo.com/u/host',
    );
  });

  it('normalizes a bare venmo handle into a url', () => {
    render(
      <PaymentConfirmStep
        event={makeEvent({ venmoLink: '@host' })}
        onConfirm={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(screen.getByRole('link', { name: /venmo/i })).toHaveAttribute(
      'href',
      'https://venmo.com/u/host',
    );
  });

  it('normalizes a bare cashapp handle into a url', () => {
    render(
      <PaymentConfirmStep
        event={makeEvent({ venmoLink: '', cashappLink: '$host' })}
        onConfirm={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(screen.getByRole('link', { name: /cashapp/i })).toHaveAttribute(
      'href',
      'https://cash.app/$host',
    );
  });

  it('renders zelle info as text, not a link', () => {
    render(
      <PaymentConfirmStep
        event={makeEvent({ venmoLink: '', zelleInfo: 'host@example.com' })}
        onConfirm={vi.fn()}
        onBack={vi.fn()}
      />,
    );
    expect(screen.getByText(/host@example\.com/)).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('calls onConfirm when the confirm button is clicked', async () => {
    const onConfirm = vi.fn();
    render(<PaymentConfirmStep event={makeEvent()} onConfirm={onConfirm} onBack={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: /yes, i paid/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('calls onBack when the back button is clicked', async () => {
    const onBack = vi.fn();
    render(<PaymentConfirmStep event={makeEvent()} onConfirm={vi.fn()} onBack={onBack} />);
    await userEvent.click(screen.getByRole('button', { name: /back/i }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('disables both buttons while busy', () => {
    render(<PaymentConfirmStep event={makeEvent()} busy onConfirm={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByRole('button', { name: /yes, i paid/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /back/i })).toBeDisabled();
  });
});
