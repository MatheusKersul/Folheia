import { Fragment, useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Barcode,
  BookOpen,
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FileText,
  LibraryBig,
  Plus,
  Search,
  Trash2,
  UserRound,
  X,
} from 'lucide-react';

import { api } from '../api';
import { useAuth } from '../auth/useAuth';
import BookCover from '../components/BookCover';
import ConfirmDialog from '../components/ConfirmDialog';
import Modal from '../components/Modal';
import { useToast } from '../ui/useToast';

const ITENS_POR_PAGINA = 8;

const FORM_VAZIO = {
  titulo: '',
  autor: '',
  isbn: '',
  data_publicacao: '',
  formato: '',
  num_paginas: '',
  editora: '',
};

function formatarData(valor) {
  return valor ? valor.split('-').reverse().join('/') : 'Não informado';
}

function formatarDataHora(valor) {
  return valor
    ? valor.split('T')[0].split('-').reverse().join('/')
    : 'Não informado';
}

function Biblioteca() {
  const { token, usuario, logout } = useAuth();
  const { notificar } = useToast();
  const navigate = useNavigate();

  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalProprias, setTotalProprias] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [termo, setTermo] = useState('');
  const [termoAplicado, setTermoAplicado] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [recarregar, setRecarregar] = useState(0);

  const [isbn, setIsbn] = useState('');
  const [adicionando, setAdicionando] = useState(false);

  const [modalAberto, setModalAberto] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [formErro, setFormErro] = useState('');
  const [salvando, setSalvando] = useState(false);

  const [itemParaRemover, setItemParaRemover] = useState(null);
  const [removendo, setRemovendo] = useState(false);

  const tratarFalha = useCallback(
    (falha) => {
      if (falha.status === 401) {
        logout();
        navigate('/login', { state: { from: '/biblioteca' } });
        return 'Sua sessão expirou. Entre novamente.';
      }

      return falha.message;
    },
    [logout, navigate],
  );

  useEffect(() => {
    let ativo = true;

    api
      .listarBiblioteca(token, {
        page: pagina,
        limit: ITENS_POR_PAGINA,
        q: termoAplicado,
      })
      .then((dados) => {
        if (!ativo) {
          return;
        }

        setItens(dados.itens || []);
        setTotal(dados.total || 0);
      })
      .catch((falha) => {
        if (ativo) {
          setErro(tratarFalha(falha));
        }
      })
      .finally(() => {
        if (ativo) {
          setCarregando(false);
        }
      });

    return () => {
      ativo = false;
    };
  }, [token, pagina, termoAplicado, recarregar, tratarFalha]);

  useEffect(() => {
    let ativo = true;

    api
      .listarEdicoesProprias(token, { page: 1, limit: 1 })
      .then((dados) => {
        if (ativo) {
          setTotalProprias(dados.total || 0);
        }
      })
      .catch(() => {
        /* o contador é complementar; falhas não bloqueiam a página */
      });

    return () => {
      ativo = false;
    };
  }, [token, recarregar]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const limpo = termo.trim();

      if (limpo !== termoAplicado) {
        setCarregando(true);
        setErro('');
        setPagina(1);
        setTermoAplicado(limpo);
      }
    }, 450);

    return () => window.clearTimeout(timer);
  }, [termo, termoAplicado]);

  const recarregarLista = () => {
    setCarregando(true);
    setErro('');
    setRecarregar((atual) => atual + 1);
  };

  const irParaPagina = (novaPagina) => {
    if (novaPagina === pagina) {
      return;
    }

    setCarregando(true);
    setErro('');
    setPagina(novaPagina);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const enviarBusca = (evento) => {
    evento.preventDefault();

    setCarregando(true);
    setErro('');

    const limpo = termo.trim();

    if (limpo === termoAplicado) {
      if (pagina !== 1) {
        setPagina(1);
      } else {
        recarregarLista();
      }
      return;
    }

    setPagina(1);
    setTermoAplicado(limpo);
  };

  const limparBusca = () => {
    setCarregando(true);
    setErro('');
    setTermo('');
    setTermoAplicado('');
    setPagina(1);
  };

  const adicionarPorIsbn = async (evento) => {
    evento.preventDefault();

    if (!isbn.trim()) {
      notificar('Informe o ISBN-13 da obra.', 'error');
      return;
    }

    setAdicionando(true);

    try {
      await api.adicionarLivro(token, { isbn: isbn.trim() });
      setIsbn('');
      notificar('Obra adicionada à sua biblioteca.', 'success');

      setCarregando(true);
      setErro('');

      if (pagina !== 1) {
        setPagina(1);
      } else {
        recarregarLista();
      }
    } catch (falha) {
      notificar(tratarFalha(falha), 'error');
    } finally {
      setAdicionando(false);
    }
  };

  const alterarCampo = (campo) => (evento) => {
    setForm((atual) => ({ ...atual, [campo]: evento.target.value }));
  };

  const abrirFormulario = () => {
    setFormErro('');
    setModalAberto(true);
  };

  const fecharFormulario = () => {
    if (salvando) {
      return;
    }

    setModalAberto(false);
    setFormErro('');
  };

  const enviarEdicaoPropria = async (evento) => {
    evento.preventDefault();
    setFormErro('');

    if (!form.titulo.trim()) {
      setFormErro('O título é obrigatório.');
      return;
    }

    const payload = {
      titulo: form.titulo.trim(),
      autor: form.autor.trim() || null,
      isbn: form.isbn.trim() || null,
      data_publicacao: form.data_publicacao.trim() || null,
      formato: form.formato.trim() || null,
      num_paginas: form.num_paginas ? Number(form.num_paginas) : null,
      editora: form.editora.trim() || null,
    };

    setSalvando(true);

    try {
      await api.criarEdicaoPropria(token, payload);
      setForm(FORM_VAZIO);
      setModalAberto(false);
      notificar('Edição própria criada e adicionada à biblioteca.', 'success');

      setCarregando(true);
      setErro('');

      if (pagina !== 1) {
        setPagina(1);
      } else {
        recarregarLista();
      }
    } catch (falha) {
      setFormErro(tratarFalha(falha));
    } finally {
      setSalvando(false);
    }
  };

  const confirmarRemocao = async () => {
    if (!itemParaRemover) {
      return;
    }

    setRemovendo(true);

    try {
      await api.removerItem(token, itemParaRemover.id);
      notificar('Obra removida da biblioteca.', 'success');
      setItemParaRemover(null);

      setCarregando(true);
      setErro('');

      if (itens.length === 1 && pagina > 1) {
        setPagina(pagina - 1);
      } else {
        recarregarLista();
      }
    } catch (falha) {
      notificar(tratarFalha(falha), 'error');
    } finally {
      setRemovendo(false);
    }
  };

  const totalPaginas = Math.max(1, Math.ceil(total / ITENS_POR_PAGINA));
  const nomeUsuario = usuario?.nome?.split(' ')[0] || 'leitor';

  const paginasVisiveis = Array.from(
    { length: totalPaginas },
    (_, indice) => indice + 1,
  ).filter(
    (numero) =>
      numero === 1 ||
      numero === totalPaginas ||
      Math.abs(numero - pagina) <= 1,
  );

  return (
    <div className="library">
      <header className="page-heading">
        <div className="page-heading__text">
          <span className="eyebrow eyebrow--dark">Sua estante</span>
          <h1>Minha Biblioteca</h1>
          <p>
            {total > 0
              ? `${total} ${total === 1 ? 'obra organizada' : 'obras organizadas'} por ${nomeUsuario}.`
              : `Organize as obras de ${nomeUsuario} em um só lugar.`}
          </p>
        </div>

        <div className="page-heading__actions">
          <Link to="/" className="btn btn--outline">
            <Search aria-hidden="true" />
            Buscar no catálogo
          </Link>
          <button type="button" className="btn btn--gold" onClick={abrirFormulario}>
            <Plus aria-hidden="true" />
            Nova edição própria
          </button>
        </div>
      </header>

      {erro && (
        <div className="alert alert--error" role="alert">
          {erro}
        </div>
      )}

      <div className="stats">
        <div className="stat-card">
          <span className="stat-card__icon" aria-hidden="true">
            <LibraryBig />
          </span>
          <div>
            <span className="stat-card__value">{total}</span>
            <span className="stat-card__label">
              {total === 1 ? 'Obra na estante' : 'Obras na estante'}
            </span>
          </div>
        </div>

        <div className="stat-card">
          <span className="stat-card__icon" aria-hidden="true">
            <UserRound />
          </span>
          <div>
            <span className="stat-card__value">
              {totalProprias === null ? '—' : totalProprias}
            </span>
            <span className="stat-card__label">Edições próprias</span>
          </div>
        </div>

        <div className="stat-card">
          <span className="stat-card__icon" aria-hidden="true">
            <BookOpen />
          </span>
          <div>
            <span className="stat-card__value">{itens.length}</span>
            <span className="stat-card__label">Nesta página</span>
          </div>
        </div>
      </div>

      <div className="library-toolbar">
        <section className="panel">
          <h2 className="panel__title">
            <Search aria-hidden="true" />
            Filtrar a estante
          </h2>
          <p className="panel__subtitle">
            Busque por título, autor ou editora. A lista é atualizada enquanto
            você digita.
          </p>

          <form onSubmit={enviarBusca} role="search">
            <div className="input-group">
              <Search className="input-group__icon" aria-hidden="true" />
              <input
                type="search"
                placeholder="Buscar por título, autor ou editora..."
                value={termo}
                onChange={(evento) => setTermo(evento.target.value)}
                aria-label="Buscar na biblioteca"
              />

              {termo && (
                <button
                  type="button"
                  className="input-group__clear"
                  onClick={limparBusca}
                  aria-label="Limpar filtro"
                >
                  <X />
                </button>
              )}

              <button type="submit" className="btn btn--primary">
                Buscar
              </button>
            </div>
          </form>
        </section>

        <section className="panel">
          <h2 className="panel__title">
            <Barcode aria-hidden="true" />
            Adicionar do catálogo
          </h2>
          <p className="panel__subtitle">
            Informe o ISBN-13 de uma obra oficial para incluí-la na sua estante.
          </p>

          <form onSubmit={adicionarPorIsbn}>
            <div className="input-group">
              <Barcode className="input-group__icon" aria-hidden="true" />
              <input
                type="text"
                placeholder="9788535902778"
                inputMode="numeric"
                maxLength={17}
                value={isbn}
                onChange={(evento) => setIsbn(evento.target.value)}
                aria-label="ISBN da obra"
              />
              <button
                type="submit"
                className="btn btn--gold"
                disabled={adicionando}
              >
                {adicionando ? (
                  <span className="btn__spinner" aria-hidden="true" />
                ) : (
                  <Plus aria-hidden="true" />
                )}
                {adicionando ? 'Adicionando...' : 'Adicionar'}
              </button>
            </div>
          </form>
        </section>
      </div>

      <div className="library-status">
        <span className="library-status__count">
          {termoAplicado ? (
            <>
              Resultados para <strong>“{termoAplicado}”</strong> — {total}{' '}
              {total === 1 ? 'obra' : 'obras'}
            </>
          ) : (
            <>
              Exibindo <strong>{itens.length}</strong> de{' '}
              <strong>{total}</strong>{' '}
              {total === 1 ? 'obra' : 'obras'}
            </>
          )}
        </span>

        {carregando && itens.length > 0 && (
          <span className="library-status__live">
            <span className="spinner" aria-hidden="true" />
            Atualizando...
          </span>
        )}
      </div>

      {carregando && itens.length === 0 ? (
        <div className="library-grid" aria-hidden="true">
          {Array.from({ length: 4 }).map((_, indice) => (
            <div className="skeleton-card" key={indice}>
              <div className="skeleton skeleton-cover" />
              <div className="skeleton-card__body">
                <div className="skeleton skeleton--title" />
                <div className="skeleton skeleton--text short" />
                <div className="skeleton skeleton--text" />
                <div className="skeleton skeleton--text" />
              </div>
            </div>
          ))}
        </div>
      ) : itens.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state__icon" aria-hidden="true">
            <LibraryBig />
          </span>
          <h3>
            {termoAplicado ? 'Nenhuma obra encontrada' : 'Sua estante está vazia'}
          </h3>
          <p>
            {termoAplicado
              ? 'Tente outro termo de busca ou limpe o filtro para ver todas as obras.'
              : 'Adicione uma obra pelo ISBN, busque no catálogo ou registre sua própria edição.'}
          </p>

          {termoAplicado ? (
            <button type="button" className="btn btn--outline" onClick={limparBusca}>
              <X aria-hidden="true" />
              Limpar filtro
            </button>
          ) : (
            <Link to="/" className="btn btn--primary">
              <Search aria-hidden="true" />
              Buscar obras
            </Link>
          )}
        </div>
      ) : (
        <div className="library-grid">
          {itens.map((item) => {
            const edicao = item.edicao;

            return (
              <article className="library-card" key={item.id}>
                <BookCover
                  className="library-card__cover"
                  size="sm"
                  titulo={edicao.titulo}
                  autor={edicao.autor}
                  imageUrl={edicao.images_url}
                />

                <div className="library-card__body">
                  <div className="library-card__top">
                    <div>
                      <h2 className="library-card__title">{edicao.titulo}</h2>
                      {edicao.autor && (
                        <p className="library-card__author">{edicao.autor}</p>
                      )}
                    </div>

                    <span
                      className={`badge ${edicao.propria ? 'badge--gold' : 'badge--blue'}`}
                    >
                      {edicao.propria ? 'Própria' : 'Catálogo'}
                    </span>
                  </div>

                  <dl className="library-card__meta">
                    <div>
                      <dt>
                        <Barcode aria-hidden="true" />
                        ISBN
                      </dt>
                      <dd>{edicao.isbn || 'Não informado'}</dd>
                    </div>

                    <div>
                      <dt>
                        <Building2 aria-hidden="true" />
                        Editora
                      </dt>
                      <dd>{edicao.editora || 'Não informada'}</dd>
                    </div>

                    <div>
                      <dt>
                        <CalendarDays aria-hidden="true" />
                        Publicação
                      </dt>
                      <dd>{formatarData(edicao.data_publicacao)}</dd>
                    </div>

                    <div>
                      <dt>
                        <BookOpen aria-hidden="true" />
                        Formato
                      </dt>
                      <dd>{edicao.formato || 'Não informado'}</dd>
                    </div>

                    <div>
                      <dt>
                        <FileText aria-hidden="true" />
                        Páginas
                      </dt>
                      <dd>{edicao.num_paginas || 'Não informado'}</dd>
                    </div>

                    <div>
                      <dt>
                        <CalendarDays aria-hidden="true" />
                        Adicionado
                      </dt>
                      <dd>{formatarDataHora(item.criado_em)}</dd>
                    </div>
                  </dl>

                  <div className="library-card__footer">
                    <button
                      type="button"
                      className="library-card__remove"
                      onClick={() => setItemParaRemover(item)}
                    >
                      <Trash2 aria-hidden="true" />
                      Remover
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {!carregando && itens.length > 0 && totalPaginas > 1 && (
        <nav className="pagination" aria-label="Paginação da biblioteca">
          <span className="pagination__info">
            Página <strong>{pagina}</strong> de <strong>{totalPaginas}</strong>
          </span>

          <div className="pagination__pages">
            <button
              type="button"
              className="page-btn"
              onClick={() => irParaPagina(pagina - 1)}
              disabled={pagina <= 1}
              aria-label="Página anterior"
            >
              <ChevronLeft />
            </button>

            {paginasVisiveis.map((numero, indice) => {
              const anterior = paginasVisiveis[indice - 1];
              const temSalto = anterior && numero - anterior > 1;

              return (
                <Fragment key={numero}>
                  {temSalto && <span className="page-ellipsis">…</span>}
                  <button
                    type="button"
                    className={`page-btn ${numero === pagina ? 'is-active' : ''}`}
                    onClick={() => irParaPagina(numero)}
                    aria-current={numero === pagina ? 'page' : undefined}
                  >
                    {numero}
                  </button>
                </Fragment>
              );
            })}

            <button
              type="button"
              className="page-btn"
              onClick={() => irParaPagina(pagina + 1)}
              disabled={pagina >= totalPaginas}
              aria-label="Próxima página"
            >
              <ChevronRight />
            </button>
          </div>
        </nav>
      )}

      <Modal
        open={modalAberto}
        titulo="Nova edição própria"
        subtitulo="Registre uma edição não oficial, visível apenas para você. O ISBN é opcional, mas quando informado deve ter 13 dígitos."
        onClose={fecharFormulario}
      >
        <form onSubmit={enviarEdicaoPropria}>
          <div className="form-grid">
            <div className="field field--full">
              <label htmlFor="edicao-titulo">Título *</label>
              <input
                id="edicao-titulo"
                type="text"
                data-autofocus
                value={form.titulo}
                onChange={alterarCampo('titulo')}
                placeholder="Título da obra"
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-autor">Autor</label>
              <input
                id="edicao-autor"
                type="text"
                value={form.autor}
                onChange={alterarCampo('autor')}
                placeholder="Autor da obra"
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-isbn">ISBN</label>
              <input
                id="edicao-isbn"
                type="text"
                inputMode="numeric"
                maxLength={17}
                value={form.isbn}
                onChange={alterarCampo('isbn')}
                placeholder="Opcional"
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-editora">Editora</label>
              <input
                id="edicao-editora"
                type="text"
                value={form.editora}
                onChange={alterarCampo('editora')}
                placeholder="Editora"
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-data">Data de publicação</label>
              <input
                id="edicao-data"
                type="date"
                value={form.data_publicacao}
                onChange={alterarCampo('data_publicacao')}
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-formato">Formato</label>
              <input
                id="edicao-formato"
                type="text"
                value={form.formato}
                onChange={alterarCampo('formato')}
                placeholder="Ex.: Capa comum"
              />
            </div>

            <div className="field">
              <label htmlFor="edicao-paginas">Páginas</label>
              <input
                id="edicao-paginas"
                type="number"
                min="1"
                value={form.num_paginas}
                onChange={alterarCampo('num_paginas')}
                placeholder="Ex.: 320"
              />
            </div>

            {formErro && (
              <div className="alert alert--error field--full" role="alert">
                {formErro}
              </div>
            )}
          </div>

          <div className="modal__footer">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={fecharFormulario}
              disabled={salvando}
            >
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={salvando}>
              {salvando ? (
                <span className="btn__spinner" aria-hidden="true" />
              ) : (
                <Plus aria-hidden="true" />
              )}
              {salvando ? 'Salvando...' : 'Salvar edição'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(itemParaRemover)}
        titulo="Remover obra"
        mensagem={
          itemParaRemover ? (
            <>
              Remover <strong>“{itemParaRemover.edicao.titulo}”</strong> da sua
              biblioteca? Essa ação não afeta o catálogo oficial.
            </>
          ) : null
        }
        confirmarLabel="Remover obra"
        processando={removendo}
        onConfirmar={confirmarRemocao}
        onCancelar={() => {
          if (!removendo) {
            setItemParaRemover(null);
          }
        }}
      />
    </div>
  );
}

export default Biblioteca;
