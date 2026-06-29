import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

const Settings: React.FC = () => {
  const { user } = useAuth();
  const [profileForm, setProfileForm] = useState({ username: user?.username || '', email: user?.email || '' });
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm: '' });
  const [profileMsg, setProfileMsg] = useState('');
  const [pwMsg, setPwMsg] = useState('');

  const handleProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.put('/api/auth/me', profileForm);
      setProfileMsg('Profile updated successfully!');
    } catch (err: any) {
      setProfileMsg(err.response?.data?.detail || 'Update failed');
    }
  };

  const handlePw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pwForm.new_password !== pwForm.confirm) { setPwMsg('Passwords do not match'); return; }
    try {
      await api.post('/api/auth/change-password', { current_password: pwForm.current_password, new_password: pwForm.new_password });
      setPwMsg('Password changed successfully!');
      setPwForm({ current_password: '', new_password: '', confirm: '' });
    } catch (err: any) {
      setPwMsg(err.response?.data?.detail || 'Change failed');
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Manage your account</p>
      </div>

      <div className="settings-grid">
        <div className="section-card">
          <h3 className="section-title">Profile</h3>
          <form className="modal-form" onSubmit={handleProfile}>
            <div className="form-group">
              <label>Username</label>
              <input value={profileForm.username} onChange={e => setProfileForm({ ...profileForm, username: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={profileForm.email} onChange={e => setProfileForm({ ...profileForm, email: e.target.value })} />
            </div>
            {profileMsg && <p className="form-msg">{profileMsg}</p>}
            <button type="submit" className="btn btn-primary">Save Profile</button>
          </form>
        </div>

        <div className="section-card">
          <h3 className="section-title">Change Password</h3>
          <form className="modal-form" onSubmit={handlePw}>
            <div className="form-group">
              <label>Current Password</label>
              <input type="password" value={pwForm.current_password} onChange={e => setPwForm({ ...pwForm, current_password: e.target.value })} />
            </div>
            <div className="form-group">
              <label>New Password</label>
              <input type="password" value={pwForm.new_password} onChange={e => setPwForm({ ...pwForm, new_password: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Confirm New Password</label>
              <input type="password" value={pwForm.confirm} onChange={e => setPwForm({ ...pwForm, confirm: e.target.value })} />
            </div>
            {pwMsg && <p className="form-msg">{pwMsg}</p>}
            <button type="submit" className="btn btn-primary">Change Password</button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Settings;
