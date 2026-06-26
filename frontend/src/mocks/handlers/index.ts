// Aggregated request handlers for mock mode.
//
// This is the foundation set: enough to boot the app authed and render the
// main screens (calendar, events, home, faq, guidelines, profile) with canned
// data. Requests with no handler fall through to MSW's default `warn`
// behavior, which surfaces in the console as a signal that the screen under
// test still needs a handler — added incrementally as later phases cover more
// screens.

import { authHandlers } from './auth';
import { contentHandlers } from './content';
import { eventHandlers } from './events';
import { notificationHandlers } from './notifications';

export const handlers = [
  ...authHandlers,
  ...eventHandlers,
  ...contentHandlers,
  ...notificationHandlers,
];
