// The Reports page: generating the monthly summary and exporting the CSV
// (a blob the browser saves through a temporary download link).
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { report } from './msw/fixtures';
import { server } from './msw/server';
import { onPage, renderApp, sent } from './utils';

const currentMonth = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
};
const stat = (label: string) => screen.getByText(label, { selector: '.rs-label' }).nextElementSibling as HTMLElement;

describe('generating', () => {
  it('nothing is requested until the user asks for a report', async () => {
    renderApp('/reports');
    await onPage('Reports');
    expect(sent('GET', '/api/reports')).toHaveLength(0);
  });

  it('shows the figures for the selected month', async () => {
    const { user } = renderApp('/reports');
    await onPage('Reports');
    await user.click(screen.getByRole('button', { name: /Generate Report/ }));

    expect(await screen.findByText('Report for 2026-09')).toBeInTheDocument();
    expect(sent('GET', '/api/reports')[0].query).toEqual({ month_year: currentMonth() });
    expect(stat('Total Income')).toHaveTextContent('$3,000.00');
    expect(stat('Total Expenses')).toHaveTextContent('$150.00');
    expect(stat('Net Savings')).toHaveTextContent('$2,850.00');
    expect(stat('Net Savings')).toHaveClass('rs-value--green');
    expect(stat('Savings Rate')).toHaveTextContent('95.0%');
    expect(stat('Top Category')).toHaveTextContent('Food & Dining');
    expect(stat('Largest Expense')).toHaveTextContent('Groceries ($120.00)');
  });

  it('negative savings are shown in red and a month without expenses has no largest expense', async () => {
    server.use(http.get('/api/reports', () => HttpResponse.json({ ...report, savings: -40, largest_expense: null })));
    const { user } = renderApp('/reports');
    await onPage('Reports');
    await user.click(screen.getByRole('button', { name: /Generate Report/ }));

    await screen.findByText('Report for 2026-09');
    expect(stat('Net Savings')).toHaveClass('rs-value--red');
    expect(screen.queryByText('Largest Expense')).not.toBeInTheDocument();
  });

  it('uses the month chosen in the picker', async () => {
    const { user, container } = renderApp('/reports');
    await onPage('Reports');
    fireEvent.change(container.querySelector('input[type="month"]')!, { target: { value: '2025-12' } });
    await user.click(screen.getByRole('button', { name: /Generate Report/ }));
    await waitFor(() => expect(sent('GET', '/api/reports')[0].query).toEqual({ month_year: '2025-12' }));
  });

  it('shows a busy state while generating', async () => {
    server.use(http.get('/api/reports', async () => { await delay(200); return HttpResponse.json(report); }));
    const { user } = renderApp('/reports');
    await onPage('Reports');
    await user.click(screen.getByRole('button', { name: /Generate Report/ }));

    expect(screen.getByRole('button', { name: /Generating…/ })).toBeDisabled();
    await screen.findByText('Report for 2026-09');
  });
});

describe('CSV export', () => {
  it('downloads report_<month>.csv from the export endpoint', async () => {
    const createObjectURL = vi.fn(() => 'blob:report');
    const revokeObjectURL = vi.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const clicks: HTMLAnchorElement[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) { clicks.push(this); });

    const { user } = renderApp('/reports');
    await onPage('Reports');
    await user.click(screen.getByRole('button', { name: /Generate Report/ }));
    await user.click(await screen.findByRole('button', { name: /Export CSV/ }));

    await waitFor(() => expect(clicks).toHaveLength(1));
    expect(sent('GET', '/api/reports/export/csv')[0].query).toEqual({ month_year: currentMonth() });
    expect(clicks[0].download).toBe(`report_${currentMonth()}.csv`);
    expect(clicks[0].href).toBe('blob:report');
    expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:report');
  });
});
