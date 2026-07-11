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
