import React, { useEffect, useState, useCallback } from 'react';
import { Plus, Search, Pencil, Trash2, X, ChevronLeft, ChevronRight } from 'lucide-react';
import api from '../api/client';
import { Transaction, Category } from '../types';

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

interface Props { type: 'income' | 'expense' }

const PAYMENT_METHODS = ['Cash', 'Credit Card', 'Debit Card', 'Bank Transfer', 'PayPal', 'Other'];

const TransactionsPage: React.FC<Props> = ({ type }) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [form, setForm] = useState<any>({
    description: '', amount: '', date: new Date().toISOString().split('T')[0],
    category_id: '', payment_method: '', merchant: '', notes: '', is_recurring: false,
  });

  const pageSize = 15;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/transactions', { params: { type, page, page_size: pageSize, search: search || undefined } });
      setTransactions(res.data.data);
      setTotal(res.data.total);
    } finally { setLoading(false); }
  }, [type, page, search]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get('/api/categories', { params: { type } }).then(res => setCategories(res.data.filter((c: Category) => c.type === type)));
  }, [type]);

  const openAdd = () => {
    setEditing(null);
    setForm({ description: '', amount: '', date: new Date().toISOString().split('T')[0], category_id: '', payment_method: '', merchant: '', notes: '', is_recurring: false });
    setShowModal(true);
  };

  const openEdit = (tx: Transaction) => {
    setEditing(tx);
    setForm({ description: tx.description, amount: String(tx.amount), date: tx.date.split('T')[0], category_id: tx.category_id, payment_method: tx.payment_method || '', merchant: tx.merchant || '', notes: tx.notes || '', is_recurring: tx.is_recurring });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { ...form, amount: parseFloat(form.amount), type, date: new Date(form.date).toISOString() };
    if (editing) {
      await api.put(`/api/transactions/${editing.id}`, payload);
    } else {
      await api.post('/api/transactions', payload);
    }
    setShowModal(false);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this transaction?')) return;
    await api.delete(`/api/transactions/${id}`);
    load();
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">{type === 'income' ? 'Income' : 'Expenses'}</h1>
          <p className="page-subtitle">{total} transaction{total !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn btn-primary" onClick={openAdd}><Plus size={16} /> Add {type === 'income' ? 'Income' : 'Expense'}</button>
      </div>

      <div className="section-card">
        <div className="table-toolbar">
          <div className="search-box">
            <Search size={16} className="search-icon" />
            <input className="search-input" placeholder="Search transactions…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} />
          </div>
        </div>

        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                {type === 'expense' && <><th>Merchant</th><th>Payment</th></>}
                <th>Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="table-loading"><div className="spinner" /></td></tr>
              ) : transactions.length === 0 ? (
                <tr><td colSpan={7} className="table-empty">No {type} entries yet. Add one to get started!</td></tr>
              ) : transactions.map(tx => (
                <tr key={tx.id}>
                  <td className="td-date">{new Date(tx.date).toLocaleDateString()}</td>
                  <td className="td-desc">{tx.description}{tx.is_recurring && <span className="badge badge-blue">Recurring</span>}</td>
                  <td><span className="cat-tag">{tx.category_name}</span></td>
                  {type === 'expense' && <><td>{tx.merchant || '—'}</td><td>{tx.payment_method || '—'}</td></>}
                  <td className={`td-amount ${type === 'income' ? 'amount--green' : 'amount--red'}`}>{type === 'income' ? '+' : '-'}{fmt(tx.amount)}</td>
                  <td className="td-actions">
                    <button className="icon-btn" onClick={() => openEdit(tx)}><Pencil size={14} /></button>
                    <button className="icon-btn icon-btn--danger" onClick={() => handleDelete(tx.id)}><Trash2 size={14} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <button className="page-btn" disabled={page === 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /></button>
            <span className="page-info">Page {page} of {totalPages}</span>
            <button className="page-btn" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}><ChevronRight size={16} /></button>
          </div>
        )}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editing ? 'Edit' : 'Add'} {type === 'income' ? 'Income' : 'Expense'}</h2>
              <button className="modal-close" onClick={() => setShowModal(false)}><X size={18} /></button>
            </div>
            <form className="modal-form" onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Description *</label>
                  <input required value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Amount *</label>
                  <input required type="number" min="0.01" step="0.01" value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Date *</label>
                  <input required type="date" value={form.date} onChange={e => setForm({ ...form, date: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>Category *</label>
                  <select required value={form.category_id} onChange={e => setForm({ ...form, category_id: e.target.value })}>
                    <option value="">Select category</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              </div>
              {type === 'expense' && (
                <div className="form-row">
                  <div className="form-group">
                    <label>Merchant</label>
                    <input value={form.merchant} onChange={e => setForm({ ...form, merchant: e.target.value })} />
                  </div>
                  <div className="form-group">
                    <label>Payment Method</label>
                    <select value={form.payment_method} onChange={e => setForm({ ...form, payment_method: e.target.value })}>
                      <option value="">Select method</option>
                      {PAYMENT_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </div>
                </div>
              )}
              <div className="form-group">
                <label>Notes</label>
                <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows={2} />
              </div>
              <div className="form-check">
                <input type="checkbox" id="recurring" checked={form.is_recurring} onChange={e => setForm({ ...form, is_recurring: e.target.checked })} />
                <label htmlFor="recurring">Recurring transaction</label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editing ? 'Save Changes' : 'Add Transaction'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionsPage;
