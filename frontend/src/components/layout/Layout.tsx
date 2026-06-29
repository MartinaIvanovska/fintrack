import React, { ReactNode } from 'react';
import Sidebar from './Sidebar';

const Layout: React.FC<{ children: ReactNode }> = ({ children }) => {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default Layout;
