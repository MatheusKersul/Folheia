import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import Header from './Header';

function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [pathname]);

  return (
    <div className="app">
      <Header />
      <main className="container">
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
