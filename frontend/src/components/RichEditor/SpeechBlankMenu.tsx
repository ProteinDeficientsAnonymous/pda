import type { Editor } from '@tiptap/react';

import { Menu, MenuItem } from './RichEditorToolbar';
import { SPEECH_BLANKS, type SpeechBlankKey } from './SpeechBlankExtension';

export function SpeechBlankMenu({ editor }: { editor: Editor }) {
  return (
    <Menu label="+ blank" active={false} trigger={<span className="text-xs">+ blank</span>}>
      {(close) =>
        (Object.keys(SPEECH_BLANKS) as SpeechBlankKey[]).map((key) => (
          <MenuItem
            key={key}
            active={false}
            onClick={() => {
              editor.chain().focus().insertSpeechBlank(key).run();
              close();
            }}
          >
            {SPEECH_BLANKS[key].label}
          </MenuItem>
        ))
      }
    </Menu>
  );
}
