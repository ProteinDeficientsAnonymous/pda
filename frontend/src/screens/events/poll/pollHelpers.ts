// Pure helpers for the datetime-poll feature. No React, no API calls — keeps
// the UI components thin and lets us unit-test sort/pick logic in isolation.

import type { EventPollOption } from '@/models/eventPoll';

// Chronological order (earliest first). Backend's display_order is the insert
// sequence; we use it only as a stable tie-break when two options share a
// datetime — which shouldn't happen in practice but guards against a rogue
// import script or a manual DB edit.
export function sortOptionsChrono(
  options: readonly EventPollOption[],
): readonly EventPollOption[] {
  return [...options].sort((a, b) => {
    const delta = a.datetime.getTime() - b.datetime.getTime();
    if (delta !== 0) return delta;
    return a.displayOrder - b.displayOrder;
  });
}

// Pre-select the option most likely to win when the host opens the finalize
// dialog: highest yes_count, ties broken by earliest datetime. Returns null
// for an empty list so the caller can handle it explicitly.
export function pickFinalizeDefault(
  options: readonly EventPollOption[],
): EventPollOption | null {
  if (options.length === 0) return null;
  return [...options].sort((a, b) => {
    if (b.yesCount !== a.yesCount) return b.yesCount - a.yesCount;
    return a.datetime.getTime() - b.datetime.getTime();
  })[0];
}
