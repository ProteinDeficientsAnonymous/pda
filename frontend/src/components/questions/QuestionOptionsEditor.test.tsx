import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { normalizeQuestionOptions, QuestionOptionsEditor } from './QuestionOptionsEditor';

describe('normalizeQuestionOptions', () => {
  it('should trim and drop blank options', () => {
    expect(normalizeQuestionOptions(['  a ', '', 'b', '   '])).toEqual(['a', 'b']);
  });
});

describe('QuestionOptionsEditor', () => {
  it('should render each option as its own field', () => {
    render(<QuestionOptionsEditor options={['driving', 'transit']} onChange={vi.fn()} />);
    expect(screen.getByLabelText('option 1')).toHaveValue('driving');
    expect(screen.getByLabelText('option 2')).toHaveValue('transit');
    expect(screen.queryByLabelText('options')).not.toBeInTheDocument();
  });

  it('should add an empty option when + is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<QuestionOptionsEditor options={['driving']} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /add option/i }));
    expect(onChange).toHaveBeenCalledWith(['driving', '']);
  });

  it('should remove an option row', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<QuestionOptionsEditor options={['driving', 'transit']} onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /remove option 1/i }));
    expect(onChange).toHaveBeenCalledWith(['transit']);
  });

  it('should update a single option value', () => {
    const onChange = vi.fn();
    render(<QuestionOptionsEditor options={['driving']} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText('option 1'), { target: { value: 'bike' } });
    expect(onChange).toHaveBeenCalledWith(['bike']);
  });
});
