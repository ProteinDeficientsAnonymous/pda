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

const GUIDELINES_TAB: TabOption = { value: 'guidelines', label: 'guidelines' };

// planners tick the checklist under each of their events in my events; this tab edits the list
const PLANNER_TABS: TabOption[] = [...OWN_TABS, GUIDELINES_TAB];

const MANAGER_TABS: TabOption[] = [
  ...OWN_TABS,
  { value: 'slots', label: 'slots' },
  { value: 'checklist', label: 'checklist' },
  GUIDELINES_TAB,
];

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
