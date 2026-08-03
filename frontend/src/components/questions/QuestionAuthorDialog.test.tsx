import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { QuestionAuthorDialog } from './QuestionAuthorDialog';

const TYPE_OPTIONS = [
  { value: 'text', label: 'short text' },
  { value: 'select', label: 'select' },
] as const;

describe('QuestionAuthorDialog', () => {
  it('should require a label before saving', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(
      <QuestionAuthorDialog
        open
        onClose={() => undefined}
        title="add question"
        initial={{ label: '', fieldType: 'text', options: [], required: false }}
        typeOptions={[...TYPE_OPTIONS]}
        busy={false}
        onSave={onSave}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(screen.getByRole('alert')).toHaveTextContent('label required');
    expect(onSave).not.toHaveBeenCalled();
  });

  it('should require options for option-backed types and save parsed values', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <QuestionAuthorDialog
        open
        onClose={() => undefined}
        title="add question"
        initial={{ label: 'Meal', fieldType: 'select', options: [], required: true }}
        typeOptions={[...TYPE_OPTIONS]}
        busy={false}
        onSave={onSave}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(screen.getByRole('alert')).toHaveTextContent('add at least one option');

    await user.type(screen.getByLabelText('options'), 'vegan\nomni');
    await user.click(screen.getByRole('button', { name: 'save' }));
    expect(onSave).toHaveBeenCalledWith({
      label: 'Meal',
      fieldType: 'select',
      options: ['vegan', 'omni'],
      required: true,
    });
  });
});
