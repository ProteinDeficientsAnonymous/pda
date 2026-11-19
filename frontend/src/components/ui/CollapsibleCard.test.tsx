import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { CollapsibleCard } from './CollapsibleCard';

function renderCard() {
  render(
    <CollapsibleCard title="rsvp">
      <p>body</p>
    </CollapsibleCard>,
  );
  return screen.getByRole('button', { name: 'rsvp' }).closest('section')!;
}

describe('CollapsibleCard', () => {
  it('clips only while collapsed, so popovers in an open card stay visible', () => {
    const card = renderCard();
    expect(card).toHaveClass('overflow-hidden');

    fireEvent.click(screen.getByRole('button', { name: 'rsvp' }));

    expect(screen.getByText('body')).toBeVisible();
    expect(card).not.toHaveClass('overflow-hidden');
  });
});
