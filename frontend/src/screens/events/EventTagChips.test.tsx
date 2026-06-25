import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { EventTag } from '@/models/event';
import { EventTagChips } from './EventTagChips';

const TAGS: EventTag[] = [
  { id: 't1', name: 'walk', slug: 'walk' },
  { id: 't2', name: 'restaurant meetup', slug: 'restaurant-meetup' },
];

describe('EventTagChips', () => {
  it('renders a chip per tag', () => {
    render(<EventTagChips tags={TAGS} />);
    expect(screen.getByText('walk')).toBeInTheDocument();
    expect(screen.getByText('restaurant meetup')).toBeInTheDocument();
  });

  it('renders nothing when there are no tags', () => {
    const { container } = render(<EventTagChips tags={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
