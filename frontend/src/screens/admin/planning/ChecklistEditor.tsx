import { useState } from 'react';

import { type ChecklistItem, useCreateChecklistItem } from '@/api/planningChecklist';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';

import { ChecklistList } from './ChecklistList';
import { toastOnError } from './toastOnError';

const TEXT_MAX = 300;
const DETAIL_MAX = 2000;

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
      <ChecklistList items={items} />
      <AddItem />
    </div>
  );
}
