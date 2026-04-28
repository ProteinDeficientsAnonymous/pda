import { Fragment, type ReactNode } from 'react';

const URL_PATTERN = /\b((?:https?:\/\/|www\.)[^\s<>()]+[^\s<>()!?.,;:'"])/gi;

const TRAILING_PUNCT = /[.,;:!?)\]}'"]+$/;

export function linkifyText(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(URL_PATTERN)) {
    const raw = match[0];
    const start = match.index;

    // Strip trailing punctuation that's likely sentence punctuation, not URL.
    const trimmed = raw.replace(TRAILING_PUNCT, '');
    const trailing = raw.slice(trimmed.length);

    if (start > lastIndex) {
      nodes.push(<Fragment key={key++}>{text.slice(lastIndex, start)}</Fragment>);
    }

    const href = trimmed.startsWith('www.') ? `https://${trimmed}` : trimmed;
    nodes.push(
      <a
        key={key++}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-brand-700 hover:text-brand-900 no-underline"
      >
        {trimmed}
      </a>,
    );

    if (trailing) {
      nodes.push(<Fragment key={key++}>{trailing}</Fragment>);
    }

    lastIndex = start + raw.length;
  }

  if (lastIndex < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>);
  }

  return nodes;
}
