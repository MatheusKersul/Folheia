import { BookOpen } from 'lucide-react';
import { Link } from 'react-router-dom';

function Brand({ to = '/', light = false, onClick, tagline = true }) {
  return (
    <Link
      to={to}
      className={`brand ${light ? 'brand--light' : ''}`}
      onClick={onClick}
      aria-label="Folheia — página inicial"
    >
      <span className="brand__mark" aria-hidden="true">
        <BookOpen />
      </span>
      <span className="brand__text">
        <strong>Folheia</strong>
        {tagline && <small>mais livros, melhores escolhas</small>}
      </span>
    </Link>
  );
}

export default Brand;
