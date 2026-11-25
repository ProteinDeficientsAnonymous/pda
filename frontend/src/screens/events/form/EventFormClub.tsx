import { useClubs } from '@/api/clubs';
import type { EventFormValues } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';

interface Props {
  value: string;
  onChange: (patch: Partial<EventFormValues>) => void;
  error: string | undefined;
}

export function EventFormClub({ value, onChange, error }: Props) {
  const { data: clubs, isPending, isError } = useClubs();

  if (isPending) return <p className="text-foreground-tertiary text-sm">loading clubs…</p>;
  if (isError) {
    return <p className="text-foreground-tertiary text-sm">couldn't load clubs — try again</p>;
  }
  if (clubs.length === 0) {
    return (
      <div className="flex flex-col gap-1">
        <p className="text-foreground-tertiary text-sm">
          no clubs yet — add them in admin &gt; clubs
        </p>
        {error ? <p className="text-destructive text-xs">{error}</p> : null}
      </div>
    );
  }

  return (
    <Select
      label="which club?"
      value={value}
      onChange={(e) => {
        onChange({ clubId: e.target.value });
      }}
      options={[
        { value: '', label: 'pick a club' },
        ...clubs.map((c) => ({ value: c.id, label: c.name })),
      ]}
      error={error}
    />
  );
}
