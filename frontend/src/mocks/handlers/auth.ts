// Auth + current-user handlers. These are the boot-critical ones: on load the
// app calls POST /api/auth/refresh/ (restoreSession), and a success here lands
// the app in the authed state so the main screens render.

import { http, HttpResponse } from 'msw';

import { MOCK_ACCESS_TOKEN, mockUser } from '../data/user';

export const authHandlers = [
  // Session restore + login both return an access token; the store then
  // fetches /me/ with it.
  http.post('/api/auth/refresh/', () => HttpResponse.json({ access: MOCK_ACCESS_TOKEN })),
  http.post('/api/auth/login/', () => HttpResponse.json({ access: MOCK_ACCESS_TOKEN })),
  http.post('/api/auth/logout/', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/auth/me/', () => HttpResponse.json(mockUser)),
  http.patch('/api/auth/me/', () => HttpResponse.json(mockUser)),
];
