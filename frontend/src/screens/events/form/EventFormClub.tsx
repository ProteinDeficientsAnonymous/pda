import { useClubs } from '@/api/clubs';
import type { EventFormValues } from '@/api/eventWrites';
import { Select } from '@/components/ui/Select';

interface Props {
  value: string;
  onChange: (patch: Partial<EventFormValues>) => void;
  error: string | undefined;
  allowedClubIds: readonly string[] | null;
}

export function EventFormClub({ value, onChange, error, allowedClubIds }: Props) {
  const { data: clubs, isPending, isError } = useClubs();

  const errorLine = error ? <p className="text-destructive text-xs">{error}</p> : null;
  const note = (text: string) => (
    <div className="flex flex-col gap-1">
      <p className="text-foreground-tertiary text-sm">{text}</p>
      {errorLine}
    </div>
  );

  if (isPending) return note('loading clubs…');
  if (isError) return note("couldn't load clubs — try again");
  if (clubs.length === 0) return note('no clubs yet — add them in admin > clubs');

  return (
    <Select
      label="which club?"
      value={value}
      onChange={(e) => {
        onChange({ clubId: e.target.value });
      }}
      options={[
        { value: '', label: 'pick a club' },
        ...clubs.map((c) => ({
          value: c.id,
          label: c.name,
          disabled: allowedClubIds !== null && !allowedClubIds.includes(c.id),
        })),
      ]}
      error={error}
    />
  );
}
