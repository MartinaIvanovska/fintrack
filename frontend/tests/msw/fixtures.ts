// Realistic API responses shared by the handlers and the tests.
import type { Budget, Category, DashboardData, Transaction, User } from '../../src/types';

export const user: User = {
  id: 'u1',
  username: 'martina',
  email: 'martina@example.com',
  created_at: '2026-01-01T00:00:00',
};

export const TOKEN = 'test-token';

export const categories: Category[] = [
  { id: 'c-salary', name: 'Salary', type: 'income', icon: 'briefcase', is_default: true },
  { id: 'c-food', name: 'Food & Dining', type: 'expense', icon: 'utensils', is_default: true },
  { id: 'c-transport', name: 'Transport', type: 'expense', icon: 'car', is_default: true },
];

export const makeTransaction = (overrides: Partial<Transaction> = {}): Transaction => ({
  id: 't1',
  type: 'expense',
  amount: 42.5,
  date: '2026-09-10T00:00:00',
  category_id: 'c-food',
  category_name: 'Food & Dining',
  description: 'Groceries',
  payment_method: 'Credit Card',
  merchant: 'Market',
  notes: '',
  is_recurring: false,
  ...overrides,
});

export const makeBudget = (overrides: Partial<Budget> = {}): Budget => ({
  id: 'b1',
  category_id: 'c-food',
  category_name: 'Food & Dining',
  category_icon: 'utensils',
  month_year: '2026-09',
  limit_amount: 100,
  spent_amount: 40,
  percentage: 40,
  ...overrides,
});

export const dashboard: DashboardData = {
  total_income: 3000,
  total_expenses: 1250,
  remaining_balance: 1750,
  savings_rate: 58.3333,
  spending_by_category: [{ name: 'Food & Dining', value: 800 }, { name: 'Transport', value: 450 }],
  monthly_trend: [{ month: 'Aug', expenses: 1100 }, { month: 'Sep', expenses: 1250 }],
  income_vs_expenses: [{ month: 'Sep', income: 3000, expenses: 1250, savings: 1750 }],
  recent_transactions: [
    { id: 'r1', description: 'Salary', amount: 3000, type: 'income', date: '2026-09-01T00:00:00', category_name: 'Salary', category_icon: 'briefcase' },
    { id: 'r2', description: 'Rent', amount: 900, type: 'expense', date: '2026-09-02T00:00:00', category_name: 'Housing', category_icon: 'home' },
  ],
};

export const report = {
  month_year: '2026-09',
  total_income: 3000,
  total_expenses: 150,
  savings: 2850,
  savings_rate: 95,
  largest_expense: { description: 'Groceries', amount: 120 },
  top_spending_category: 'Food & Dining',
};
