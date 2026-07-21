import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RSVP_COMMENT_MAX_LENGTH, RsvpCommentField } from './RsvpCommentField';

describe('RsvpCommentField', () => {
  it('renders the current value', () => {
    render(<RsvpCommentField value="hello" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('hello');
  });

  it('calls onChange as the user types', () => {
    const onChange = vi.fn();
    render(<RsvpCommentField value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hi' } });
    expect(onChange).toHaveBeenCalledWith('hi');
  });

  it('shows remaining characters', () => {
    render(<RsvpCommentField value="ab" onChange={() => {}} />);
    expect(screen.getByText(`${RSVP_COMMENT_MAX_LENGTH - 2} characters left`)).toBeInTheDocument();
  });

  it('triggers onSubmitShortcut on cmd+enter', () => {
    const onSubmitShortcut = vi.fn();
    render(<RsvpCommentField value="hi" onChange={() => {}} onSubmitShortcut={onSubmitShortcut} />);
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', metaKey: true });
    expect(onSubmitShortcut).toHaveBeenCalledTimes(1);
  });

  it('triggers onSubmitShortcut on ctrl+enter', () => {
    const onSubmitShortcut = vi.fn();
    render(<RsvpCommentField value="hi" onChange={() => {}} onSubmitShortcut={onSubmitShortcut} />);
    fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', ctrlKey: true });
    expect(onSubmitShortcut).toHaveBeenCalledTimes(1);
  });

  it('does not throw when onSubmitShortcut is not provided', () => {
    render(<RsvpCommentField value="hi" onChange={() => {}} />);
    expect(() => {
      fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter', metaKey: true });
    }).not.toThrow();
  });
});
