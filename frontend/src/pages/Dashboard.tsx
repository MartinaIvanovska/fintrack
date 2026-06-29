import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, TrendingDown, Wallet, Percent } from 'lucide-react';
import api from '../api/client';
import { DashboardData } from '../types';

const COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#14b8a6'];

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n);

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/dashboard').then(res => {
      setData(res.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading"><div className="spinner" /></div>;
  if (!data) return <div className="page-empty">Failed to load dashboard.</div>;

  const cards = [
    { label: 'Total Income', value: fmt(data.total_income), icon: TrendingUp, color: 'green', sub: 'This month' },
    { label: 'Total Expenses', value: fmt(data.total_expenses), icon: TrendingDown, color: 'red', sub: 'This month' },
    { label: 'Remaining', value: fmt(data.remaining_balance), icon: Wallet, color: data.remaining_balance >= 0 ? 'green' : 'red', sub: 'Balance' },
    { label: 'Savings Rate', value: `${data.savings_rate.toFixed(1)}%`, icon: Percent, color: 'purple', sub: 'Of income saved' },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">{new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
      </div>

      <div className="cards-grid">
        {cards.map(({ label, value, icon: Icon, color, sub }) => (
          <div key={label} className={`stat-card stat-card--${color}`}>
            <div className="stat-card__header">
              <span className="stat-card__label">{label}</span>
              <div className={`stat-card__icon icon--${color}`}><Icon size={18} /></div>
            </div>
            <div className="stat-card__value">{value}</div>
            <div className="stat-card__sub">{sub}</div>
          </div>
        ))}
      </div>

      <div className="charts-grid">
        <div className="chart-card">
          <h3 className="chart-title">Spending by Category</h3>
          {data.spending_by_category.length === 0 ? (
            <div className="chart-empty">No expense data yet.</div>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={data.spending_by_category} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }: any) => `${name} ${((percent || 0) * 100).toFixed(0)}%`} labelLine={false}>
                  {data.spending_by_category.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: any) => fmt(Number(v))} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="chart-card">
          <h3 className="chart-title">Monthly Spending Trend</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.monthly_trend}>
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: any) => fmt(Number(v))} />
              <Line type="monotone" dataKey="expenses" stroke="#6366f1" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card chart-card--wide">
          <h3 className="chart-title">Income vs Expenses</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.income_vs_expenses} barGap={4}>
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: any) => fmt(Number(v))} />
              <Legend />
              <Bar dataKey="income" fill="#10b981" radius={[4, 4, 0, 0]} name="Income" />
              <Bar dataKey="expenses" fill="#f43f5e" radius={[4, 4, 0, 0]} name="Expenses" />
              <Bar dataKey="savings" fill="#6366f1" radius={[4, 4, 0, 0]} name="Savings" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="section-card">
        <h3 className="section-title">Recent Transactions</h3>
        {data.recent_transactions.length === 0 ? (
          <div className="table-empty">No transactions yet. Start by adding one!</div>
        ) : (
          <div className="tx-list">
            {data.recent_transactions.map(tx => (
              <div key={tx.id} className="tx-row">
                <div className="tx-cat-badge">{tx.category_name.charAt(0)}</div>
                <div className="tx-info">
                  <span className="tx-desc">{tx.description}</span>
                  <span className="tx-meta">{tx.category_name} · {new Date(tx.date).toLocaleDateString()}</span>
                </div>
                <span className={`tx-amount ${tx.type === 'income' ? 'amount--green' : 'amount--red'}`}>
                  {tx.type === 'income' ? '+' : '-'}{fmt(tx.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
