// TipTap extensions + config. Feature set is narrow by design — every node
// we enable here must also have a handler in backend/community/_prosemirror_html.py,
// otherwise it will be silently dropped on render.

import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import TextAlign from '@tiptap/extension-text-align';
import type { Extensions } from '@tiptap/react';
import { CtaExtension } from './CtaExtension';

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
