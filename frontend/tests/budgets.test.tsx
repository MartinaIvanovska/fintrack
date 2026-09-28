// The Budgets page: cards and their alert states, creating a budget for the
// selected month, month switching and deleting with confirmation.
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { makeBudget } from './msw/fixtures';
import { server } from './msw/server';
import { field, onPage, renderApp, sent } from './utils';

const currentMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};
const card = (category: string) => screen.getByText(category, { selector: '.budget-cat-name' }).closest('.budget-card') as HTMLElement;

function budgetsReturn(...budgets: ReturnType<typeof makeBudget>[]) {
  server.use(http.get('/api/budgets', () => HttpResponse.json(budgets)));
}

describe('cards', () => {
  it('loads the current month and shows spending against the limit', async () => {
    renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });

    expect(sent('GET', '/api/budgets')[0].query).toEqual({ month_year: currentMonth() });
    const c = card('Food & Dining');
    expect(c).toHaveTextContent('$40 / $100');
    expect(c).toHaveTextContent('40%');
    expect(c).toHaveTextContent('$60 left');
    expect(c.className).toBe('budget-card ');
  });

  it.each([
    [79, '', '$21 left'],
    [80, 'budget-card--warning', '$20 left'],
    [99, 'budget-card--warning', '$1 left'],
    [120, 'budget-card--over', '$20 over'],
  ])('spending %i of 100 gives state "%s"', async (spent, state, remaining) => {
    budgetsReturn(makeBudget({ spent_amount: spent, percentage: Math.min(spent, 100) }));
    renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });

    const c = card('Food & Dining');
    expect(c.className.trim()).toBe(`budget-card ${state}`.trim());
    expect(c).toHaveTextContent(remaining);
    expect(c.querySelector('.icon-red, .icon-amber') !== null).toBe(state !== '');
  });

  it.fails('spending exactly the limit is not shown as "over"', async () => {
    budgetsReturn(makeBudget({ spent_amount: 100, percentage: 100 }));
    renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    expect(card('Food & Dining')).not.toHaveTextContent('over');
  });

  it('shows an empty state whose button opens the form', async () => {
    budgetsReturn();
    const { user } = renderApp('/budgets');
    expect(await screen.findByText('No budgets set')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Create Budget/ }));
    expect(screen.getByRole('heading', { name: 'New Budget' })).toBeInTheDocument();
  });
});

describe('creating', () => {
  it('only offers expense categories that have no budget yet', async () => {
    const { user } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    await user.click(screen.getByRole('button', { name: /Add Budget/ }));

    const options = Array.from(field('Category *').querySelectorAll('option')).map(o => o.textContent);
    expect(options).toEqual(['Select category', 'Transport']);
  });

  it('sends the budget for the selected month and reloads', async () => {
    const { user } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    await user.click(screen.getByRole('button', { name: /Add Budget/ }));
    await user.selectOptions(field('Category *'), 'Transport');
    await user.type(field('Monthly Limit ($) *'), '250');
    await user.click(screen.getByRole('button', { name: 'Create Budget' }));

    await waitFor(() => expect(sent('POST', '/api/budgets')).toHaveLength(1));
    expect(sent('POST', '/api/budgets')[0].body).toEqual({ category_id: 'c-transport', limit_amount: 250, month_year: currentMonth() });
    expect(screen.queryByRole('heading', { name: 'New Budget' })).not.toBeInTheDocument();
    await waitFor(() => expect(sent('GET', '/api/budgets')).toHaveLength(2));
  });

  it('cancelling closes the form without sending anything', async () => {
    const { user } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    await user.click(screen.getByRole('button', { name: /Add Budget/ }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('heading', { name: 'New Budget' })).not.toBeInTheDocument();
    expect(sent('POST', '/api/budgets')).toHaveLength(0);
  });
});

describe('month and deleting', () => {
  it('choosing another month reloads that month', async () => {
    const { container } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    const picker = container.querySelector('input[type="month"]') as HTMLInputElement;
    expect(picker.value).toBe(currentMonth());

    fireEvent.change(picker, { target: { value: '2025-12' } });

    await waitFor(() => expect(sent('GET', '/api/budgets').at(-1)!.query).toEqual({ month_year: '2025-12' }));
  });

  it('deletes after confirmation and reloads', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { user } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    await user.click(card('Food & Dining').querySelector('.icon-btn--danger')!);

    expect(confirm).toHaveBeenCalledWith('Delete this budget?');
    await waitFor(() => expect(sent('DELETE', '/api/budgets/b1')).toHaveLength(1));
    await waitFor(() => expect(sent('GET', '/api/budgets')).toHaveLength(2));
  });

  it('keeps the budget when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const { user } = renderApp('/budgets');
    await screen.findByText('Food & Dining', { selector: '.budget-cat-name' });
    await user.click(card('Food & Dining').querySelector('.icon-btn--danger')!);
    expect(sent('DELETE', '/api/budgets/b1')).toHaveLength(0);
  });
});

it('the page heading is shown', async () => {
  renderApp('/budgets');
  await onPage('Budgets');
});
