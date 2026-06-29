import React, { useEffect, useState } from 'react';
import { Plus, X, Trash2, AlertTriangle } from 'lucide-react';
import api from '../api/client';
import { Budget, Category } from '../types';

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n);

const BudgetsPage: React.FC = () => {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [monthYear, setMonthYear] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ category_id: '', limit_amount: '' });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    const res = await api.get('/api/budgets', { params: { month_year: monthYear } });
    setBudgets(res.data);
    setLoading(false);
  };

  useEffect(() => { load(); }, [monthYear]);
  useEffect(() => {
    api.get('/api/categories').then(res => setCategories(res.data.filter((c: Category) => c.type === 'expense')));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.post('/api/budgets', { ...form, limit_amount: parseFloat(form.limit_amount), month_year: monthYear });
    setShowModal(false);
    setForm({ category_id: '', limit_amount: '' });
    load();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this budget?')) return;
    await api.delete(`/api/budgets/${id}`);
    load();
  };

  const usedCategoryIds = new Set(budgets.map(b => b.category_id));
  const availableCategories = categories.filter(c => !usedCategoryIds.has(c.id));

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Budgets</h1>
          <p className="page-subtitle">Monthly spending limits</p>
        </div>
        <div className="header-actions">
          <input type="month" className="month-picker" value={monthYear} onChange={e => setMonthYear(e.target.value)} />
          <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> Add Budget</button>
        </div>
      </div>

      {loading ? (
        <div className="page-loading"><div className="spinner" /></div>
      ) : budgets.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <h3>No budgets set</h3>
          <p>Set spending limits for each category to track your progress.</p>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}><Plus size={16} /> Create Budget</button>
        </div>
      ) : (
        <div className="budgets-grid">
          {budgets.map(budget => {
            const over = budget.percentage >= 100;
            const warning = budget.percentage >= 80 && !over;
            return (
              <div key={budget.id} className={`budget-card ${over ? 'budget-card--over' : warning ? 'budget-card--warning' : ''}`}>
                <div className="budget-header">
                  <div className="budget-cat">
                    <span className="budget-cat-icon">{budget.category_name.charAt(0)}</span>
                    <span className="budget-cat-name">{budget.category_name}</span>
                  </div>
                  <div className="budget-actions">
                    {(over || warning) && <AlertTriangle size={16} className={over ? 'icon-red' : 'icon-amber'} />}
                    <button className="icon-btn icon-btn--danger" onClick={() => handleDelete(budget.id)}><Trash2 size={14} /></button>
                  </div>
                </div>
                <div className="budget-amounts">
                  <span className="budget-spent">{fmt(budget.spent_amount)}</span>
                  <span className="budget-limit"> / {fmt(budget.limit_amount)}</span>
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${over ? 'progress-fill--red' : warning ? 'progress-fill--amber' : 'progress-fill--green'}`}
                    style={{ width: `${Math.min(budget.percentage, 100)}%` }}
                  />
                </div>
                <div className="budget-footer">
                  <span className={`budget-pct ${over ? 'text-red' : warning ? 'text-amber' : 'text-muted'}`}>{budget.percentage.toFixed(0)}%</span>
                  <span className="budget-remaining">{over ? `${fmt(budget.spent_amount - budget.limit_amount)} over` : `${fmt(budget.limit_amount - budget.spent_amount)} left`}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal modal--sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Budget</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>
            <form className="modal-form" onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Category *</label>
                <select required value={form.category_id} onChange={e => setForm({ ...form, category_id: e.target.value })}>
                  <option value="">Select category</option>
                  {availableCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Monthly Limit ($) *</label>
                <input required type="number" min="1" step="1" value={form.limit_amount} onChange={e => setForm({ ...form, limit_amount: e.target.value })} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Budget</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default BudgetsPage;
