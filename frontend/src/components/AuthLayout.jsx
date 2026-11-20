import { BadgeCheck, LibraryBig, Sparkles } from 'lucide-react';

import HeaderDecoration from '../HeaderDecoration';
import Brand from './Brand';

const DESTAQUES = [
  {
    icone: BadgeCheck,
    titulo: 'Catálogo verificado',
    texto: 'Obras oficiais e edições próprias organizadas num só lugar.',
  },
  {
    icone: LibraryBig,
    titulo: 'Sua estante, suas regras',
    texto: 'Busque por título, autor ou ISBN e monte sua coleção pessoal.',
  },
  {
    icone: Sparkles,
    titulo: 'Descobertas rápidas',
    texto: 'Compare ofertas e encontre o próximo capítulo sem perder tempo.',
  },
];

function AuthLayout({ eyebrow, title, subtitle, children, footer, legal }) {
  return (
    <div className="auth-grid">
      <aside className="auth-aside">
        <HeaderDecoration className="auth-aside__decoration" />

        <div className="auth-aside__content">
          <Brand />

          <h2>
            Toda grande leitura começa com uma <em>boa descoberta</em>.
          </h2>
          <p className="auth-aside__lead">
            O Folheia reúne catálogo, ofertas e a sua biblioteca pessoal em uma
            experiência simples de usar — da primeira busca ao último capítulo.
          </p>

          <ul className="auth-features">
            {DESTAQUES.map(({ icone: Icone, titulo, texto }) => (
              <li className="auth-feature" key={titulo}>
                <span className="auth-feature__icon" aria-hidden="true">
                  <Icone />
                </span>
                <div>
                  <strong>{titulo}</strong>
                  <span>{texto}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <blockquote className="auth-quote">
          “Um leitor vive mil vidas antes de morrer.”
          <span>George R. R. Martin</span>
        </blockquote>
      </aside>

      <section className="auth-panel">
        <div className="auth-card">
          <span className="auth-card__eyebrow">{eyebrow}</span>
          <h1 className="auth-card__title">{title}</h1>
          <p className="auth-card__subtitle">{subtitle}</p>

          {children}

          {footer && <div className="auth-footer">{footer}</div>}
          {legal && <p className="auth-legal">{legal}</p>}
        </div>
      </section>
    </div>
  );
}

export default AuthLayout;
