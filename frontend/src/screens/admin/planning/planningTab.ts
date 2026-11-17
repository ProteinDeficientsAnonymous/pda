export type PlanningTab =
  | 'schedule'
  | 'events'
  | 'availability'
  | 'slots'
  | 'checklist'
  | 'guidelines';

interface TabOption {
  value: PlanningTab;
  label: string;
}

const OWN_TABS: TabOption[] = [
  { value: 'schedule', label: 'schedule' },
  { value: 'events', label: 'my events' },
  { value: 'availability', label: 'my availability' },
];

const GUIDE_TABS: TabOption[] = [
  { value: 'checklist', label: 'checklist' },
  { value: 'guidelines', label: 'guidelines' },
];

const PLANNER_TABS: TabOption[] = [...OWN_TABS, ...GUIDE_TABS];

const MANAGER_TABS: TabOption[] = [...OWN_TABS, { value: 'slots', label: 'slots' }, ...GUIDE_TABS];

export function tabOptions(canManage: boolean): TabOption[] {
  return canManage ? MANAGER_TABS : PLANNER_TABS;
}

// ?tab=mine predates the events/availability split; old links still land on events
export function explicitTab(raw: string | null, canManage: boolean): PlanningTab | null {
  const value = raw === 'mine' ? 'events' : raw;
  return tabOptions(canManage).find((o) => o.value === value)?.value ?? null;
}

export function resolveTab(
  raw: string | null,
  hasWaiting: boolean,
  canManage: boolean,
): PlanningTab {
  return explicitTab(raw, canManage) ?? (hasWaiting || !canManage ? 'events' : 'schedule');
}
