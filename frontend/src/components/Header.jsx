import { useEffect, useRef, useState } from 'react';
import {
  ChevronDown,
  LayoutDashboard,
  Library,
  LogIn,
  LogOut,
  Menu,
  Search,
  UserPlus,
  X,
} from 'lucide-react';
import { NavLink, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/useAuth';
import { useToast } from '../ui/useToast';
import Brand from './Brand';

function classeNavLink({ isActive }) {
  return isActive ? 'nav-link active' : 'nav-link';
}

function iniciaisDe(nome) {
  const partes = (nome || 'Leitor').trim().split(/\s+/);

  if (partes.length === 1) {
    return partes[0].slice(0, 2).toUpperCase();
  }

  return `${partes[0][0]}${partes[partes.length - 1][0]}`.toUpperCase();
}

function Header() {
  const { usuario, logout } = useAuth();
  const { notificar } = useToast();
  const navigate = useNavigate();

  const [menuMobile, setMenuMobile] = useState(false);
  const [menuUsuario, setMenuUsuario] = useState(false);
  const menuUsuarioRef = useRef(null);

  const fecharMenus = () => {
    setMenuMobile(false);
    setMenuUsuario(false);
  };

  useEffect(() => {
    const fecharComEsc = (evento) => {
      if (evento.key === 'Escape') {
        setMenuMobile(false);
        setMenuUsuario(false);
      }
    };

    document.addEventListener('keydown', fecharComEsc);
    return () => document.removeEventListener('keydown', fecharComEsc);
  }, []);

  useEffect(() => {
    if (!menuUsuario) {
      return undefined;
    }

    const fecharAoCliqueFora = (evento) => {
      if (
        menuUsuarioRef.current &&
        !menuUsuarioRef.current.contains(evento.target)
      ) {
        setMenuUsuario(false);
      }
    };

    const fecharComEsc = (evento) => {
      if (evento.key === 'Escape') {
        setMenuUsuario(false);
      }
    };

    document.addEventListener('mousedown', fecharAoCliqueFora);
    document.addEventListener('keydown', fecharComEsc);

    return () => {
      document.removeEventListener('mousedown', fecharAoCliqueFora);
      document.removeEventListener('keydown', fecharComEsc);
    };
  }, [menuUsuario]);

  const sair = () => {
    logout();
    setMenuUsuario(false);
    setMenuMobile(false);
    notificar('Sessão encerrada. Até a próxima leitura!', 'info');
    navigate('/');
  };

  const linkBiblioteca = (
    <NavLink to="/biblioteca" className={classeNavLink} onClick={fecharMenus}>
      <Library />
      Minha biblioteca
    </NavLink>
  );

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Brand onClick={fecharMenus} />

        <nav className="site-nav" aria-label="Navegação principal">
          <NavLink to="/" end className={classeNavLink} onClick={fecharMenus}>
            <Search />
            Buscar
          </NavLink>
          {linkBiblioteca}
        </nav>

        <div className="site-actions">
          <NavLink
            to="/admin"
            className="icon-button"
            title="Painel do administrador"
            aria-label="Painel do administrador"
            onClick={fecharMenus}
          >
            <LayoutDashboard />
          </NavLink>

          {usuario ? (
            <div className="user-menu" ref={menuUsuarioRef}>
              <button
                type="button"
                className="user-menu__trigger"
                onClick={() => setMenuUsuario((aberto) => !aberto)}
                aria-expanded={menuUsuario}
                aria-haspopup="true"
              >
                <span className="avatar" aria-hidden="true">
                  {iniciaisDe(usuario.nome)}
                </span>
                <span className="user-menu__name">{usuario.nome}</span>
                <ChevronDown className="user-menu__chevron" aria-hidden="true" />
              </button>

              {menuUsuario && (
                <div className="user-menu__panel" role="menu">
                  <div className="user-menu__identity">
                    <strong>{usuario.nome}</strong>
                    <span>{usuario.email}</span>
                  </div>

                  <NavLink
                    to="/biblioteca"
                    className="user-menu__item"
                    role="menuitem"
                    onClick={fecharMenus}
                  >
                    <Library />
                    Minha biblioteca
                  </NavLink>

                  <NavLink
                    to="/admin"
                    className="user-menu__item"
                    role="menuitem"
                    onClick={fecharMenus}
                  >
                    <LayoutDashboard />
                    Painel do administrador
                  </NavLink>

                  <button
                    type="button"
                    className="user-menu__item user-menu__item--danger"
                    onClick={sair}
                    role="menuitem"
                  >
                    <LogOut />
                    Sair da conta
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <NavLink to="/login" className="header-cta header-cta--ghost">
                Entrar
              </NavLink>
              <NavLink to="/cadastro" className="header-cta header-cta--solid">
                <UserPlus size={16} aria-hidden="true" />
                Criar conta
              </NavLink>
            </>
          )}

          <button
            type="button"
            className="menu-toggle"
            onClick={() => setMenuMobile((aberto) => !aberto)}
            aria-expanded={menuMobile}
            aria-controls="menu-mobile"
            aria-label={menuMobile ? 'Fechar menu' : 'Abrir menu'}
          >
            {menuMobile ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      <div
        id="menu-mobile"
        className={`mobile-nav ${menuMobile ? 'is-open' : ''}`}
      >
        <div className="mobile-nav__inner">
          <NavLink
            to="/"
            end
            className={classeNavLink}
            onClick={fecharMenus}
          >
            <Search />
            Buscar obras
          </NavLink>

          <NavLink
            to="/biblioteca"
            className={classeNavLink}
            onClick={fecharMenus}
          >
            <Library />
            Minha biblioteca
          </NavLink>

          <NavLink
            to="/admin"
            className={classeNavLink}
            onClick={fecharMenus}
          >
            <LayoutDashboard />
            Painel do administrador
          </NavLink>

          <div className="mobile-nav__divider" />

          {usuario ? (
            <>
              <div className="mobile-user">
                <span className="avatar" aria-hidden="true">
                  {iniciaisDe(usuario.nome)}
                </span>
                <div>
                  <strong>{usuario.nome}</strong>
                  <span>{usuario.email}</span>
                </div>
              </div>
              <button type="button" className="nav-link" onClick={sair}>
                <LogOut />
                Sair da conta
              </button>
            </>
          ) : (
            <div className="mobile-nav__actions">
              <NavLink
                to="/login"
                className="header-cta header-cta--ghost"
                onClick={fecharMenus}
              >
                <LogIn size={16} aria-hidden="true" />
                Entrar
              </NavLink>
              <NavLink
                to="/cadastro"
                className="header-cta header-cta--solid"
                onClick={fecharMenus}
              >
                <UserPlus size={16} aria-hidden="true" />
                Criar conta
              </NavLink>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;
