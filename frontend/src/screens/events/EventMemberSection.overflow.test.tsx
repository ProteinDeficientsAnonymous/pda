import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { Event } from '@/models/event';

import { CostSection, LinksSection, LocationSection } from './EventMemberSection';

const LONG_TOKEN = 'x'.repeat(200);

function renderIn(node: React.ReactElement) {
  return render(<MemoryRouter>{node}</MemoryRouter>);
}

describe('event detail — long user content wraps (issue 1131)', () => {
  it('wraps a long location so it cannot overflow the viewport', () => {
    const event = { location: `somewhere/${LONG_TOKEN}` } as Event;
    renderIn(<LocationSection event={event} />);
    const link = screen.getByRole('link');
    expect(link).toHaveClass('break-words', '[overflow-wrap:anywhere]');
  });

  it('wraps a long other-link label so it cannot overflow the viewport', () => {
    const event = {
      otherLink: `https://example.com/${LONG_TOKEN}`,
      surveySlugs: [],
    } as unknown as Event;
    renderIn(<LinksSection event={event} />);
    const link = screen.getByRole('link');
    expect(link).toHaveClass('break-words', '[overflow-wrap:anywhere]');
  });

  it('wraps long zelle info so it cannot overflow the viewport', () => {
    const event = { zelleInfo: LONG_TOKEN } as Event;
    renderIn(<CostSection event={event} />);
    expect(screen.getByText(new RegExp(LONG_TOKEN.slice(0, 40)))).toHaveClass(
      'break-words',
      '[overflow-wrap:anywhere]',
    );
  });
});
