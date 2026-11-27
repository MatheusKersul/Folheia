import { useState } from 'react';

const PALETAS = [
  ['#1e3057', '#14213d'],
  ['#14213d', '#0b1425'],
  ['#2c4373', '#1e3057'],
  ['#3a2a12', '#14213d'],
  ['#243b63', '#101b31'],
  ['#5a4218', '#241a0d'],
];

const PALAVRAS_IGNORADAS = new Set([
  'a',
  'o',
  'as',
  'os',
  'de',
  'da',
  'do',
  'das',
  'dos',
  'e',
  'em',
  'um',
  'uma',
  'the',
  'of',
]);

function gerarHash(texto) {
  let hash = 0;

  for (let indice = 0; indice < texto.length; indice += 1) {
    hash = (hash * 31 + texto.charCodeAt(indice)) % 100000;
  }

  return hash;
}

function obterIniciais(titulo) {
  const palavras = (titulo || '')
    .trim()
    .split(/\s+/)
    .filter((palavra) => palavra && !PALAVRAS_IGNORADAS.has(palavra.toLowerCase()));

  if (palavras.length === 0) {
    return 'F';
  }

  return palavras
    .slice(0, 2)
    .map((palavra) => palavra.charAt(0).toUpperCase())
    .join('');
}

function BookCover({
  titulo = '',
  autor = '',
  size = 'md',
  className = '',
  imageUrl = '',
}) {
  const [imagemErro, setImagemErro] = useState(false);
  const temImagem = Boolean(imageUrl) && !imagemErro;

  const [inicio, fim] = PALETAS[gerarHash(titulo) % PALETAS.length];
  const iniciais = obterIniciais(titulo);

  return (
    <div
      className={`book-cover ${size === 'sm' ? 'book-cover--sm' : ''} ${temImagem ? 'book-cover--has-image' : ''} ${className}`.trim()}
      style={{ '--capa-fundo': `linear-gradient(150deg, ${inicio}, ${fim})` }}
      aria-hidden="true"
    >
      {temImagem ? (
        <>
          <img
            src={imageUrl}
            alt={titulo || 'Capa do livro'}
            className="book-cover__img"
            loading="lazy"
            onError={() => setImagemErro(true)}
          />
          <div className="book-cover__fadeout" />
        </>
      ) : (
        <>
          <span className="book-cover__glow" />
          <span className="book-cover__initials">{iniciais}</span>

          <div className="book-cover__bottom">
            <span className="book-cover__line" />
            <p className="book-cover__title">{titulo || 'Obra sem título'}</p>
            {autor && <span className="book-cover__author">{autor}</span>}
          </div>
        </>
      )}
    </div>
  );
}

export default BookCover;
