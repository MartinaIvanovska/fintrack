// AuthContext, the sign-in / registration page and the route guard, rendered
// through the real <App/> with the API mocked by MSW.
import { screen } from '@testing-library/react';
import { http, HttpResponse, delay } from 'msw';
import { describe, expect, it } from 'vitest';
import { TOKEN, user as me } from './msw/fixtures';
import { server } from './msw/server';
import { captureRedirects, field, onPage, renderApp, sent } from './utils';

describe('route guard', () => {
  it.each(['/', '/expenses', '/budgets', '/reports', '/settings'])('signed out, %s shows the sign-in page', async path => {
    renderApp(path, { signedIn: false });
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(window.location.pathname).toBe('/auth');
    expect(sent('GET', '/api/auth/me')).toHaveLength(0);
  });

  it('signed in, /auth sends the user to the dashboard', async () => {
    renderApp('/auth');
    await onPage('Dashboard');
    expect(window.location.pathname).toBe('/');
  });

  it('unknown paths lead to the dashboard', async () => {
    renderApp('/does-not-exist');
    await onPage('Dashboard');
    expect(window.location.pathname).toBe('/');
  });
});

describe('session', () => {
  it('a stored token is restored through /api/auth/me', async () => {
    renderApp('/');
    await onPage('Dashboard');
    expect(screen.getByText(me.username)).toBeInTheDocument();
    expect(screen.getByText(me.email)).toBeInTheDocument();
    expect(sent('GET', '/api/auth/me')[0].authorization).toBe(`Bearer ${TOKEN}`);
  });

  it('a rejected token is discarded and the sign-in page is shown', async () => {
    const redirects = captureRedirects();
    localStorage.setItem('token', 'expired-token');
    renderApp('/', { signedIn: false });

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBeNull();
    expect(redirects).toEqual(['/login']);
  });

  it('logging out clears the token and returns to sign-in', async () => {
    const { user } = renderApp('/');
    await onPage('Dashboard');

    await user.click(screen.getByRole('button', { name: 'Log out' }));

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBeNull();
  });
});

describe('sign in', () => {
  it('sends the credentials, stores the token and opens the dashboard', async () => {
    const { user } = renderApp('/auth', { signedIn: false });
    await user.type(field('Email'), 'martina@example.com');
    await user.type(field('Password'), 'secret-1');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    await onPage('Dashboard');
    // The login endpoint is typed with the registration schema, so the UI
    // sends an empty username alongside the credentials.
    expect(sent('POST', '/api/auth/login')[0].body).toEqual({ email: 'martina@example.com', password: 'secret-1', username: '' });
    expect(localStorage.getItem('token')).toBe(TOKEN);
  });

  it('shows a waiting state while the request is in flight', async () => {
    server.use(http.post('/api/auth/login', async () => {
      await delay(200);
      return HttpResponse.json({ access_token: TOKEN, user: me });
    }));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.type(field('Email'), 'martina@example.com');
    await user.type(field('Password'), 'secret-1');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(screen.getByRole('button', { name: 'Please wait…' })).toBeDisabled();
    await onPage('Dashboard');
  });

  it('a wrong password shows the error message from the server', async () => {
    captureRedirects();
    server.use(http.post('/api/auth/login', () => HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.type(field('Email'), 'martina@example.com');
    await user.type(field('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument();
  });

  // In a real browser the message above is wiped out at once: the axios
  // interceptor treats every 401 - including a failed sign-in - as an
  // expired session and reloads the page at /login.
  it.fails('a failed sign-in does not trigger the session-expired redirect', async () => {
    const redirects = captureRedirects();
    server.use(http.post('/api/auth/login', () => HttpResponse.json({ detail: 'Invalid email or password' }, { status: 401 })));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.type(field('Email'), 'martina@example.com');
    await user.type(field('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    await screen.findByText('Invalid email or password');
    expect(redirects).toEqual([]);
  });
});

describe('registration', () => {
  it('switches to the registration form and creates the account', async () => {
    const { user } = renderApp('/auth', { signedIn: false });
    await user.click(screen.getByRole('button', { name: 'Register' }));
    expect(screen.getByRole('heading', { name: 'Create account' })).toBeInTheDocument();

    await user.type(field('Username'), 'newbie');
    await user.type(field('Email'), 'newbie@example.com');
    await user.type(field('Password'), 'pw-123456');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    await onPage('Dashboard');
    expect(sent('POST', '/api/auth/register')[0].body).toEqual({ username: 'newbie', email: 'newbie@example.com', password: 'pw-123456' });
  });

  it('shows the server error and stays on the form', async () => {
    server.use(http.post('/api/auth/register', () => HttpResponse.json({ detail: 'Email already registered' }, { status: 400 })));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.type(field('Username'), 'dup');
    await user.type(field('Email'), 'taken@example.com');
    await user.type(field('Password'), 'pw-123456');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    expect(await screen.findByText('Email already registered')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Account' })).toBeEnabled();
    expect(localStorage.getItem('token')).toBeNull();
  });

  it('shows a generic message when the server gives no reason', async () => {
    server.use(http.post('/api/auth/register', () => HttpResponse.error()));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.type(field('Username'), 'x');
    await user.type(field('Email'), 'x@example.com');
    await user.type(field('Password'), 'pw');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));

    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument();
  });

  it('switching between the forms clears an error', async () => {
    server.use(http.post('/api/auth/register', () => HttpResponse.json({ detail: 'Username already taken' }, { status: 400 })));
    const { user } = renderApp('/auth', { signedIn: false });
    await user.click(screen.getByRole('button', { name: 'Register' }));
    await user.type(field('Username'), 'dup');
    await user.type(field('Email'), 'd@example.com');
    await user.type(field('Password'), 'pw');
    await user.click(screen.getByRole('button', { name: 'Create Account' }));
    await screen.findByText('Username already taken');

    await user.click(screen.getByRole('button', { name: 'Sign In' }));

    expect(screen.queryByText('Username already taken')).not.toBeInTheDocument();
  });
});
