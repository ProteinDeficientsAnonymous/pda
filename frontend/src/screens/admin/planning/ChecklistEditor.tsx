import { useState } from 'react';

import {
  type ChecklistItem,
  useCreateChecklistItem,
  useDeleteChecklistItem,
  useMoveChecklistItem,
  useUpdateChecklistItem,
} from '@/api/planningChecklist';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { useConfirm } from '@/components/ui/useConfirm';

import { ChecklistItemText } from './ChecklistList';
import { toastOnError } from './toastOnError';

const TEXT_MAX = 300;
const DETAIL_MAX = 2000;
const SAVE_FAILED = "couldn't save that item — try again";

interface Draft {
  text: string;
  detail: string;
}

function ItemFields({
  id,
  draft,
  onChange,
}: {
  id: string;
  draft: Draft;
  onChange: (d: Draft) => void;
}) {
  return (
    <>
      <TextField
        id={`${id}-text`}
        label="item"
        maxLength={TEXT_MAX}
        value={draft.text}
        onChange={(e) => {
          onChange({ ...draft, text: e.target.value });
        }}
      />
      <Textarea
        id={`${id}-detail`}
        label="details"
        labelSuffix="optional"
        rows={3}
        maxLength={DETAIL_MAX}
        value={draft.detail}
        onChange={(e) => {
          onChange({ ...draft, detail: e.target.value });
        }}
      />
    </>
  );
}

function ItemRow({ item, first, last }: { item: ChecklistItem; first: boolean; last: boolean }) {
  const update = useUpdateChecklistItem();
  const remove = useDeleteChecklistItem();
  const move = useMoveChecklistItem();
  const { confirm, element } = useConfirm();
  const [draft, setDraft] = useState<Draft | null>(null);
  const busy = update.isPending || remove.isPending || move.isPending;

  async function save(next: Draft) {
    const input = { text: next.text.trim(), detail: next.detail.trim() };
    if (await toastOnError(update.mutateAsync({ id: item.id, input }), SAVE_FAILED)) setDraft(null);
  }

  async function onDelete() {
    const ok = await confirm({
      message: "delete this item? it's dropped from every event's checklist",
      confirmLabel: 'delete',
      destructive: true,
    });
    if (ok)
      await toastOnError(remove.mutateAsync(item.id), "couldn't delete that item — try again");
  }

  function onMove(direction: 'up' | 'down') {
    void toastOnError(
      move.mutateAsync({ id: item.id, direction }),
      "couldn't move that item — try again",
    );
  }

  if (draft) {
    return (
      <li className="flex flex-col gap-2">
        <ItemFields id={`item-${item.id}`} draft={draft} onChange={setDraft} />
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy || !draft.text.trim()} onClick={() => void save(draft)}>
            save
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setDraft(null);
            }}
          >
            cancel
          </Button>
          <Button
            variant="destructive"
            aria-label={`delete ${item.text}`}
            disabled={busy}
            onClick={() => void onDelete()}
          >
            delete
          </Button>
        </div>
        {element}
      </li>
    );
  }

  return (
    <li className="flex items-start justify-between gap-2">
      <div className="min-w-0 break-words">
        <ChecklistItemText item={item} />
      </div>
      <div className="flex shrink-0 gap-1">
        <Button
          variant="ghost"
          aria-label={`move ${item.text} up`}
          disabled={busy || first}
          onClick={() => {
            onMove('up');
          }}
        >
          ↑
        </Button>
        <Button
          variant="ghost"
          aria-label={`move ${item.text} down`}
          disabled={busy || last}
          onClick={() => {
            onMove('down');
          }}
        >
          ↓
        </Button>
        <Button
          variant="secondary"
          aria-label={`edit ${item.text}`}
          onClick={() => {
            setDraft({ text: item.text, detail: item.detail });
          }}
        >
          edit
        </Button>
      </div>
    </li>
  );
}

function AddItem() {
  const create = useCreateChecklistItem();
  const [draft, setDraft] = useState<Draft>({ text: '', detail: '' });

  async function onAdd() {
    const input = { text: draft.text.trim(), detail: draft.detail.trim() };
    if (await toastOnError(create.mutateAsync(input), "couldn't add that item — try again")) {
      setDraft({ text: '', detail: '' });
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <ItemFields id="new-item" draft={draft} onChange={setDraft} />
      <div>
        <Button disabled={create.isPending || !draft.text.trim()} onClick={() => void onAdd()}>
          add item
        </Button>
      </div>
    </div>
  );
}

export function ChecklistEditor({ items }: { items: ChecklistItem[] }) {
  return (
    <div className="flex flex-col gap-6">
      <ul className="flex flex-col gap-4">
        {items.map((item, i) => (
          <ItemRow key={item.id} item={item} first={i === 0} last={i === items.length - 1} />
        ))}
      </ul>
      <AddItem />
    </div>
  );
}
