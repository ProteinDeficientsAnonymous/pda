import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { SortableList } from './SortableList';

describe('SortableList', () => {
  it('should let row content shrink so truncated children do not overflow actions', () => {
    render(
      <SortableList
        items={[{ id: 'a' }]}
        onReorder={vi.fn()}
        renderItem={() => <div>item</div>}
        ariaLabel="items"
      />,
    );

    const row = screen.getByRole('listitem');
    expect(row).toHaveClass('min-w-0');
    const content = row.querySelector(':scope > div');
    expect(content).toHaveClass('min-w-0', 'flex-1');
  });
});
