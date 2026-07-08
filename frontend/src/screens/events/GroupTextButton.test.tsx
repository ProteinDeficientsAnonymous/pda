import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { makeEvent } from '@/test/fixtures';

vi.mock('./GroupTextDialog', () => ({
  GroupTextDialog: ({ open }: { open: boolean }) =>
    open ? <div role="dialog" aria-label="group text" /> : null,
}));

import { GroupTextButton } from './GroupTextButton';

describe('GroupTextButton', () => {
  it('renders a trigger and opens the picker dialog on click', () => {
    render(<GroupTextButton event={makeEvent()} />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'group text' }));
    expect(screen.getByRole('dialog', { name: 'group text' })).toBeInTheDocument();
  });
});
