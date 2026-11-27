import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BadgeCheck,
  Barcode,
  BookOpen,
  BookPlus,
  Building2,
  CalendarDays,
  Check,
  ExternalLink,
  FileText,
  LibraryBig,
  Search,
  ShieldCheck,
  Sparkles,
  Tag,
  User,
  Zap,
} from 'lucide-react';

import { api } from '../api';
import { useAuth } from '../auth/useAuth';
import BookCover from '../components/BookCover';
import HeaderDecoration from '../HeaderDecoration';
import { useToast } from '../ui/useToast';

const TIPOS_BUSCA = [
  {
    valor: 'titulo',
    rotulo: 'Título',
    icone: BookOpen,
    placeholder: 'Ex.: Dom Casmurro',
  },
  {
    valor: 'autor',
    rotulo: 'Autor',
    icone: User,
    placeholder: 'Ex.: Machado de Assis',
  },
  {
    valor: 'isbn',
    rotulo: 'ISBN',
    icone: Barcode,
    placeholder: 'Ex.: 9788535902778',
  },
];

const CHAVE_RECENTES = 'folheia.buscas-recentes';

const FORMATADOR_MOEDA = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
});

function formatarData(valor) {
  return valor ? valor.split('-').reverse().join('/') : 'Não informado';
}

function formatarPreco(valor) {
  return Number.isFinite(Number(valor))
    ? FORMATADOR_MOEDA.format(Number(valor))
    : 'Consulte';
}

function linkSeguro(link) {
  return typeof link === 'string' && /^https?:\/\//i.test(link);
}

function lerRecentes() {
  try {
    const dados = JSON.parse(localStorage.getItem(CHAVE_RECENTES) || '[]');
    return Array.isArray(dados) ? dados.slice(0, 5) : [];
  } catch {
    return [];
  }
}

