// Read-only overview pages: Dashboard, Analytics and Subscriptions.
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { dashboard, makeTransaction } from './msw/fixtures';
import { server } from './msw/server';
import { onPage, renderApp, sent } from './utils';

const statCard = (label: string) => screen.getByText(label, { selector: '.stat-card__label' }).closest('.stat-card') as HTMLElement;

describe('dashboard', () => {
  it('shows this month\'s figures, charts and recent transactions', async () => {
    const { container } = renderApp('/');
    await onPage('Dashboard');

    expect(await screen.findByText('$3,000', { selector: '.stat-card__value' })).toBeInTheDocument();
    expect(statCard('Total Expenses')).toHaveTextContent('$1,250');
    expect(statCard('Remaining')).toHaveTextContent('$1,750');
    expect(statCard('Remaining')).toHaveClass('stat-card--green');
    expect(statCard('Savings Rate')).toHaveTextContent('58.3%');
    expect(screen.getByText('Spending by Category')).toBeInTheDocument();
    expect(container.querySelectorAll('.recharts-responsive-container')).toHaveLength(3);

    expect(screen.getByText('Rent')).toBeInTheDocument();
    expect(screen.getByText('+$3,000', { selector: '.tx-amount' })).toBeInTheDocument();
    expect(screen.getByText('-$900', { selector: '.tx-amount' })).toBeInTheDocument();
  });

  it('a negative balance is shown in red and empty sections explain themselves', async () => {
    server.use(http.get('/api/dashboard', () => HttpResponse.json({
      ...dashboard, remaining_balance: -200, spending_by_category: [], recent_transactions: [],
    })));
    renderApp('/');
    await onPage('Dashboard');

    expect(await screen.findByText('No expense data yet.')).toBeInTheDocument();
    expect(screen.getByText('No transactions yet. Start by adding one!')).toBeInTheDocument();
    expect(statCard('Remaining')).toHaveClass('stat-card--red');
  });

  it('shows a message when the dashboard can\'t be loaded', async () => {
    server.use(http.get('/api/dashboard', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })));
    renderApp('/');
    expect(await screen.findByText('Failed to load dashboard.')).toBeInTheDocument();
  });
});

describe('analytics', () => {
  it('renders the three charts from the dashboard data', async () => {
    const { container } = renderApp('/analytics');
    await onPage('Analytics');
    expect(screen.getByText('Income vs Expenses vs Savings')).toBeInTheDocument();
    expect(container.querySelectorAll('.recharts-responsive-container')).toHaveLength(3);
    expect(sent('GET', '/api/dashboard')).toHaveLength(1);
  });

  it('renders nothing when the data can\'t be loaded', async () => {
    server.use(http.get('/api/dashboard', () => HttpResponse.json({ detail: 'boom' }, { status: 500 })));
    const { container } = renderApp('/analytics');
    await screen.findByText('Dashboard', { selector: 'a span' });
    await new Promise(r => setTimeout(r, 50));
    expect(container.querySelector('h1')).toBeNull();
  });
});

describe('subscriptions', () => {
  it('lists only recurring expenses with their yearly cost', async () => {
    server.use(http.get('/api/transactions', () => HttpResponse.json({
      total: 3, page: 1, page_size: 100, data: [
        makeTransaction({ id: 's1', description: 'Netflix', amount: 15.99, is_recurring: true, merchant: undefined }),
        makeTransaction({ id: 's2', description: 'Gym', amount: 30, is_recurring: true }),
        makeTransaction({ id: 'x', description: 'One-off lunch', amount: 12, is_recurring: false }),
      ],
    })));
    renderApp('/subscriptions');
    await onPage('Subscriptions');

    expect(await screen.findByText('Netflix')).toBeInTheDocument();
    expect(screen.queryByText('One-off lunch')).not.toBeInTheDocument();
    expect(screen.getByText('2 active subscriptions')).toBeInTheDocument();
    expect(screen.getByText('$191.88')).toBeInTheDocument(); // 15.99 x 12
    expect(screen.getByText('Yearly total:', { exact: false })).toHaveTextContent('Yearly total: $551.88');
    expect(sent('GET', '/api/transactions')[0].query).toEqual({ type: 'expense', page_size: '100' });
  });

  it('explains how to add subscriptions when there are none', async () => {
    server.use(http.get('/api/transactions', () => HttpResponse.json({ total: 0, page: 1, page_size: 100, data: [] })));
    renderApp('/subscriptions');
    expect(await screen.findByText('No subscriptions tracked')).toBeInTheDocument();
    expect(screen.getByText('0 active subscriptions')).toBeInTheDocument();
  });
});
