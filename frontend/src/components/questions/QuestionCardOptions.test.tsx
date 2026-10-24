import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { QuestionType } from '@/api/questionTypes';

import { QuestionCardOptions } from './QuestionCardOptions';

function renderOptions(fieldType: string, options: string[]) {
  const onChange = vi.fn();
  const onCommit = vi.fn();
  render(
    <QuestionCardOptions
      id="q1"
      fieldType={fieldType}
      options={options}
      disabled={false}
      onChange={onChange}
      onCommit={onCommit}
    />,
  );
  return { onChange, onCommit };
}

function StatefulOptions({ initial }: { initial: string[] }) {
  const [options, setOptions] = useState(initial);
  return (
    <QuestionCardOptions
      id="q1"
      fieldType={QuestionType.Radio}
      options={options}
      disabled={false}
      onChange={setOptions}
      onCommit={vi.fn()}
    />
  );
}

describe('QuestionCardOptions', () => {
  it('commits the rows when an option loses focus', () => {
    const { onCommit } = renderOptions(QuestionType.Radio, ['tofu', 'tempeh']);
    fireEvent.blur(screen.getByLabelText('option 1'));
    expect(onCommit).toHaveBeenCalledWith(['tofu', 'tempeh']);
  });

  it('inserts an empty row after the current one on enter and focuses it', () => {
    render(<StatefulOptions initial={['tofu', 'tempeh']} />);
    fireEvent.keyDown(screen.getByLabelText('option 1'), { key: 'Enter' });
    const inserted = screen.getByLabelText('option 2');
    expect(inserted).toHaveValue('');
    expect(inserted).toHaveFocus();
    expect(screen.getByLabelText('option 3')).toHaveValue('tempeh');
  });

  it('removes a row and commits right away', () => {
    const { onCommit } = renderOptions(QuestionType.Checkbox, ['tofu', 'tempeh']);
    fireEvent.click(screen.getByRole('button', { name: 'remove option 2' }));
    expect(onCommit).toHaveBeenCalledWith(['tofu']);
  });

  it('keeps the last choice option', () => {
    renderOptions(QuestionType.Radio, ['tofu']);
    expect(screen.queryByRole('button', { name: /^remove/ })).not.toBeInTheDocument();
  });

  it('uses date pickers for a datetime poll', () => {
    renderOptions(QuestionType.DatetimePoll, []);
    expect(screen.getByRole('button', { name: 'pick a date & time' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '+ add date' })).toBeInTheDocument();
  });
});
