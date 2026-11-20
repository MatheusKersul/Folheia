import { ArrowUp, BookOpen, ExternalLink, LayoutDashboard, Library, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

import Brand from './Brand';

function voltarAoTopo() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__brand">
          <Brand />
          <p>
            Um catálogo colaborativo para descobrir, comparar e guardar as obras
            que marcam a sua estante.
          </p>
        </div>

        <div className="site-footer__column">
          <h4>Navegar</h4>
          <Link to="/">
            <Search size={14} aria-hidden="true" />
            Buscar obras
          </Link>
          <Link to="/biblioteca">
            <Library size={14} aria-hidden="true" />
            Minha biblioteca
          </Link>
          <Link to="/admin">
            <LayoutDashboard size={14} aria-hidden="true" />
            Painel do administrador
          </Link>
        </div>

        <div className="site-footer__column">
          <h4>Sobre o projeto</h4>
          <a
            href="https://github.com/MatheusKersul/Folheia"
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={14} aria-hidden="true" />
            Repositório no GitHub
          </a>
          <span className="sr-only">
            Projeto acadêmico de Sistemas Distribuídos
          </span>
          <p className="footer-note">
            <BookOpen size={14} aria-hidden="true" />
            Projeto acadêmico de Sistemas Distribuídos
          </p>
        </div>
      </div>

      <div className="site-footer__bottom">
        <span>
          © {new Date().getFullYear()} <strong>Folheia</strong>. Feito para quem
          lê.
        </span>
        <button type="button" className="back-to-top" onClick={voltarAoTopo}>
          <ArrowUp aria-hidden="true" />
          Voltar ao topo
        </button>
      </div>
    </footer>
  );
}

export default Footer;
