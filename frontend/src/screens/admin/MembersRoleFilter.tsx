import { MembersMultiSelectFilter } from './MembersMultiSelectFilter';

export function MembersRoleFilter({
  roleNames,
  selected,
  onChange,
}: {
  roleNames: string[];
  selected: Set<string>;
  onChange: (next: Set<string>) => void;
}) {
  return (
    <MembersMultiSelectFilter
      label="filter by role"
      options={roleNames.map((name) => ({ value: name, label: name }))}
      selected={selected}
      onChange={onChange}
      emptyLabel="all roles"
      manyLabel={(count) => `${String(count)} roles`}
    />
  );
}
