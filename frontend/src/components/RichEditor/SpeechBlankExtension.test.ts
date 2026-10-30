import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import { describe, expect, it } from 'vitest';

import { SPEECH_BLANKS, SpeechBlankExtension } from './SpeechBlankExtension';

const BLANK_DOC = {
  type: 'doc',
  content: [
    {
      type: 'paragraph',
      content: [
        { type: 'text', text: 'walk: ' },
        { type: 'speechBlank', attrs: { key: 'walk_details' } },
      ],
    },
  ],
};

function makeEditor(content: object = BLANK_DOC) {
  return new Editor({ extensions: [StarterKit, SpeechBlankExtension], content });
}

describe('SpeechBlankExtension', () => {
  it('round-trips a blank through getJSON', () => {
    const editor = makeEditor();
    expect(editor.getJSON()).toEqual(BLANK_DOC);
  });

  it('renders a chip with the blank label', () => {
    const editor = makeEditor();
    expect(editor.getHTML()).toContain('walk details');
  });

  it('reparses the rendered chip', () => {
    const html = makeEditor().getHTML();
    const editor = new Editor({ extensions: [StarterKit, SpeechBlankExtension], content: html });
    expect(editor.getJSON()).toEqual(BLANK_DOC);
  });

  it('inserts a blank at the cursor', () => {
    const editor = makeEditor({ type: 'doc', content: [{ type: 'paragraph' }] });
    editor.commands.insertSpeechBlank('facilitators');
    expect(JSON.stringify(editor.getJSON())).toContain('"key":"facilitators"');
  });

  it('mirrors the backend blank set', () => {
    expect(Object.keys(SPEECH_BLANKS).sort()).toEqual([
      'back_walker',
      'facilitators',
      'front_walker',
      'intro_question',
      'open_roles',
      'restaurant',
      'upcoming_events',
      'walk_details',
    ]);
    expect(SPEECH_BLANKS.open_roles).toEqual({ label: 'open roles', isList: true });
    expect(SPEECH_BLANKS.upcoming_events.isList).toBe(true);
    expect(SPEECH_BLANKS.facilitators.isList).toBe(false);
  });
});
