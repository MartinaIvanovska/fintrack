// The Income / Expenses page (one component with a `type` prop): listing,
// the add/edit modal, deleting with confirmation, search and pagination.
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { makeTransaction } from './msw/fixtures';
import { server } from './msw/server';
import { field, onPage, renderApp, sent } from './utils';

const row = (text: string) => screen.getByText(text).closest('tr') as HTMLElement;
const editButton = (r: HTMLElement) => r.querySelector('.icon-btn:not(.icon-btn--danger)') as HTMLElement;
const deleteButton = (r: HTMLElement) => r.querySelector('.icon-btn--danger') as HTMLElement;

function listReturns(transactions: ReturnType<typeof makeTransaction>[], total = transactions.length) {
  server.use(http.get('/api/transactions', () => HttpResponse.json({ total, page: 1, page_size: 15, data: transactions })));
}

describe('listing', () => {
  it('shows expenses with category, merchant, payment method and a negative amount', async () => {
    renderApp('/expenses');
    await onPage('Expenses');

    const r = row(await screen.findByText('Groceries').then(el => el.textContent!));
    expect(within(r).getByText('Food & Dining')).toBeInTheDocument();
    expect(within(r).getByText('Market')).toBeInTheDocument();
    expect(within(r).getByText('Credit Card')).toBeInTheDocument();
    expect(within(r).getByText('-$42.50')).toBeInTheDocument();
    expect(screen.getByText('1 transaction')).toBeInTheDocument();
  });

  it('shows income with a positive amount and without merchant columns', async () => {
    renderApp('/income');
    await onPage('Income');

    expect(await screen.findByText('+$3,000.00')).toBeInTheDocument();
    expect(screen.queryByRole('columnheader', { name: 'Merchant' })).not.toBeInTheDocument();
  });

  it('requests the first page of the right type', async () => {
    renderApp('/income');
    await screen.findByText('+$3,000.00');
    expect(sent('GET', '/api/transactions')[0].query).toEqual({ type: 'income', page: '1', page_size: '15' });
  });

  it('marks recurring transactions', async () => {
    listReturns([makeTransaction({ description: 'Netflix', is_recurring: true })]);
    renderApp('/expenses');
    expect(await screen.findByText('Recurring')).toBeInTheDocument();
  });

  it('shows an empty state', async () => {
    listReturns([]);
    renderApp('/expenses');
    expect(await screen.findByText('No expense entries yet. Add one to get started!')).toBeInTheDocument();
    expect(screen.getByText('0 transactions')).toBeInTheDocument();
  });

  it('shows missing merchant and payment method as a dash', async () => {
    listReturns([makeTransaction({ merchant: undefined, payment_method: undefined })]);
    renderApp('/expenses');
    const r = row((await screen.findByText('Groceries')).textContent!);
    expect(within(r).getAllByText('—')).toHaveLength(2);
  });
});

