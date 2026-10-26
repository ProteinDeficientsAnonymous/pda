import { useId, useState } from 'react';

import { cn } from '@/utils/cn';

const MAX_LINES = 4;
const MAX_CHARS = 200;

export const WRAP_TEXT = '[overflow-wrap:anywhere] break-words whitespace-pre-wrap';

export function ExpandableAnswer({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const textId = useId();
  const long = text.length > MAX_CHARS || text.split('\n').length > MAX_LINES;

  if (!long) return <div className={WRAP_TEXT}>{text}</div>;
  return (
    <div>
      <div id={textId} className={cn(WRAP_TEXT, !expanded && 'line-clamp-4')}>
        {text}
      </div>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={textId}
        onClick={() => {
          setExpanded((v) => !v);
        }}
        className="text-brand-700 hover:text-brand-900 mt-1 text-xs"
      >
        {expanded ? 'show less' : 'show more'}
      </button>
    </div>
  );
}
