import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { makeEvent } from '@/test/fixtures';

import { LinksSection } from './EventMemberSection';

function renderLinks(event: ReturnType<typeof makeEvent>) {
  return render(
    <MemoryRouter>
      <LinksSection event={event} />
    </MemoryRouter>,
  );
}

describe('LinksSection — linked surveys (Issue 1463)', () => {
  it('renders nothing when there are no links or surveys', () => {
    const { container } = renderLinks(makeEvent());
    expect(container).toBeEmptyDOMElement();
  });

  it('names each linked survey and links to it', () => {
    renderLinks(
      makeEvent({
        linkedSurveys: [{ id: 's1', title: 'Potluck Feedback', slug: 'potluck-feedback' }],
      }),
    );

    const link = screen.getByRole('link', { name: 'potluck feedback' });
    expect(link).toHaveAttribute('href', '/surveys/potluck-feedback');
  });

  it('excludes the datetime poll from the links card', () => {
    renderLinks(
      makeEvent({
        datetimePollSlug: 'when-poll',
        linkedSurveys: [
          { id: 's1', title: 'When Poll', slug: 'when-poll' },
          { id: 's2', title: 'Feedback', slug: 'feedback' },
        ],
      }),
    );

    expect(screen.queryByRole('link', { name: 'when poll' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'feedback' })).toBeInTheDocument();
  });
});
