import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import Footer from './Footer';
import Header from './Header';

const TITULOS = {
  '/': 'Folheia — Encontre seu próximo livro',
  '/biblioteca': 'Minha biblioteca — Folheia',
  '/login': 'Entrar — Folheia',
  '/cadastro': 'Criar conta — Folheia',
  '/404': 'Página não encontrada — Folheia',
};

function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' });
    document.title = TITULOS[pathname] || 'Folheia';
  }, [pathname]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>

      <Header />

      <main className="site-main" id="conteudo">
        <div className="page-transition" key={pathname}>
          <Outlet />
        </div>
      </main>

      <Footer />
    </div>
  );
}

export default Layout;
