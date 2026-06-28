import { http, HttpResponse } from 'msw';

import { MOCK_ACCESS_TOKEN, mockUser } from '../data/user';

export const authHandlers = [
  http.post('/api/auth/refresh/', () => HttpResponse.json({ access: MOCK_ACCESS_TOKEN })),
  http.post('/api/auth/login/', () => HttpResponse.json({ access: MOCK_ACCESS_TOKEN })),
  http.post('/api/auth/logout/', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/auth/me/', () => HttpResponse.json(mockUser)),
  http.patch('/api/auth/me/', () => HttpResponse.json(mockUser)),
];
