// TipTap extensions + config shared between edit and view-with-editor render.
// Feature set is intentionally narrow — matches the Quill toolbar used by the
// Flutter app so cross-editor collisions (one client edits a doc authored by
// the other) don't silently drop formatting.

import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import type { Extensions } from '@tiptap/react';

export function pdaExtensions(): Extensions {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      // Not used by the PDA app — keep the bundle small and prevent editors
      // from producing nodes the backend PM→HTML renderer doesn't support.
      codeBlock: false,
      horizontalRule: false,
      strike: false,
    }),
    Link.configure({
      openOnClick: false,
      autolink: true,
      HTMLAttributes: { rel: 'noopener noreferrer', target: '_blank' },
    }),
  ];
}
