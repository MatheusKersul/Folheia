import { BookX, Library, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

function NotFound() {
  return (
    <div className="not-found">
      <span className="not-found__code" aria-hidden="true">
        404
      </span>

      <h1>Esta página saiu da estante.</h1>
      <p>
        O endereço que você tentou acessar não existe ou foi movido. Que tal
        voltar ao catálogo e escolher uma nova leitura?
      </p>

      <div className="not-found__actions">
        <Link to="/" className="btn btn--primary">
          <Search aria-hidden="true" />
          Voltar à busca
        </Link>
        <Link to="/biblioteca" className="btn btn--outline">
          <Library aria-hidden="true" />
          Minha biblioteca
        </Link>
      </div>

      <BookX
        aria-hidden="true"
        style={{ marginTop: 38, width: 42, height: 42, color: '#fca311' }}
      />
    </div>
  );
}

export default NotFound;
