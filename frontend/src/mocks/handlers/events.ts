// Event list + detail handlers. The detail handler matches any id and returns
// the same canned event (with its id swapped in) so deep links render.

import { http, HttpResponse } from 'msw';

import { mockEventDetail, mockEventList } from '../data/events';

export const eventHandlers = [
  http.get('/api/community/events/', () => HttpResponse.json(mockEventList)),

  http.get('/api/community/events/:id/', ({ params }) =>
    HttpResponse.json({ ...mockEventDetail, id: String(params.id) }),
  ),
];
