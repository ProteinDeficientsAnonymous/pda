import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpNoteField } from './RsvpNoteField';

function openEditor(note = '') {
  const onSave = vi.fn();
  render(<RsvpNoteField note={note} disabled={false} onSave={onSave} />);
  fireEvent.click(screen.getByRole('button', { name: note ? 'edit your note' : 'add a note' }));
  return { onSave, textarea: screen.getByLabelText('note') };
}

describe('RsvpNoteField', () => {
  it('shows an existing note and offers to edit it', () => {
    render(<RsvpNoteField note="bringing snacks" disabled={false} onSave={vi.fn()} />);
    expect(screen.getByText('“bringing snacks”')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'edit your note' })).toBeInTheDocument();
  });

  it('offers to add a note when there is none', () => {
    render(<RsvpNoteField note="" disabled={false} onSave={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'add a note' })).toBeInTheDocument();
  });

  it('trims whitespace before saving', () => {
    const { onSave, textarea } = openEditor();
    fireEvent.change(textarea, { target: { value: '  bringing snacks  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'save note' }));
    expect(onSave).toHaveBeenCalledWith('bringing snacks');
  });

  it('saves an empty string to clear an existing note', () => {
    const { onSave, textarea } = openEditor('bringing snacks');
    fireEvent.change(textarea, { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: 'save note' }));
    expect(onSave).toHaveBeenCalledWith('');
  });

  it('skips the save when the note is unchanged', () => {
    const { onSave } = openEditor('bringing snacks');
    fireEvent.click(screen.getByRole('button', { name: 'save note' }));
    expect(onSave).not.toHaveBeenCalled();
  });

  it('discards the draft on cancel', () => {
    const { onSave, textarea } = openEditor('bringing snacks');
    fireEvent.change(textarea, { target: { value: 'never mind' } });
    fireEvent.click(screen.getByRole('button', { name: 'cancel' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText('“bringing snacks”')).toBeInTheDocument();
  });

  it('caps the note length', () => {
    const { textarea } = openEditor();
    expect(textarea).toHaveAttribute('maxLength', '300');
  });
});
