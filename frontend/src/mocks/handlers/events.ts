import { http, HttpResponse } from 'msw';

import { mockEventDetail, mockEventList } from '../data/events';

export const eventHandlers = [
  http.get('/api/community/events/', () => HttpResponse.json(mockEventList)),

  http.get('/api/community/events/:id/', ({ params }) =>
    HttpResponse.json({ ...mockEventDetail, id: String(params.id) }),
  ),
];
