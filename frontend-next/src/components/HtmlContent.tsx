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
        'prose prose-neutral max-w-none text-neutral-800',
        '[&_a]:text-neutral-900 [&_a]:underline',
        '[&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-2xl [&_h1]:font-medium',
        '[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-medium',
        '[&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium',
        '[&_p]:my-3',
        '[&_ul]:my-3 [&_ul]:list-disc [&_ul]:ps-6',
        '[&_ol]:my-3 [&_ol]:list-decimal [&_ol]:ps-6',
        '[&_blockquote]:border-s-4 [&_blockquote]:border-neutral-300 [&_blockquote]:ps-4 [&_blockquote]:italic',
        '[&_code]:rounded [&_code]:bg-neutral-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-sm',
        className,
      )}
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}
