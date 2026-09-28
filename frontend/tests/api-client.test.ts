// The shared axios client (src/api/client.ts) on its own: the request
// interceptor that attaches the stored token, and the response interceptor
// that ends the session on 401. Responses come from MSW, so these are real
// HTTP round trips through axios, not mocked function calls.
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import api from '../src/api/client';
import { server } from './msw/server';
import { captureRedirects, sent } from './utils';

describe('request interceptor', () => {
  it('sends the stored token as a Bearer header', async () => {
    localStorage.setItem('token', 'abc123');
    await api.get('/api/dashboard');
    expect(sent('GET', '/api/dashboard')[0].authorization).toBe('Bearer abc123');
  });

  it('sends no Authorization header when signed out', async () => {
    await api.get('/api/dashboard');
    expect(sent('GET', '/api/dashboard')[0].authorization).toBeNull();
  });

  it('uses the same-origin /api path (no hard-coded host)', async () => {
    await api.get('/api/dashboard');
    expect(api.defaults.baseURL).toBe('');
    expect(sent('GET', '/api/dashboard')[0].path).toBe('/api/dashboard');
  });
});

describe('response interceptor', () => {
  it('passes successful responses through unchanged', async () => {
    const res = await api.get('/api/reports');
    expect(res.status).toBe(200);
    expect(res.data.month_year).toBe('2026-09');
  });

  it('on 401 clears the token, redirects to /login and still rejects', async () => {
    const redirects = captureRedirects();
    localStorage.setItem('token', 'expired');
    server.use(http.get('/api/dashboard', () => HttpResponse.json({ detail: 'expired' }, { status: 401 })));

    await expect(api.get('/api/dashboard')).rejects.toMatchObject({ response: { status: 401 } });
    expect(localStorage.getItem('token')).toBeNull();
    expect(redirects).toEqual(['/login']);
  });

  it.each([400, 403, 404, 422, 500])('on %i keeps the session and just rejects', async status => {
    const redirects = captureRedirects();
    localStorage.setItem('token', 'still-valid');
    server.use(http.get('/api/dashboard', () => HttpResponse.json({ detail: 'nope' }, { status })));

    await expect(api.get('/api/dashboard')).rejects.toMatchObject({ response: { status } });
    expect(localStorage.getItem('token')).toBe('still-valid');
    expect(redirects).toEqual([]);
  });

  it('a network failure rejects without a response and keeps the session', async () => {
    localStorage.setItem('token', 'still-valid');
    server.use(http.get('/api/dashboard', () => HttpResponse.error()));

    await expect(api.get('/api/dashboard')).rejects.toMatchObject({ message: 'Network Error' });
    expect(localStorage.getItem('token')).toBe('still-valid');
  });
});
