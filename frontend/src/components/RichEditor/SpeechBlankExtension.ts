import { Node } from '@tiptap/core';

export type SpeechBlankKey =
  | 'facilitators'
  | 'open_roles'
  | 'upcoming_events'
  | 'intro_question'
  | 'front_walker'
  | 'back_walker'
  | 'walk_details'
  | 'restaurant';

export const SPEECH_BLANKS: Record<SpeechBlankKey, { label: string; isList: boolean }> = {
  facilitators: { label: 'facilitators', isList: false },
  open_roles: { label: 'open roles', isList: true },
  upcoming_events: { label: 'upcoming events', isList: true },
  intro_question: { label: 'intro question', isList: false },
  front_walker: { label: 'front walker', isList: false },
  back_walker: { label: 'back walker', isList: false },
  walk_details: { label: 'walk details', isList: false },
  restaurant: { label: 'restaurant', isList: false },
};

const CHIP_CLASS = 'bg-brand-600 text-brand-on rounded-full px-2 text-xs';

function labelFor(key: unknown): string {
  return typeof key === 'string' && key in SPEECH_BLANKS
    ? SPEECH_BLANKS[key as SpeechBlankKey].label
    : String(key);
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    speechBlank: {
      insertSpeechBlank: (key: SpeechBlankKey) => ReturnType;
    };
  }
}

export const SpeechBlankExtension = Node.create({
  name: 'speechBlank',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return { key: { default: '' } };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-speech-blank]',
        getAttrs: (el) =>
          el instanceof HTMLElement ? { key: el.getAttribute('data-speech-blank') ?? '' } : false,
      },
    ];
  },

  renderHTML({ node }) {
    const key = node.attrs.key as string;
    return ['span', { 'data-speech-blank': key, class: CHIP_CLASS }, labelFor(key)];
  },

  renderText({ node }) {
    return labelFor(node.attrs.key);
  },

  addCommands() {
    return {
      insertSpeechBlank:
        (key: SpeechBlankKey) =>
        ({ chain }) =>
          chain().insertContent({ type: 'speechBlank', attrs: { key } }).run(),
    };
  },
});
