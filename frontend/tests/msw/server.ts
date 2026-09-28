import { setupServer } from 'msw/node';
import { beforeEach } from 'vitest';
import { handlers, record, requests } from './handlers';

export const server = setupServer(...handlers);

// Record every request the app makes - also those answered by handlers a
// test adds with server.use() - so tests can assert on what was sent.
server.events.on('request:start', ({ request }) => record(request));

beforeEach(() => {
  requests.length = 0;
});