describe('adding', () => {
  it('only offers categories of the page type', async () => {
    const { user } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.click(screen.getByRole('button', { name: /Add Expense/ }));

    const options = Array.from(field('Category *').querySelectorAll('option')).map(o => o.textContent);
    expect(options).toEqual(['Select category', 'Food & Dining', 'Transport']);
  });

  it('sends the new transaction and reloads the list', async () => {
    const { user } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.click(screen.getByRole('button', { name: /Add Expense/ }));
    expect(screen.getByRole('heading', { name: 'Add Expense' })).toBeInTheDocument();

    await user.type(field('Description *'), 'Train ticket');
    await user.type(field('Amount *'), '12.5');
    await user.clear(field('Date *'));
    await user.type(field('Date *'), '2026-09-15');
    await user.selectOptions(field('Category *'), 'Transport');
    await user.type(field('Merchant'), 'Rail Co');
    await user.selectOptions(field('Payment Method'), 'Debit Card');
    await user.type(field('Notes'), 'commute');
    await user.click(screen.getByLabelText('Recurring transaction'));
    await user.click(screen.getByRole('button', { name: 'Add Transaction' }));

    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Add Expense' })).not.toBeInTheDocument());
    expect(sent('POST', '/api/transactions')[0].body).toEqual({
      description: 'Train ticket',
      amount: 12.5,
      date: '2026-09-15T00:00:00.000Z',
      category_id: 'c-transport',
      payment_method: 'Debit Card',
      merchant: 'Rail Co',
      notes: 'commute',
      is_recurring: true,
      type: 'expense',
    });
    await waitFor(() => expect(sent('GET', '/api/transactions')).toHaveLength(2));
  });

  it('defaults the date to today', async () => {
    const { user } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.click(screen.getByRole('button', { name: /Add Expense/ }));
    expect(field('Date *').value).toBe(new Date().toISOString().split('T')[0]);
  });

  it('cancelling closes the modal without sending anything', async () => {
    const { user } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.click(screen.getByRole('button', { name: /Add Expense/ }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByRole('heading', { name: 'Add Expense' })).not.toBeInTheDocument();
    expect(sent('POST', '/api/transactions')).toHaveLength(0);
  });

  it('clicking outside the dialog closes it', async () => {
    const { user, container } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.click(screen.getByRole('button', { name: /Add Expense/ }));
    await user.click(container.querySelector('.modal-overlay')!);
    expect(screen.queryByRole('heading', { name: 'Add Expense' })).not.toBeInTheDocument();
  });
});

describe('editing', () => {
  it('opens the modal with the current values and sends the change', async () => {
    const { user } = renderApp('/expenses');
    const r = row((await screen.findByText('Groceries')).textContent!);
    await user.click(editButton(r));

    expect(screen.getByRole('heading', { name: 'Edit Expense' })).toBeInTheDocument();
    expect(field('Description *').value).toBe('Groceries');
    expect(field('Amount *').value).toBe('42.5');
    expect(field('Date *').value).toBe('2026-09-10');
    expect(field('Category *').value).toBe('c-food');

    await user.clear(field('Description *'));
    await user.type(field('Description *'), 'Big shop');
    await user.click(screen.getByRole('button', { name: 'Save Changes' }));

    await waitFor(() => expect(sent('PUT', '/api/transactions/t1')).toHaveLength(1));
    expect(sent('PUT', '/api/transactions/t1')[0].body).toMatchObject({ description: 'Big shop', amount: 42.5 });
    expect(sent('POST', '/api/transactions')).toHaveLength(0);
  });
});

describe('deleting', () => {
  it('asks for confirmation, deletes and reloads', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { user } = renderApp('/expenses');
    await user.click(deleteButton(row((await screen.findByText('Groceries')).textContent!)));

    expect(confirm).toHaveBeenCalledWith('Delete this transaction?');
    await waitFor(() => expect(sent('DELETE', '/api/transactions/t1')).toHaveLength(1));
    await waitFor(() => expect(sent('GET', '/api/transactions')).toHaveLength(2));
  });

  it('does nothing when the confirmation is declined', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const { user } = renderApp('/expenses');
    await user.click(deleteButton(row((await screen.findByText('Groceries')).textContent!)));
    expect(sent('DELETE', '/api/transactions/t1')).toHaveLength(0);
  });
});

describe('search and pagination', () => {
  it('searching sends the text and goes back to page 1', async () => {
    const { user } = renderApp('/expenses');
    await screen.findByText('Groceries');
    await user.type(screen.getByPlaceholderText('Search transactions…'), 'mark');

    await waitFor(() => expect(sent('GET', '/api/transactions').at(-1)!.query).toMatchObject({ search: 'mark', page: '1' }));
  });

  it('shows page controls for more than one page and requests the next page', async () => {
    listReturns([makeTransaction()], 40);
    const { user, container } = renderApp('/expenses');
    expect(await screen.findByText('Page 1 of 3')).toBeInTheDocument();
    const [prev, next] = Array.from(container.querySelectorAll<HTMLButtonElement>('.page-btn'));
    expect(prev).toBeDisabled();

    await user.click(next);

    expect(await screen.findByText('Page 2 of 3')).toBeInTheDocument();
    expect(sent('GET', '/api/transactions').at(-1)!.query.page).toBe('2');
  });

  it('hides page controls when everything fits on one page', async () => {
    renderApp('/expenses');
    await screen.findByText('Groceries');
    expect(screen.queryByText(/^Page \d+ of/)).not.toBeInTheDocument();
  });
});
