// The Settings page: profile form and password form, including the
// client-side "passwords do not match" check and server error messages.
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { user as me } from './msw/fixtures';
import { server } from './msw/server';
import { field, onPage, renderApp, sent } from './utils';

async function openSettings() {
  const rendered = renderApp('/settings');
  await onPage('Settings');
  await waitFor(() => expect(field('Username').value).toBe(me.username));
  return rendered;
}

describe('profile', () => {
  it('is prefilled with the signed-in user', async () => {
    await openSettings();
    expect(field('Username').value).toBe(me.username);
    expect(field('Email').value).toBe(me.email);
  });

  it('saves the changes and confirms', async () => {
    const { user } = await openSettings();
    await user.clear(field('Username'));
    await user.type(field('Username'), 'renamed');
    await user.click(screen.getByRole('button', { name: 'Save Profile' }));

    expect(await screen.findByText('Profile updated successfully!')).toBeInTheDocument();
    expect(sent('PUT', '/api/auth/me')[0].body).toEqual({ username: 'renamed', email: me.email });
  });

  it.fails('the sidebar shows the new username straight away', async () => {
    const { user } = await openSettings();
    await user.clear(field('Username'));
    await user.type(field('Username'), 'renamed');
    await user.click(screen.getByRole('button', { name: 'Save Profile' }));
    await screen.findByText('Profile updated successfully!');

    expect(screen.getByText('renamed', { selector: '.user-name' })).toBeInTheDocument();
  });

  it('shows the reason the server gives', async () => {
    server.use(http.put('/api/auth/me', () => HttpResponse.json({ detail: 'Email already registered' }, { status: 400 })));
    const { user } = await openSettings();
    await user.click(screen.getByRole('button', { name: 'Save Profile' }));
    expect(await screen.findByText('Email already registered')).toBeInTheDocument();
  });

  it('shows a generic message when the request fails without a reason', async () => {
    server.use(http.put('/api/auth/me', () => HttpResponse.error()));
    const { user } = await openSettings();
    await user.click(screen.getByRole('button', { name: 'Save Profile' }));
    expect(await screen.findByText('Update failed')).toBeInTheDocument();
  });
});

describe('password', () => {
  it('catches mismatching passwords without contacting the server', async () => {
    const { user } = await openSettings();
    await user.type(field('Current Password'), 'old-pw');
    await user.type(field('New Password'), 'new-pw-1');
    await user.type(field('Confirm New Password'), 'new-pw-2');
    await user.click(screen.getByRole('button', { name: 'Change Password' }));

    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument();
    expect(sent('POST', '/api/auth/change-password')).toHaveLength(0);
  });

  it('changes the password and clears the form', async () => {
    const { user } = await openSettings();
    await user.type(field('Current Password'), 'old-pw');
    await user.type(field('New Password'), 'new-pw-1');
    await user.type(field('Confirm New Password'), 'new-pw-1');
    await user.click(screen.getByRole('button', { name: 'Change Password' }));

    expect(await screen.findByText('Password changed successfully!')).toBeInTheDocument();
    // The confirmation field is checked in the browser only; it isn't sent.
    expect(sent('POST', '/api/auth/change-password')[0].body).toEqual({ current_password: 'old-pw', new_password: 'new-pw-1' });
    expect(field('Current Password').value).toBe('');
    expect(field('New Password').value).toBe('');
    expect(field('Confirm New Password').value).toBe('');
  });

  it('shows the server error for a wrong current password', async () => {
    server.use(http.post('/api/auth/change-password', () => HttpResponse.json({ detail: 'Current password is incorrect' }, { status: 400 })));
    const { user } = await openSettings();
    await user.type(field('Current Password'), 'wrong');
    await user.type(field('New Password'), 'new-pw-1');
    await user.type(field('Confirm New Password'), 'new-pw-1');
    await user.click(screen.getByRole('button', { name: 'Change Password' }));

    expect(await screen.findByText('Current password is incorrect')).toBeInTheDocument();
  });

  it('shows a generic message when the request fails without a reason', async () => {
    server.use(http.post('/api/auth/change-password', () => HttpResponse.error()));
    const { user } = await openSettings();
    await user.type(field('Current Password'), 'a');
    await user.type(field('New Password'), 'b');
    await user.type(field('Confirm New Password'), 'b');
    await user.click(screen.getByRole('button', { name: 'Change Password' }));
    expect(await screen.findByText('Change failed')).toBeInTheDocument();
  });
});
