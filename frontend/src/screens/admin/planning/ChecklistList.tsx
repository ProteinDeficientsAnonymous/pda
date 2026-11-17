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

export function ChecklistList({ items }: { items: ChecklistItem[] }) {
  if (items.length === 0) return <p className="text-muted text-sm">no checklist items yet 🌿</p>;
  return (
    <ol className="flex list-decimal flex-col gap-3 pl-5">
      {items.map((item) => (
        <li key={item.id}>
          <ChecklistItemText item={item} />
        </li>
      ))}
    </ol>
  );
}
