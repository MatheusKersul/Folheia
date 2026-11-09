import { Link, NavLink, useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';

import { useAuth } from '../auth/useAuth';
import HeaderDecoration from '../HeaderDecoration';

function classeNavLink({ isActive }) {
  return isActive ? 'nav-link active' : 'nav-link';
}

function Header() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  const sair = () => {
    logout();
    navigate('/');
  };

  return (
    <>
      <header className="header">
        <HeaderDecoration />
        <Link to="/" className="header-title-link">
          <h1>Folheia</h1>
        </Link>

        <Link
          to="/admin"
          className="btn-header-admin"
          title="Acessar o Painel do Administrador (Telemetria do Redis e Workers)"
        >
          <ShieldCheck size={16} />
          <span className="btn-header-admin-text">Painel Admin</span>
        </Link>
      </header>

      <nav className="navbar">
        <div className="navbar-inner">
          <div className="navbar-links">
            <NavLink to="/" end className={classeNavLink}>
              Buscar
            </NavLink>
            <NavLink to="/biblioteca" className={classeNavLink}>
              Minha Biblioteca
            </NavLink>
          </div>

          <div className="navbar-user">
            {usuario ? (
              <>
                <span className="navbar-user-name">{usuario.nome}</span>
                <button type="button" className="nav-logout" onClick={sair}>
                  Sair
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav-button-outline">
                  Entrar
                </NavLink>
                <NavLink to="/cadastro" className="nav-button-solid">
                  Criar conta
                </NavLink>
              </>
            )}
          </div>
        </div>
      </nav>
    </>
  );
}

export default Header;
