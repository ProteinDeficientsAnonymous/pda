import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { EventType } from '@/models/event';

export type TypeFilter =
  | 'all'
  | typeof EventType.Official
  | typeof EventType.Club
  | typeof EventType.Community;

const TYPE_FILTER_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'all' },
  { value: EventType.Official, label: 'pda official' },
  { value: EventType.Club, label: 'pda club' },
  { value: EventType.Community, label: 'community' },
];

interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  typeFilter: TypeFilter;
  onTypeFilterChange: (value: TypeFilter) => void;
  date?: Date;
  onDateChange?: (date: Date) => void;
}

export function CalendarFilterBar({
  search,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  date,
  onDateChange,
}: Props) {
  return (
    <div className="mb-4 flex flex-col items-center gap-3">
      <div className="w-full max-w-xs">
        <TextField
          label="search events"
          placeholder="search by title"
          value={search}
          onChange={(e) => {
            onSearchChange(e.target.value);
          }}
        />
      </div>
      <SegmentedControl<TypeFilter>
        name="calendar-type-filter"
        ariaLabel="event type filter"
        options={TYPE_FILTER_OPTIONS}
        value={typeFilter}
        onChange={onTypeFilterChange}
      />
      {date && onDateChange ? (
        <div className="w-full max-w-xs">
          <DateTimePicker
            label="jump to date"
            value={date.toISOString()}
            onChange={(iso) => {
              if (iso) onDateChange(new Date(iso));
            }}
          />
        </div>
      ) : null}
    </div>
  );
}
