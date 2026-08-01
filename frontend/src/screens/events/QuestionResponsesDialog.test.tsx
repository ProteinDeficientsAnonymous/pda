import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { makeEvent } from '@/test/fixtures';

import { QuestionResponsesDialog } from './QuestionResponsesDialog';

describe('QuestionResponsesDialog', () => {
  it('renders nothing when closed', () => {
    render(
      <QuestionResponsesDialog
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'bringing?',
              fieldType: 'dropdown',
              options: ['chips'],
              required: false,
            },
          ],
        })}
        open={false}
        onClose={() => {}}
      />,
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows responses when open', () => {
    render(
      <QuestionResponsesDialog
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'bringing?',
              fieldType: 'dropdown',
              options: ['chips', 'dips'],
              required: false,
            },
          ],
        })}
        open
        onClose={() => {}}
      />,
    );
    const dialog = screen.getByRole('dialog', { name: /question responses/i });
    expect(dialog).toHaveTextContent('bringing?');
    expect(dialog).toHaveTextContent('chips');
    expect(screen.getByRole('button', { name: /^close$/i })).toBeInTheDocument();
  });
});
