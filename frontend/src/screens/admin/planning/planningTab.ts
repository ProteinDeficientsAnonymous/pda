export type PlanningTab = 'schedule' | 'mine' | 'slots';

export const TAB_OPTIONS: { value: PlanningTab; label: string }[] = [
  { value: 'schedule', label: 'schedule' },
  { value: 'mine', label: 'mine' },
  { value: 'slots', label: 'slots' },
];

export function resolveTab(raw: string | null, hasWaiting: boolean): PlanningTab {
  const valid = TAB_OPTIONS.find((o) => o.value === raw);
  if (valid) return valid.value;
  return hasWaiting ? 'mine' : 'schedule';
}