function Home() {
  const { autenticado, token, logout } = useAuth();
  const { notificar } = useToast();
  const navigate = useNavigate();

  const entradaRef = useRef(null);
  const resultadosRef = useRef(null);

  const [dadosLivro, setDadosLivro] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [termoBusca, setTermoBusca] = useState('');
  const [tipoBusca, setTipoBusca] = useState('titulo');
  const [erro, setErro] = useState('');
  const [adicionando, setAdicionando] = useState(false);
  const [adicionado, setAdicionado] = useState(false);
  const [mensagemBiblioteca, setMensagemBiblioteca] = useState(null);
  const [recentes, setRecentes] = useState(lerRecentes);
  const [ofertas, setOfertas] = useState(null);
  const [carregandoOfertas, setCarregandoOfertas] = useState(false);
  const [erroOfertas, setErroOfertas] = useState('');

  const tipoAtual =
    TIPOS_BUSCA.find((tipo) => tipo.valor === tipoBusca) || TIPOS_BUSCA[0];

  useEffect(() => {
    const atalho = (evento) => {
      const alvo = document.activeElement;
      const digitando =
        alvo &&
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(alvo.tagName);

      if (evento.key === '/' && !digitando) {
        evento.preventDefault();
        entradaRef.current?.focus();
      }
    };

    window.addEventListener('keydown', atalho);
    return () => window.removeEventListener('keydown', atalho);
  }, []);

  const guardarRecente = (item) => {
    setRecentes((atuais) => {
      const semDuplicado = atuais.filter(
        (atual) =>
          !(
            atual.tipo === item.tipo &&
            atual.termo.toLowerCase() === item.termo.toLowerCase()
          ),
      );

      const atualizados = [item, ...semDuplicado].slice(0, 5);

      try {
        localStorage.setItem(CHAVE_RECENTES, JSON.stringify(atualizados));
      } catch {
        /* armazenamento indisponível: segue sem persistir */
      }

      return atualizados;
    });
  };

  const limparRecentes = () => {
    setRecentes([]);
    localStorage.removeItem(CHAVE_RECENTES);
  };

  const pesquisar = async (tipo, termoBruto) => {
    const termo = (termoBruto || '').trim();

    if (!termo) {
      setErro('Digite um termo para pesquisar.');
      entradaRef.current?.focus();
      return;
    }

    setTipoBusca(tipo);
    setTermoBusca(termo);
    setErro('');
    setDadosLivro(null);
    setMensagemBiblioteca(null);
    setAdicionado(false);
    setOfertas(null);
    setErroOfertas('');
    setCarregando(true);

    try {
      const resultado = await api.buscarLivros({ tipo, termo });
      setDadosLivro(resultado);
      guardarRecente({ tipo, termo, titulo: resultado.titulo });

      if (window.matchMedia('(max-width: 920px)').matches) {
        window.setTimeout(() => {
          resultadosRef.current?.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
          });
        }, 80);
      }
    } catch (falha) {
      if (falha.status === 401) {
        logout();
      }
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  const enviarBusca = (evento) => {
    evento.preventDefault();
    pesquisar(tipoBusca, termoBusca);
  };

  const adicionarNaBiblioteca = async () => {
    if (!autenticado) {
      notificar('Entre na sua conta para montar sua biblioteca.', 'info');
      navigate('/login', { state: { from: '/' } });
      return;
    }

    setAdicionando(true);
    setMensagemBiblioteca(null);

    try {
      await api.adicionarLivro(token, { isbn: dadosLivro.isbn });
      setAdicionado(true);
      setMensagemBiblioteca({
        tipo: 'success',
        texto: 'Obra adicionada à sua biblioteca.',
      });
      notificar('Obra adicionada à sua biblioteca.', 'success');
    } catch (falha) {
      if (falha.status === 401) {
        logout();
        navigate('/login', { state: { from: '/' } });
        return;
      }

      const tipo = falha.status === 409 ? 'info' : 'error';
      setMensagemBiblioteca({ tipo, texto: falha.message });
      notificar(falha.message, tipo);
    } finally {
      setAdicionando(false);
    }
  };

  const compararOfertas = async () => {
    setCarregandoOfertas(true);
    setErroOfertas('');
    setOfertas(null);

    try {
      const resposta = await api.buscarPrecos(
        dadosLivro.titulo,
        dadosLivro.isbn,
      );

      const lista = [...(resposta?.ofertas || [])].sort(
        (a, b) => Number(a.preco) - Number(b.preco),
      );

      setOfertas(lista);
    } catch (falha) {
      setErroOfertas(falha.message);
    } finally {
      setCarregandoOfertas(false);
    }
  };

  const metadados = dadosLivro
    ? [
        {
          icone: Barcode,
          rotulo: 'ISBN',
          valor: dadosLivro.isbn || 'Não informado',
        },
        {
          icone: CalendarDays,
          rotulo: 'Publicação',
          valor: formatarData(dadosLivro.data_publicacao),
        },
        {
          icone: BookOpen,
          rotulo: 'Formato',
          valor: dadosLivro.formato || 'Não informado',
        },
        {
          icone: FileText,
          rotulo: 'Páginas',
          valor: dadosLivro.num_paginas || 'Não informado',
        },
        {
          icone: Building2,
          rotulo: 'Editora',
          valor: dadosLivro.editora || 'Não informada',
        },
        {
          icone: User,
          rotulo: 'Autor',
          valor: dadosLivro.autor || 'Não informado',
        },
      ]
    : [];

  const menorPreco =
    ofertas && ofertas.length > 0
      ? Math.min(...ofertas.map((oferta) => Number(oferta.preco)))
      : null;

  return (
    <div className="home">
      <section className="hero">
        <HeaderDecoration className="hero__decoration" />

        <div className="hero__content">
          <span className="eyebrow">
            <Sparkles aria-hidden="true" />
            Catálogo de obras e ofertas
          </span>

          <h1>
            Encontre o próximo <span className="hero__highlight">capítulo</span>{' '}
            da sua estante.
          </h1>

          <p className="hero__lead">
            Busque por título, autor ou ISBN, descubra os detalhes da edição e
            compare ofertas em poucos segundos.
          </p>

          <form
            className={`hero__search ${carregando ? 'is-loading' : ''}`}
            onSubmit={enviarBusca}
            aria-busy={carregando}
          >
            <div className="search-tabs" role="tablist" aria-label="Tipo de busca">
              {TIPOS_BUSCA.map(({ valor, rotulo, icone: Icone }) => (
                <button
                  key={valor}
                  type="button"
                  role="tab"
                  aria-selected={tipoBusca === valor}
                  className={`search-tab ${tipoBusca === valor ? 'is-active' : ''}`}
                  onClick={() => {
                    setTipoBusca(valor);
                    setErro('');
                    entradaRef.current?.focus();
                  }}
                >
                  <Icone aria-hidden="true" />
                  {rotulo}
                </button>
              ))}
            </div>

            <div className="search-box">
              <Search className="search-box__icon" aria-hidden="true" />
              <input
                ref={entradaRef}
                type={tipoBusca === 'isbn' ? 'search' : 'text'}
                className="search-box__input"
                placeholder={tipoAtual.placeholder}
                aria-label={`Buscar por ${tipoAtual.rotulo}`}
                inputMode={tipoBusca === 'isbn' ? 'numeric' : 'text'}
                value={termoBusca}
                onChange={(evento) => {
                  setTermoBusca(evento.target.value);
                  setErro('');
                }}
              />
              <button type="submit" className="search-box__submit">
                Buscar
                <ArrowRight aria-hidden="true" />
              </button>
            </div>

            <div className="hero__meta">
              <span>
                <BadgeCheck aria-hidden="true" />
                Catálogo verificado
              </span>
              <span>
                <Zap aria-hidden="true" />
                Resposta com cache inteligente
              </span>
              <span>
                <ShieldCheck aria-hidden="true" />
                Biblioteca privada
              </span>
            </div>

            {recentes.length > 0 && (
              <div className="hero__recent">
                <span className="hero__recent-label">Buscas recentes:</span>

                {recentes.map((item) => (
                  <button
                    key={`${item.tipo}-${item.termo}`}
                    type="button"
                    className="recent-chip"
                    onClick={() => pesquisar(item.tipo, item.termo)}
                  >
                    <Search aria-hidden="true" />
                    {item.titulo || item.termo}
                  </button>
                ))}

                <button
                  type="button"
                  className="recent-clear"
                  onClick={limparRecentes}
                >
                  limpar
                </button>
              </div>
            )}
          </form>
        </div>
      </section>

      <div className="results" ref={resultadosRef}>
        {erro && (
          <div className="alert alert--error" role="alert">
            {erro}
          </div>
        )}

        {carregando && (
          <>
            <div className="skeleton-result" aria-hidden="true">
              <div className="skeleton skeleton-cover" />
              <div>
                <div className="skeleton skeleton--title" />
                <div className="skeleton skeleton--text short" />
                <div className="skeleton-meta">
                  {Array.from({ length: 6 }).map((_, indice) => (
                    <div className="skeleton skeleton-block" key={indice} />
                  ))}
                </div>
              </div>
            </div>
            <p className="sr-only" role="status">
              Buscando dados da obra...
            </p>
          </>
        )}

        {!carregando && dadosLivro && (
          <>
            <article className="result-card">
              <BookCover
                className="result-card__cover"
                titulo={dadosLivro.titulo}
                autor={dadosLivro.autor}
                imageUrl={dadosLivro.images_url}
              />

              <div className="result-card__body">
                <span className="result-card__eyebrow">Resultado da busca</span>
                <h2 className="result-card__title">{dadosLivro.titulo}</h2>
                {dadosLivro.autor && (
                  <p className="result-card__author">por {dadosLivro.autor}</p>
                )}

                <div className="result-card__divider" />

                <dl className="meta-grid">
                  {metadados.map(({ icone: Icone, rotulo, valor }) => (
                    <div className="meta-item" key={rotulo}>
                      <span className="meta-item__icon" aria-hidden="true">
                        <Icone />
                      </span>
                      <div>
                        <dt className="meta-item__label">{rotulo}</dt>
                        <dd className="meta-item__value">{valor}</dd>
                      </div>
                    </div>
                  ))}
                </dl>

                {mensagemBiblioteca && (
                  <div
                    className={`alert alert--${mensagemBiblioteca.tipo} result-card__alert`}
                    role="status"
                  >
                    {mensagemBiblioteca.texto}
                  </div>
                )}

                <div className="result-card__actions">
                  <button
                    type="button"
                    className="btn btn--primary"
                    onClick={adicionarNaBiblioteca}
                    disabled={adicionando || adicionado}
                  >
                    {adicionando ? (
                      <span className="btn__spinner" aria-hidden="true" />
                    ) : adicionado ? (
                      <Check aria-hidden="true" />
                    ) : (
                      <BookPlus aria-hidden="true" />
                    )}
                    {adicionando
                      ? 'Adicionando...'
                      : adicionado
                        ? 'Já está na sua biblioteca'
                        : 'Adicionar à minha biblioteca'}
                  </button>

                  <button
                    type="button"
                    className="btn btn--outline"
                    onClick={compararOfertas}
                    disabled={carregandoOfertas}
                  >
                    {carregandoOfertas ? (
                      <span className="btn__spinner" aria-hidden="true" />
                    ) : (
                      <Tag aria-hidden="true" />
                    )}
                    {carregandoOfertas ? 'Consultando lojas...' : 'Comparar ofertas'}
                  </button>
                </div>
              </div>
            </article>

            {(carregandoOfertas || erroOfertas || ofertas) && (
              <section className="offers" aria-live="polite">
                <div className="offers__header">
                  <div>
                    <h3>Ofertas encontradas</h3>
                    <p>
                      Preços informados por lojas parceiras para “{dadosLivro.titulo}”.
                    </p>
                  </div>
                  {ofertas && ofertas.length > 0 && (
                    <span className="badge badge--gold">
                      <Tag aria-hidden="true" />
                      {ofertas.length}{' '}
                      {ofertas.length === 1 ? 'oferta' : 'ofertas'}
                    </span>
                  )}
                </div>

                {carregandoOfertas && (
                  <div className="offer-list" aria-hidden="true">
                    {Array.from({ length: 3 }).map((_, indice) => (
                      <div
                        className="skeleton skeleton--offer"
                        key={indice}
                      />
                    ))}
                  </div>
                )}

                {!carregandoOfertas && erroOfertas && (
                  <div className="alert alert--error" role="alert">
                    {erroOfertas}
                  </div>
                )}

                {!carregandoOfertas && ofertas && ofertas.length === 0 && (
                  <div className="alert alert--info">
                    Nenhuma oferta disponível no momento. Tente novamente mais
                    tarde.
                  </div>
                )}

                {!carregandoOfertas && ofertas && ofertas.length > 0 && (
                  <div className="offer-list">
                    {ofertas.map((oferta) => {
                      const melhor =
                        Number(oferta.preco) === Number(menorPreco);

                      return (
                        <div
                          className={`offer ${melhor ? 'offer--best' : ''}`}
                          key={`${oferta.loja}-${oferta.preco}`}
                        >
                          <div className="offer__store">
                            <span className="offer__logo" aria-hidden="true">
                              {(oferta.loja || '?').charAt(0).toUpperCase()}
                            </span>
                            <div>
                              <strong>{oferta.loja}</strong>
                              <span>
                                {melhor ? 'Melhor preço encontrado' : 'Loja parceira'}
                              </span>
                            </div>
                          </div>

                          {melhor && (
                            <span className="badge badge--gold">Menor preço</span>
                          )}

                          <span className="offer__price">
                            {formatarPreco(oferta.preco)}
                          </span>

                          {linkSeguro(oferta.link) ? (
                            <a
                              className="offer__link"
                              href={oferta.link}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Ver oferta
                              <ExternalLink aria-hidden="true" />
                            </a>
                          ) : (
                            <span
                              className="offer__link offer__link--disabled"
                              title="Link indisponível para esta oferta"
                            >
                              Indisponível
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            )}
          </>
        )}

        {!carregando && !dadosLivro && !erro && (
          <>
            <div className="empty-hint">
              <span className="empty-hint__icon" aria-hidden="true">
                <Search />
              </span>
              <div>
                <h3>Pronto para começar?</h3>
                <p>
                  Digite um título, autor ou ISBN acima e pressione{' '}
                  <strong>Buscar</strong>. Dica: use a tecla{' '}
                  <kbd>/</kbd> para focar a barra de pesquisa.
                </p>
              </div>
            </div>

            <div className="features">
              <article className="feature-card">
                <span className="feature-card__step" aria-hidden="true">
                  01
                </span>
                <span className="feature-card__icon" aria-hidden="true">
                  <Search />
                </span>
                <div>
                  <h3>Encontre a edição certa</h3>
                  <p>
                    Consultas por título, autor ou ISBN com respostas rápidas do
                    catálogo.
                  </p>
                </div>
              </article>

              <article className="feature-card">
                <span className="feature-card__step" aria-hidden="true">
                  02
                </span>
                <span className="feature-card__icon" aria-hidden="true">
                  <Tag />
                </span>
                <div>
                  <h3>Compare ofertas</h3>
                  <p>
                    Veja preços em diferentes lojas e escolha a melhor opção para
                    você.
                  </p>
                </div>
              </article>

              <article className="feature-card">
                <span className="feature-card__step" aria-hidden="true">
                  03
                </span>
                <span className="feature-card__icon" aria-hidden="true">
                  <LibraryBig />
                </span>
                <div>
                  <h3>Monte sua estante</h3>
                  <p>
                    Adicione obras ao catálogo ou registre edições próprias na
                    sua biblioteca.
                  </p>
                </div>
              </article>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Home;
