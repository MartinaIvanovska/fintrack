import React, { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import api from '../api/client';
import { Transaction } from '../types';

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

const Subscriptions: React.FC = () => {
  const [subscriptions, setSubscriptions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/transactions', { params: { type: 'expense', page_size: 100 } }).then(res => {
      setSubscriptions(res.data.data.filter((tx: Transaction) => tx.is_recurring));
      setLoading(false);
    });
  }, []);

  const yearlyTotal = subscriptions.reduce((sum, s) => sum + s.amount * 12, 0);

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Subscriptions</h1>
          <p className="page-subtitle">{subscriptions.length} active subscription{subscriptions.length !== 1 ? 's' : ''}</p>
        </div>
        {subscriptions.length > 0 && (
          <div className="stat-pill">Yearly total: <strong>{fmt(yearlyTotal)}</strong></div>
        )}
      </div>

      {loading ? <div className="page-loading"><div className="spinner" /></div> :
        subscriptions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><RefreshCw size={40} /></div>
            <h3>No subscriptions tracked</h3>
            <p>Mark transactions as recurring in the Expenses section to track them here.</p>
          </div>
        ) : (
          <div className="section-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Monthly</th>
                  <th>Yearly</th>
                  <th>Merchant</th>
                </tr>
              </thead>
              <tbody>
                {subscriptions.map(s => (
                  <tr key={s.id}>
                    <td className="td-desc">{s.description}</td>
                    <td><span className="cat-tag">{s.category_name}</span></td>
                    <td className="amount--red">{fmt(s.amount)}</td>
                    <td className="amount--red">{fmt(s.amount * 12)}</td>
                    <td>{s.merchant || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </div>
  );
};

export default Subscriptions;
