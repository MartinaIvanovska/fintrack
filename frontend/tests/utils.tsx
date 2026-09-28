// Helpers for rendering the real app in tests.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { onTestFinished } from 'vitest';
import App from '../src/App';
import { TOKEN } from './msw/fixtures';
import { requests, RecordedRequest } from './msw/handlers';

/**
 * Render the whole app (router, AuthProvider, layout) at `path`, the way a
 * user arriving at that URL would see it. `signedIn` stores a valid token
 * first, so AuthContext restores the session through /api/auth/me.
 */
export function renderApp(path = '/', { signedIn = true } = {}) {
  if (signedIn) localStorage.setItem('token', TOKEN);
  window.history.pushState({}, '', path);
  const user = userEvent.setup();
  return { user, ...render(<App />) };
}

/** Wait until the signed-in layout has rendered the given page heading. */
export async function onPage(title: string) {
  return screen.findByRole('heading', { level: 1, name: title });
}

/**
 * The input/select/textarea in the form group labelled `label`. The app's
 * <label>s aren't linked to their inputs, so getByLabelText can't be used.
 */
export function field(label: string): HTMLInputElement {
  const labelEl = screen.getByText(label, { selector: 'label' });
  const control = labelEl.parentElement?.querySelector('input, select, textarea');
  if (!control) throw new Error(`no form control next to label "${label}"`);
  return control as HTMLInputElement;
}

/**
 * Record full-page redirects (`window.location.href = ...`) instead of
 * letting jsdom attempt a navigation it doesn't implement. Everything else
 * on window.location keeps working, so the router is unaffected. The real
 * location is put back when the test finishes.
 */
export function captureRedirects(): string[] {
  const original = window.location;
  const redirects: string[] = [];
  const proxy = new Proxy(original, {
    get: (target, prop) => {
      const value = Reflect.get(target, prop, target);
      return typeof value === 'function' ? value.bind(target) : value;
    },
    set: (target, prop, value) => {
      if (prop === 'href') {
        redirects.push(String(value));
        return true;
      }
      return Reflect.set(target, prop, value, target);
    },
  });
  Object.defineProperty(window, 'location', { configurable: true, value: proxy });
  onTestFinished(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: original });
  });
  return redirects;
}

/** Requests the app sent to `method path` during this test. */
export function sent(method: string, path: string): RecordedRequest[] {
  return requests.filter(r => r.method === method && r.path === path);
}
