export type PlanningTab = 'schedule' | 'events' | 'availability' | 'slots';

interface TabOption {
  value: PlanningTab;
  label: string;
}

const PLANNER_TABS: TabOption[] = [
  { value: 'schedule', label: 'schedule' },
  { value: 'events', label: 'my events' },
  { value: 'availability', label: 'my availability' },
];

const MANAGER_TABS: TabOption[] = [...PLANNER_TABS, { value: 'slots', label: 'slots' }];

export function withTab(prev: URLSearchParams, tab: PlanningTab): URLSearchParams {
  const p = new URLSearchParams(prev);
  p.set('tab', tab);
  return p;
}

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
