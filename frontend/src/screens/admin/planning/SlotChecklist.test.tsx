import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { SlotChecklist } from './SlotChecklist';

const tick = vi.fn();
const toastError = vi.fn();
let items: { id: string; text: string; detail: string }[];

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/planningChecklist', () => ({
  useChecklist: () => ({ data: items }),
  useTickChecklistItem: () => ({ mutateAsync: tick }),
}));

beforeEach(() => {
  items = [
    { id: 'i1', text: 'secure venue', detail: '' },
    { id: 'i2', text: 'make a flyer', detail: '' },
    { id: 'i3', text: 'send a reminder', detail: '' },
  ];
  tick.mockReset().mockResolvedValue(undefined);
  toastError.mockReset();
});

async function open() {
  await userEvent.click(screen.getByRole('button', { name: 'checklist · 1/3 done' }));
}

describe('SlotChecklist', () => {
  it('counts done items and lists open ones first', async () => {
    renderWithProviders(<SlotChecklist slotId="s1" label="march" doneIds={['i1']} />);
    await open();
    expect(screen.getAllByRole('checkbox').map((c) => c.getAttribute('aria-label'))).toEqual([
      'make a flyer for march',
      'send a reminder for march',
      'secure venue for march',
    ]);
    expect(screen.getByRole('checkbox', { name: 'secure venue for march' })).toBeChecked();
  });

  it('ticks and unticks items', async () => {
    renderWithProviders(<SlotChecklist slotId="s1" label="march" doneIds={['i1']} />);
    await open();
    await userEvent.click(screen.getByRole('checkbox', { name: 'make a flyer for march' }));
    expect(tick).toHaveBeenCalledWith({ itemId: 'i2', done: true });
    await userEvent.click(screen.getByRole('checkbox', { name: 'secure venue for march' }));
    expect(tick).toHaveBeenCalledWith({ itemId: 'i1', done: false });
  });

  it('keeps rows in place while open and locks a box until its save settles', async () => {
    let settle = () => {};
    tick.mockReturnValue(
      new Promise<void>((resolve) => {
        settle = resolve;
      }),
    );
    renderWithProviders(<SlotChecklist slotId="s1" label="march" doneIds={['i1']} />);
    await open();
    const box = screen.getByRole('checkbox', { name: 'make a flyer for march' });
    await userEvent.click(box);
    expect(box).toBeChecked();
    expect(box).toBeDisabled();
    expect(screen.getAllByRole('checkbox')[0]).toBe(box);
    settle();
    await waitFor(() => {
      expect(box).toBeEnabled();
    });
  });

  it('rolls back and toasts when a tick fails', async () => {
    tick.mockRejectedValue(new Error('nope'));
    renderWithProviders(<SlotChecklist slotId="s1" label="march" doneIds={['i1']} />);
    await open();
    const box = screen.getByRole('checkbox', { name: 'make a flyer for march' });
    await userEvent.click(box);
    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith("couldn't save that — try again");
    });
    expect(box).not.toBeChecked();
  });

  it('renders nothing without checklist items', () => {
    items = [];
    const { container } = renderWithProviders(
      <SlotChecklist slotId="s1" label="march" doneIds={[]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
