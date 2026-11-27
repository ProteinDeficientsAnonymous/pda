import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RichEditor } from './RichEditor';

describe('RichEditor', () => {
  it('reports html alongside the json value', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const onHtmlChange = vi.fn();
    render(
      <RichEditor
        value=""
        onChange={onChange}
        onHtmlChange={onHtmlChange}
        toolbarExtra={(editor) => (
          <button onClick={() => editor.commands.insertContent('hi')}>add text</button>
        )}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'add text' }));

    expect(onChange).toHaveBeenCalled();
    expect(onHtmlChange).toHaveBeenLastCalledWith('<p>hi</p>');
  });
});
