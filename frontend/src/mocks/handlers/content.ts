import { http, HttpResponse } from 'msw';

import {
  mockCalendarToken,
  mockFaq,
  mockGuidelines,
  mockHome,
  mockVersion,
  mockWelcomeTemplate,
} from '../data/content';

export const contentHandlers = [
  http.get('/api/community/home/', () => HttpResponse.json(mockHome)),
  http.get('/api/community/faq/', () => HttpResponse.json(mockFaq)),
  http.get('/api/community/guidelines/', () => HttpResponse.json(mockGuidelines)),
  http.get('/api/community/welcome-template/', () => HttpResponse.json(mockWelcomeTemplate)),
  http.get('/api/community/version/', () => HttpResponse.json(mockVersion)),

  http.get('/api/community/calendar/token/', () => HttpResponse.json(mockCalendarToken)),
  http.post('/api/community/calendar/token/', () => HttpResponse.json(mockCalendarToken)),
];
