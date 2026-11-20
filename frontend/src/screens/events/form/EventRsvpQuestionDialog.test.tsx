import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { RsvpQuestionDraft } from '../rsvpQuestions';
import { EventRsvpQuestionDialog } from './EventRsvpQuestionDialog';

describe('EventRsvpQuestionDialog', () => {
  it('requires a question', () => {
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/question required/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('requires options for select one', () => {
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'pick one' } });
    fireEvent.change(screen.getByLabelText('type'), { target: { value: 'select' } });
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/at least one option/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  it('saves a free response question', () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={onClose} onSave={onSave} />);
    fireEvent.change(screen.getByLabelText('question'), { target: { value: 'notes' } });
    fireEvent.click(screen.getByRole('switch', { name: 'required' }));
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'notes',
        fieldType: 'textarea',
        options: [],
        required: true,
        id: expect.any(String) as string,
      }),
    );
    expect(onClose).toHaveBeenCalled();
  });

  it('saves select multiple with option rows when editing', async () => {
    const user = userEvent.setup();
    const existing: RsvpQuestionDraft = {
      id: 'q-existing',
      label: 'help',
      fieldType: 'checkbox',
      options: ['a'],
      required: false,
    };
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open existing={existing} onClose={() => {}} onSave={onSave} />);
    await user.clear(screen.getByLabelText('option 1'));
    await user.type(screen.getByLabelText('option 1'), 'setup');
    await user.click(screen.getByRole('button', { name: /add option/i }));
    await user.type(screen.getByLabelText('option 2'), 'cleanup');
    await user.click(screen.getByRole('button', { name: /^save$/i }));
    expect(onSave).toHaveBeenCalledWith({
      id: 'q-existing',
      label: 'help',
      fieldType: 'checkbox',
      options: ['setup', 'cleanup'],
      optionPrices: [],
      required: false,
    });
  });

  it('allows commas in select multiple options', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    await user.type(screen.getByLabelText('question'), 'help');
    fireEvent.change(screen.getByLabelText('type'), { target: { value: 'checkbox' } });
    await user.type(screen.getByLabelText('option 1'), 'club events (book club, movie club)');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ options: ['club events (book club, movie club)'] }),
    );
  });

  it('allows commas in select one options', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    await user.type(screen.getByLabelText('question'), 'bringing someone?');
    fireEvent.change(screen.getByLabelText('type'), { target: { value: 'select' } });
    await user.type(screen.getByLabelText('option 1'), 'yes, with a guest');
    await user.click(screen.getByRole('button', { name: /add option/i }));
    await user.type(screen.getByLabelText('option 2'), 'no');
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ options: ['yes, with a guest', 'no'] }),
    );
  });

  it('rejects options over the answer length limit', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
    await user.type(screen.getByLabelText('question'), 'pick one');
    fireEvent.change(screen.getByLabelText('type'), { target: { value: 'select' } });
    fireEvent.change(screen.getByLabelText('option 1'), { target: { value: 'x'.repeat(201) } });
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/options must be 200 characters or fewer/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  describe('price per option', () => {
    async function fillOrder(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByLabelText('question'), 'what are you ordering?');
      fireEvent.change(screen.getByLabelText('type'), { target: { value: 'select' } });
      await user.type(screen.getByLabelText('option 1'), 'bowl');
      await user.click(screen.getByRole('button', { name: /add option/i }));
      await user.type(screen.getByLabelText('option 2'), 'plate');
      await user.click(screen.getByRole('switch', { name: 'price per option' }));
    }

    it('saves a price in cents for each option', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
      await fillOrder(user);
      await user.type(screen.getByLabelText('price for bowl'), '12');
      await user.type(screen.getByLabelText('price for plate'), '$18.50');
      await user.click(screen.getByRole('button', { name: /^save$/i }));

      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({ options: ['bowl', 'plate'], optionPrices: [1200, 1850] }),
      );
    });

    it('requires a dollar price for every option', async () => {
      const user = userEvent.setup();
      const onSave = vi.fn();
      render(<EventRsvpQuestionDialog open onClose={() => {}} onSave={onSave} />);
      await fillOrder(user);
      await user.type(screen.getByLabelText('price for bowl'), 'free');
      await user.click(screen.getByRole('button', { name: /^save$/i }));

      expect(screen.getByRole('alert')).toHaveTextContent(/dollar price for each option/i);
      expect(onSave).not.toHaveBeenCalled();
    });

    it('shows saved prices in dollars when editing', () => {
      const existing: RsvpQuestionDraft = {
        id: 'q-order',
        label: 'order',
        fieldType: 'select',
        options: ['bowl', 'plate'],
        optionPrices: [1200, 1850],
        required: true,
      };
      render(
        <EventRsvpQuestionDialog open existing={existing} onClose={() => {}} onSave={vi.fn()} />,
      );

      expect(screen.getByRole('switch', { name: 'price per option' })).toBeChecked();
      expect(screen.getByLabelText('price for plate')).toHaveValue('18.50');
    });
  });
});
