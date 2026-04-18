// Links + cost sections.

import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
}

export function EventFormLinksAndCost({ values, onChange, errors }: Props) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">links</h2>
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

      <h2 className="mt-4 text-xs font-medium tracking-wide text-neutral-500 uppercase">cost</h2>
      <TextField
        label="price"
        value={values.price}
        onChange={(e) => {
          onChange({ price: e.target.value });
        }}
        placeholder="$20 sliding scale"
        maxLength={300}
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
        placeholder="email or phone"
        maxLength={300}
      />
    </section>
  );
}
