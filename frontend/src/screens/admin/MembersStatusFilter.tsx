import { STATUS_FILTER_OPTIONS, type StatusFilter } from './membersFilterSort';
import { MembersMultiSelectFilter } from './MembersMultiSelectFilter';

export function MembersStatusFilter({
  selected,
  onChange,
}: {
  selected: Set<StatusFilter>;
  onChange: (next: Set<StatusFilter>) => void;
}) {
  return (
    <MembersMultiSelectFilter
      label="filter by"
      options={STATUS_FILTER_OPTIONS}
      selected={selected}
      onChange={onChange}
      emptyLabel="everyone"
      manyLabel={(count) => `${String(count)} filters`}
    />
  );
}
