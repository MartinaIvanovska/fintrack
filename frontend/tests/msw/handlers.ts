// Default API behaviour for component tests. MSW intercepts the requests
// the real axios client sends (at the network level), so the app code under
// test - including its interceptors - runs unchanged. Individual tests
// override a handler with `server.use(...)` to simulate other responses.
import { http, HttpResponse } from 'msw';
import * as data from './fixtures';

export interface RecordedRequest {
  method: string;
  path: string;
  query: Record<string, string>;
  body: unknown;
  authorization: string | null;
}

/** Every request the app made during the current test, in order. */
export const requests: RecordedRequest[] = [];

/** Called for every request (see server.ts), whichever handler answers it. */
export function record(request: Request) {
  const url = new URL(request.url);
  const entry: RecordedRequest = {
    method: request.method,
    path: url.pathname,
    query: Object.fromEntries(url.searchParams),
    body: null,
    authorization: request.headers.get('Authorization'),
  };
  requests.push(entry);
  if (request.method !== 'GET' && request.method !== 'DELETE') {
    request.clone().text().then(text => { entry.body = text ? JSON.parse(text) : null; });
  }
}

export const handlers = [
  http.get('/api/auth/me', ({ request }) =>
    request.headers.get('Authorization') === `Bearer ${data.TOKEN}`
      ? HttpResponse.json(data.user)
      : HttpResponse.json({ detail: 'Could not validate credentials' }, { status: 401 })),
  http.post('/api/auth/login', () => HttpResponse.json({ access_token: data.TOKEN, token_type: 'bearer', user: data.user })),
  http.post('/api/auth/register', () => HttpResponse.json({ access_token: data.TOKEN, token_type: 'bearer', user: data.user }, { status: 201 })),
  http.put('/api/auth/me', async ({ request }) => HttpResponse.json({ ...data.user, ...(await request.json() as object) })),
  http.post('/api/auth/change-password', () => HttpResponse.json({ message: 'Password updated successfully' })),

  http.get('/api/categories', () => HttpResponse.json(data.categories)),

  http.get('/api/transactions', ({ request }) => {
    const type = new URL(request.url).searchParams.get('type') ?? 'expense';
    const tx = type === 'income'
      ? data.makeTransaction({ id: 't-in', type: 'income', description: 'Salary', amount: 3000, category_id: 'c-salary', category_name: 'Salary' })
      : data.makeTransaction();
    return HttpResponse.json({ total: 1, page: 1, page_size: 15, data: [tx] });
  }),
  http.post('/api/transactions', async ({ request }) => HttpResponse.json(data.makeTransaction({ id: 't-new', ...(await request.json() as object) }), { status: 201 })),
  http.put('/api/transactions/:id', async ({ request }) => HttpResponse.json(data.makeTransaction(await request.json() as object))),
  http.delete('/api/transactions/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/budgets', () => HttpResponse.json([data.makeBudget()])),
  http.post('/api/budgets', () => HttpResponse.json(data.makeBudget({ id: 'b-new' }), { status: 201 })),
  http.delete('/api/budgets/:id', () => new HttpResponse(null, { status: 204 })),

  http.get('/api/dashboard', () => HttpResponse.json(data.dashboard)),
  http.get('/api/reports', () => HttpResponse.json(data.report)),
  http.get('/api/reports/export/csv', () =>
    new HttpResponse('Date,Type,Description,Amount,Category,Payment Method,Merchant\n', {
      headers: { 'Content-Type': 'text/csv' },
    })),
];
