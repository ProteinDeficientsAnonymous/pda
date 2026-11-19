import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { ExpandableAnswer } from './ExpandableAnswer';

describe('ExpandableAnswer', () => {
  it('shows short answers in full with no toggle', () => {
    render(<ExpandableAnswer text="great" />);

    expect(screen.getByText('great')).not.toHaveClass('line-clamp-4');
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('wraps long unbroken tokens', () => {
    const token = 'x'.repeat(80);
    render(<ExpandableAnswer text={token} />);

    expect(screen.getByText(token)).toHaveClass(
      'break-words',
      '[overflow-wrap:anywhere]',
      'whitespace-pre-wrap',
    );
  });

  it.each([
    ['many lines', 'a\n\n\n\n\nb'],
    ['many characters', 'y'.repeat(201)],
  ])('clamps answers with %s and toggles them open', async (_, text) => {
    const user = userEvent.setup();
    render(<ExpandableAnswer text={text} />);

    const toggle = screen.getByRole('button', { name: 'show more' });
    const answer = document.getElementById(toggle.getAttribute('aria-controls') ?? '');
    expect(answer).toHaveTextContent(text, { normalizeWhitespace: false });
    expect(answer).toHaveClass('line-clamp-4');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await user.click(toggle);
    expect(answer).not.toHaveClass('line-clamp-4');
    expect(screen.getByRole('button', { name: 'show less' })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
  });
});
