// Thin dnd-kit wrapper for reorderable lists. Callers own the source-of-
// truth state and decide what to do on reorder (optimistic update + server
// PUT is the common pattern).
//
// Keyboard support is baked in — focus an item, space to lift, arrow keys
// to move, space to drop. The visual drag handle is a button with an
// aria-label so screen readers announce it.

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { ReactNode } from 'react';

interface Props<T extends { id: string }> {
  items: readonly T[];
  onReorder: (nextIds: string[]) => void;
  renderItem: (item: T) => ReactNode;
  ariaLabel?: string;
}

export function SortableList<T extends { id: string }>({
  items,
  onReorder,
  renderItem,
  ariaLabel,
}: Props<T>) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex = items.findIndex((i) => i.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    onReorder(arrayMove(items as T[], oldIndex, newIndex).map((i) => i.id));
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
      <SortableContext items={items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
        <ul aria-label={ariaLabel} className="flex flex-col gap-2">
          {items.map((item) => (
            <SortableRow key={item.id} id={item.id}>
              {renderItem(item)}
            </SortableRow>
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}

function SortableRow({ id, children }: { id: string; children: ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id,
  });
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };
  return (
    <li ref={setNodeRef} style={style} className="flex items-stretch gap-2">
      <button
        type="button"
        aria-label="drag to reorder"
        {...attributes}
        {...listeners}
        className="text-muted-foreground hover:bg-surface-dim flex w-6 shrink-0 cursor-grab touch-none items-center justify-center rounded active:cursor-grabbing"
      >
        <span aria-hidden="true">⋮⋮</span>
      </button>
      <div className="flex-1">{children}</div>
    </li>
  );
}
