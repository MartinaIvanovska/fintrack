export interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  type: 'income' | 'expense';
  amount: number;
  date: string;
  category_id: string;
  category_name: string;
  description: string;
  payment_method?: string;
  merchant?: string;
  notes?: string;
  is_recurring: boolean;
  recurrence_rule?: string;
}

export interface Category {
  id: string;
  name: string;
  type: 'income' | 'expense';
  icon: string;
  is_default: boolean;
}

export interface Budget {
  id: string;
  category_id: string;
  category_name: string;
  category_icon: string;
  month_year: string;
  limit_amount: number;
  spent_amount: number;
  percentage: number;
}

export interface DashboardData {
  total_income: number;
  total_expenses: number;
  remaining_balance: number;
  savings_rate: number;
  spending_by_category: { name: string; value: number }[];
  monthly_trend: { month: string; expenses: number }[];
  income_vs_expenses: { month: string; income: number; expenses: number; savings: number }[];
  recent_transactions: {
    id: string;
    description: string;
    amount: number;
    type: string;
    date: string;
    category_name: string;
    category_icon: string;
  }[];
}
