import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RichEditor } from './RichEditor';
import { SpeechBlankExtension } from './SpeechBlankExtension';
import { SpeechBlankMenu } from './SpeechBlankMenu';

describe('SpeechBlankMenu', () => {
  it('inserts the picked blank into the editor', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <RichEditor
        value=""
        onChange={onChange}
        extraExtensions={[SpeechBlankExtension]}
        toolbarExtra={(editor) => <SpeechBlankMenu editor={editor} />}
      />,
    );

    await user.click(screen.getByRole('button', { name: '+ blank' }));
    await user.click(screen.getByRole('menuitem', { name: 'open roles' }));

    expect(onChange).toHaveBeenLastCalledWith(expect.stringContaining('"key":"open_roles"'));
    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument();
  });
});
