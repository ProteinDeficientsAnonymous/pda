import Link from '@tiptap/extension-link';
import TextAlign from '@tiptap/extension-text-align';
import type { Extensions } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

import { CtaExtension } from './CtaExtension';

// every node enabled here must also have a handler in backend/community/_prosemirror_html.py, or it's silently dropped on render
export function pdaExtensions(): Extensions {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: false,
      horizontalRule: false,
      strike: false,
    }),
    Link.configure({
      openOnClick: false,
      autolink: true,
      HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' },
    }),
    TextAlign.configure({
      types: ['paragraph', 'heading', 'cta'],
      alignments: ['left', 'center', 'right'],
    }),
    CtaExtension,
  ];
}
