// Sanitized HTML renderer for server-produced Quill HTML.
// Centralizes the dangerouslySetInnerHTML usage so every callsite goes through
// DOMPurify + a consistent prose stylesheet.

import { useMemo } from 'react';
import { sanitizeHtml } from '@/utils/sanitize';
import { cn } from '@/utils/cn';

interface Props {
  html: string;
  className?: string | undefined;
}

export function HtmlContent({ html, className }: Props) {
  const safe = useMemo(() => sanitizeHtml(html), [html]);
  return (
    <div
      className={cn(
        'prose prose-neutral text-foreground max-w-none break-words',
        '[&_a]:text-foreground [&_a]:underline',
        '[&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-2xl [&_h1]:font-medium',
        '[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-medium',
        '[&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium',
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
