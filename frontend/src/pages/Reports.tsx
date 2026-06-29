import React, { useState } from 'react';
import { FileText, Download } from 'lucide-react';
import api from '../api/client';

const fmt = (n: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);

const Reports: React.FC = () => {
  const [monthYear, setMonthYear] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const res = await api.get('/api/reports', { params: { month_year: monthYear } });
    setReport(res.data);
    setLoading(false);
  };

  const exportCsv = async () => {
    const res = await api.get('/api/reports/export/csv', { params: { month_year: monthYear }, responseType: 'blob' });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url; a.download = `report_${monthYear}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Monthly financial summary</p>
        </div>
      </div>

      <div className="section-card">
        <div className="report-toolbar">
          <input type="month" className="month-picker" value={monthYear} onChange={e => setMonthYear(e.target.value)} />
          <button className="btn btn-primary" onClick={generate} disabled={loading}>
            <FileText size={16} /> {loading ? 'Generating…' : 'Generate Report'}
          </button>
        </div>

        {report && (
          <div className="report-content">
            <div className="report-header-row">
              <h2 className="report-title">Report for {report.month_year}</h2>
              <button className="btn btn-ghost" onClick={exportCsv}><Download size={16} /> Export CSV</button>
            </div>

            <div className="report-stats">
              <div className="report-stat"><span className="rs-label">Total Income</span><span className="rs-value rs-value--green">{fmt(report.total_income)}</span></div>
              <div className="report-stat"><span className="rs-label">Total Expenses</span><span className="rs-value rs-value--red">{fmt(report.total_expenses)}</span></div>
              <div className="report-stat"><span className="rs-label">Net Savings</span><span className={`rs-value ${report.savings >= 0 ? 'rs-value--green' : 'rs-value--red'}`}>{fmt(report.savings)}</span></div>
              <div className="report-stat"><span className="rs-label">Savings Rate</span><span className="rs-value rs-value--purple">{report.savings_rate.toFixed(1)}%</span></div>
              <div className="report-stat"><span className="rs-label">Top Category</span><span className="rs-value">{report.top_spending_category}</span></div>
              {report.largest_expense && (
                <div className="report-stat">
                  <span className="rs-label">Largest Expense</span>
                  <span className="rs-value">{report.largest_expense.description} ({fmt(report.largest_expense.amount)})</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;
