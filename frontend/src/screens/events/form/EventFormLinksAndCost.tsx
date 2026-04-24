// Links + cost section bodies. Each is rendered inside its own
// CollapsibleCard by the parent form. Kept in one file so the small
// per-section components stay co-located with their related logic.

import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
}

export function EventFormLinks({ values, onChange, errors }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <TextField
        label="whatsapp group"
        value={values.whatsappLink}
        onChange={(e) => {
          onChange({ whatsappLink: e.target.value });
        }}
        placeholder="https://chat.whatsapp.com/…"
        maxLength={200}
        error={errors.whatsappLink}
      />
      <TextField
        label="partiful"
        value={values.partifulLink}
        onChange={(e) => {
          onChange({ partifulLink: e.target.value });
        }}
        placeholder="https://partiful.com/…"
        maxLength={200}
        error={errors.partifulLink}
      />
      <TextField
        label="other link"
        value={values.otherLink}
        onChange={(e) => {
          onChange({ otherLink: e.target.value });
        }}
        placeholder="https://…"
        maxLength={200}
        error={errors.otherLink}
      />
    </div>
  );
}

export function EventFormMoney({ values, onChange }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <TextField
        label="price"
        value={values.price}
        onChange={(e) => {
          onChange({ price: e.target.value });
        }}
        placeholder="$20 sliding scale"
        maxLength={300}
        hint="only for covering costs (food, supplies, etc)"
      />
      <TextField
        label="venmo"
        value={values.venmoLink}
        onChange={(e) => {
          onChange({ venmoLink: e.target.value });
        }}
        placeholder="@handle or venmo.com URL"
        maxLength={100}
      />
      <TextField
        label="cash app"
        value={values.cashappLink}
        onChange={(e) => {
          onChange({ cashappLink: e.target.value });
        }}
        placeholder="$handle or cash.app URL"
        maxLength={100}
      />
      <TextField
        label="zelle"
        value={values.zelleInfo}
        onChange={(e) => {
          onChange({ zelleInfo: e.target.value });
        }}
        placeholder="email address or phone number"
        maxLength={300}
      />
    </div>
  );
}
