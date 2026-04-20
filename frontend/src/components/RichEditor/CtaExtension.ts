// Custom TipTap node for CTA buttons. Renders as an anchor with class
// `cta cta--{variant}` — the backend PM→HTML renderer emits the same markup
// so the live editor preview and the saved HTML look identical.

import { Node } from '@tiptap/core';

export type CtaVariant = 'primary' | 'secondary';
export type CtaAlignment = 'left' | 'center' | 'right';

export interface CtaAttrs {
  href: string;
  label: string;
  variant: CtaVariant;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    cta: {
      insertCta: (attrs: CtaAttrs) => ReturnType;
      updateCta: (attrs: CtaAttrs) => ReturnType;
    };
  }
}

export const CtaExtension = Node.create({
  name: 'cta',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      href: { default: '' },
      label: { default: '' },
      variant: { default: 'primary' as CtaVariant },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'a.cta',
        getAttrs: (el) => {
          if (!(el instanceof HTMLElement)) return false;
          const classList = el.classList;
          const variant: CtaVariant = classList.contains('cta--secondary')
            ? 'secondary'
            : 'primary';
          return {
            href: el.getAttribute('href') ?? '',
            label: el.textContent || '',
            variant,
          };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes, node }) {
    const attrs = node.attrs as CtaAttrs;
    const variant: CtaVariant = attrs.variant === 'secondary' ? 'secondary' : 'primary';
    // TextAlign extension injects `style: "text-align: ..."` into HTMLAttributes
    // via addGlobalAttributes. Pull it onto a <p> wrapper so alignment actually
    // applies — the inline-flex anchor won't respect its own text-align.
    const styleAttr =
      typeof HTMLAttributes.style === 'string' && HTMLAttributes.style.includes('text-align')
        ? { style: HTMLAttributes.style }
        : {};
    return [
      'p',
      styleAttr,
      [
        'a',
        {
          class: `cta cta--${variant}`,
          href: attrs.href,
          target: '_blank',
          rel: 'noopener noreferrer',
          role: 'button',
        },
        attrs.label,
      ],
    ];
  },

  addCommands() {
    return {
      insertCta:
        (attrs: CtaAttrs) =>
        ({ chain }) =>
          chain().insertContent({ type: 'cta', attrs }).run(),
      updateCta:
        (attrs: CtaAttrs) =>
        ({ commands }) =>
          commands.updateAttributes('cta', attrs),
    };
  },
});
