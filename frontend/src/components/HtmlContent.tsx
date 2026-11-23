import { useEffect, useMemo } from 'react';

import { cn } from '@/utils/cn';
import { addHeadingAnchors, scrollToHash } from '@/utils/headingAnchors';
import { sanitizeHtml } from '@/utils/sanitize';

interface Props {
  html: string;
  className?: string | undefined;
}

export function HtmlContent({ html, className }: Props) {
  const safe = useMemo(() => addHeadingAnchors(sanitizeHtml(html)), [html]);

  // content arrives after the browser's own load-time hash jump, so redo it once it's in the dom
  useEffect(() => {
    scrollToHash(window.location.hash);
  }, [safe]);
  return (
    <div
      className={cn(
        'prose prose-neutral text-foreground max-w-none break-words',
        '[&_a]:text-foreground [&_a]:underline',
        '[&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-2xl [&_h1]:font-medium',
        '[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-medium',
        '[&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium',
        '[&_:is(h1,h2,h3)]:scroll-mt-14',
        '[&_a.heading-anchor]:text-muted [&_a.heading-anchor]:ms-2 [&_a.heading-anchor]:no-underline [&_a.heading-anchor]:opacity-0 [&_a.heading-anchor]:transition-opacity',
        '[&_:is(h1,h2,h3):hover_a.heading-anchor]:opacity-100 [&_a.heading-anchor:focus-visible]:opacity-100 pointer-coarse:[&_a.heading-anchor]:opacity-60',
        '[&_p]:my-3',
        '[&_ul]:my-3 [&_ul]:list-disc [&_ul]:ps-6',
        '[&_ol]:my-3 [&_ol]:list-decimal [&_ol]:ps-6',
        '[&_blockquote]:border-border-strong [&_blockquote]:border-s-4 [&_blockquote]:ps-4 [&_blockquote]:italic',
        '[&_code]:bg-surface-dim [&_code]:rounded [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-sm',
        '[&_a.cta]:my-3 [&_a.cta]:inline-flex [&_a.cta]:h-10 [&_a.cta]:items-center [&_a.cta]:justify-center [&_a.cta]:rounded-md [&_a.cta]:px-4 [&_a.cta]:text-sm [&_a.cta]:font-medium [&_a.cta]:no-underline [&_a.cta]:transition-colors',
        '[&_a.cta--primary]:bg-brand-600 [&_a.cta--primary]:text-brand-on hover:[&_a.cta--primary]:bg-brand-700',
        '[&_a.cta--secondary]:bg-surface [&_a.cta--secondary]:text-foreground [&_a.cta--secondary]:border-border-strong hover:[&_a.cta--secondary]:bg-background [&_a.cta--secondary]:border',
        className,
      )}
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}
