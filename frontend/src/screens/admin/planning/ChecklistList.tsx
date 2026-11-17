import type { ChecklistItem } from '@/api/planningChecklist';

export function ChecklistItemText({ item }: { item: ChecklistItem }) {
  return (
    <>
      <span>{item.text}</span>
      {item.detail ? (
        <p className="text-foreground-secondary mt-1 text-sm whitespace-pre-line">{item.detail}</p>
      ) : null}
    </>
  );
}
