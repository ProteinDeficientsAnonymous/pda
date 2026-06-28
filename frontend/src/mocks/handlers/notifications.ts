// Notification handlers — the bell's unread count, list, and mark-read calls.

import { http, HttpResponse } from 'msw';

import { mockNotifications, mockUnreadCount } from '../data/content';

export const notificationHandlers = [
  http.get('/api/notifications/', () => HttpResponse.json(mockNotifications)),
  http.get('/api/notifications/unread-count/', () => HttpResponse.json(mockUnreadCount)),
  http.post('/api/notifications/:id/read/', () => new HttpResponse(null, { status: 204 })),
  http.post('/api/notifications/read-all/', () => new HttpResponse(null, { status: 204 })),
];
