// MSW browser worker. Started by enableMocking() before the app renders.

import { setupWorker } from 'msw/browser';

import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
