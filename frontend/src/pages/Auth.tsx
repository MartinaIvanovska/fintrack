import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Wallet } from 'lucide-react';

const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isLogin) {
        await login(form.email, form.password);
      } else {
        await register(form.username, form.email, form.password);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand">
          <div className="brand-icon brand-icon--lg"><Wallet size={28} /></div>
          <span className="brand-name brand-name--lg">Fintrack</span>
        </div>
        <h1 className="auth-headline">Your finances,<br />finally clear.</h1>
        <p className="auth-sub">Track income, control spending, and build towards your goals — all in one place.</p>
        <div className="auth-features">
          {['Real-time spending insights', 'Budget tracking & alerts', 'Subscription management', 'Detailed financial reports'].map(f => (
            <div key={f} className="auth-feature"><span className="feature-dot" />{f}</div>
          ))}
        </div>
      </div>

      <div className="auth-right">
        <div className="auth-card">
          <h2 className="auth-card-title">{isLogin ? 'Welcome back' : 'Create account'}</h2>
          <p className="auth-card-sub">{isLogin ? 'Sign in to your account' : 'Start tracking your finances'}</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            {!isLogin && (
              <div className="form-group">
                <label>Username</label>
                <input required placeholder="johndoe" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} />
              </div>
            )}
            <div className="form-group">
              <label>Email</label>
              <input required type="email" placeholder="you@example.com" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input required type="password" placeholder="••••••••" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
            {error && <div className="auth-error">{error}</div>}
            <button type="submit" className="btn btn-primary btn--full" disabled={loading}>
              {loading ? 'Please wait…' : isLogin ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="auth-toggle">
            {isLogin ? "Don't have an account? " : "Already have an account? "}
            <button className="link-btn" onClick={() => { setIsLogin(!isLogin); setError(''); }}>
              {isLogin ? 'Register' : 'Sign In'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
