import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { ChecklistEditor } from './ChecklistEditor';

const createItem = vi.fn();
const updateItem = vi.fn();
const deleteItem = vi.fn();
const reorder = vi.fn();

vi.mock('@/api/planningChecklist', () => ({
  useCreateChecklistItem: () => ({ mutateAsync: createItem, isPending: false }),
  useUpdateChecklistItem: () => ({ mutateAsync: updateItem, isPending: false }),
  useDeleteChecklistItem: () => ({ mutateAsync: deleteItem, isPending: false }),
  useReorderChecklist: () => ({ mutateAsync: reorder, isPending: false }),
}));

vi.mock('@/components/SortableList', () => ({
  SortableList: ({
    items,
    onReorder,
    renderItem,
  }: {
    items: { id: string }[];
    onReorder: (ids: string[]) => void;
    renderItem: (item: { id: string }) => ReactNode;
  }) => (
    <div>
      {items.map((item) => (
        <div key={item.id}>{renderItem(item)}</div>
      ))}
      <button
        type="button"
        onClick={() => {
          onReorder(items.map((i) => i.id).reverse());
        }}
      >
        simulate reorder
      </button>
    </div>
  ),
}));

const ITEMS = [
  { id: 'i1', text: 'secure venue', detail: '' },
  { id: 'i2', text: 'make a flyer', detail: 'canva works' },
];

beforeEach(() => {
  for (const fn of [createItem, updateItem, deleteItem, reorder]) {
    fn.mockReset().mockResolvedValue(undefined);
  }
});

describe('ChecklistEditor', () => {
  it('saves the new order after a drag', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    await user.click(screen.getByRole('button', { name: 'simulate reorder' }));
    expect(reorder).toHaveBeenCalledWith(['i2', 'i1']);
  });

  it('edits an item and trims what it saves', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    await user.click(screen.getByRole('button', { name: 'edit make a flyer' }));
    const text = screen.getByDisplayValue('make a flyer');
    await user.clear(text);
    await user.type(text, ' make an ig flyer ');
    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(updateItem).toHaveBeenCalledWith({
      id: 'i2',
      input: { text: 'make an ig flyer', detail: 'canva works' },
    });
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'save' })).not.toBeInTheDocument();
    });
  });

  it('cancels an edit without saving', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    await user.click(screen.getByRole('button', { name: 'edit secure venue' }));
    await user.click(screen.getByRole('button', { name: 'cancel' }));
    expect(updateItem).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'edit secure venue' })).toBeInTheDocument();
  });

  it('asks before deleting', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    await user.click(screen.getByRole('button', { name: 'edit secure venue' }));
    await user.click(screen.getByRole('button', { name: 'delete secure venue' }));
    expect(deleteItem).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'delete' }));
    await waitFor(() => {
      expect(deleteItem).toHaveBeenCalledWith('i1');
    });
  });

  it('lists the items above the add form', () => {
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    expect(screen.getByText('canva works')).toBeInTheDocument();
  });

  it('adds an item once it has text, then clears the form', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ChecklistEditor items={ITEMS} />);
    const add = screen.getByRole('button', { name: 'add item' });
    expect(add).toBeDisabled();
    await user.type(screen.getByLabelText('item'), 'book the room');
    await user.type(screen.getByLabelText(/details/), ' ask for the back room ');
    await user.click(add);
    expect(createItem).toHaveBeenCalledWith({
      text: 'book the room',
      detail: 'ask for the back room',
    });
    await waitFor(() => {
      expect(screen.getAllByLabelText('item').at(-1)).toHaveValue('');
    });
  });
});
