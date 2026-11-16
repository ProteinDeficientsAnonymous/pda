import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { ChecklistEditor } from './ChecklistEditor';

const createItem = vi.fn();

vi.mock('@/api/planningChecklist', () => ({
  useCreateChecklistItem: () => ({ mutateAsync: createItem, isPending: false }),
}));

const ITEMS = [
  { id: 'i1', text: 'secure venue', detail: '' },
  { id: 'i2', text: 'make a flyer', detail: 'canva works' },
];

beforeEach(() => {
  createItem.mockReset().mockResolvedValue(undefined);
});

describe('ChecklistEditor', () => {
  it('lists the items above the add form', () => {
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'secure venue',
      'make a flyercanva works',
    ]);
  });

  it('adds an item once it has text, then clears the form', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    const add = screen.getByRole('button', { name: 'add item' });
    expect(add).toBeDisabled();
    await user.type(screen.getByLabelText('item'), 'book the room');
    await user.click(add);
    expect(createItem).toHaveBeenCalledWith({ text: 'book the room', detail: '' });
    await waitFor(() => {
      expect(screen.getByLabelText('item')).toHaveValue('');
    });
  });
});
