import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Barcode,
  BookOpen,
  Building2,
  CalendarDays,
  FileText,
  LibraryBig,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';

import { api } from '../api';
import { useAuth } from '../auth/useAuth';

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
  const navigate = useNavigate();

  const [itens, setItens] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [termo, setTermo] = useState('');
  const [termoAplicado, setTermoAplicado] = useState('');
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState(null);

  const [isbn, setIsbn] = useState('');
  const [adicionando, setAdicionando] = useState(false);

  const [formAberto, setFormAberto] = useState(false);
  const [form, setForm] = useState(FORM_VAZIO);
  const [formErro, setFormErro] = useState('');
  const [salvando, setSalvando] = useState(false);

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

  const iniciarCarregamento = () => {
    setCarregando(true);
    setErro('');
  };

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro('');

    try {
      const dados = await api.listarBiblioteca(token, {
        page,
        limit: ITENS_POR_PAGINA,
        q: termoAplicado,
      });

      setItens(dados.itens);
      setTotal(dados.total);
    } catch (falha) {
      setErro(tratarFalha(falha));
    } finally {
      setCarregando(false);
    }
  }, [token, page, termoAplicado, tratarFalha]);

  useEffect(() => {
    let ativo = true;

    api
      .listarBiblioteca(token, {
        page,
        limit: ITENS_POR_PAGINA,
        q: termoAplicado,
      })
      .then((dados) => {
        if (!ativo) {
          return;
        }

        setItens(dados.itens);
        setTotal(dados.total);
        setErro('');
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
  }, [token, page, termoAplicado, tratarFalha]);

  const buscar = (evento) => {
    evento.preventDefault();

    const novoTermo = termo.trim();

    if (novoTermo === termoAplicado && page === 1) {
      iniciarCarregamento();
      carregar();
      return;
    }

    if (novoTermo !== termoAplicado) {
      setTermoAplicado(novoTermo);
    }

    if (page !== 1) {
      setPage(1);
    }

    iniciarCarregamento();
  };

  const irParaPagina = (novaPagina) => {
    iniciarCarregamento();
    setPage(novaPagina);
  };

  const adicionarPorIsbn = async (evento) => {
    evento.preventDefault();
    setAviso(null);

    if (!isbn.trim()) {
      setAviso({ tipo: 'erro', texto: 'Informe o ISBN-13 da obra.' });
      return;
    }

    setAdicionando(true);

    try {
      await api.adicionarLivro(token, { isbn: isbn.trim() });
      setIsbn('');
      setAviso({
        tipo: 'sucesso',
        texto: 'Obra adicionada à sua biblioteca.',
      });

      if (page === 1) {
        await carregar();
      } else {
        iniciarCarregamento();
        setPage(1);
      }
    } catch (falha) {
      setAviso({ tipo: 'erro', texto: tratarFalha(falha) });
    } finally {
      setAdicionando(false);
    }
  };

  const alterarCampo = (campo) => (evento) => {
    setForm((atual) => ({ ...atual, [campo]: evento.target.value }));
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
      setFormAberto(false);
      setAviso({
        tipo: 'sucesso',
        texto: 'Edição própria criada e adicionada à biblioteca.',
      });

      if (page === 1) {
        await carregar();
      } else {
        iniciarCarregamento();
        setPage(1);
      }
    } catch (falha) {
      setFormErro(tratarFalha(falha));
    } finally {
      setSalvando(false);
    }
  };

  const remover = async (item) => {
    const confirmou = window.confirm(
      `Remover "${item.edicao.titulo}" da sua biblioteca?`,
    );

    if (!confirmou) {
      return;
    }

    setAviso(null);

    try {
      await api.removerItem(token, item.id);
      setAviso({ tipo: 'sucesso', texto: 'Obra removida da biblioteca.' });

      if (itens.length === 1 && page > 1) {
        iniciarCarregamento();
        setPage(page - 1);
      } else {
        await carregar();
      }
    } catch (falha) {
      setAviso({ tipo: 'erro', texto: tratarFalha(falha) });
    }
  };

  const totalPaginas = Math.max(1, Math.ceil(total / ITENS_POR_PAGINA));
  const nomeUsuario = usuario?.nome?.split(' ')[0] || 'leitor';

  return (
    <>
      <div className="page-heading">
        <h2>Minha Biblioteca</h2>
        <p>
          {total > 0
            ? `${total} ${total === 1 ? 'obra' : 'obras'} na estante de ${nomeUsuario}.`
            : `Organize as obras de ${nomeUsuario} em um só lugar.`}
        </p>
      </div>

      {erro && <div className="alert alert-error">{erro}</div>}
      {aviso && <div className={`alert alert-${aviso.tipo}`}>{aviso.texto}</div>}

      <section className="panel">
        <form className="search-row" onSubmit={buscar}>
          <input
            type="search"
            className="field-input"
            placeholder="Buscar por título, autor ou editora..."
            value={termo}
            onChange={(evento) => setTermo(evento.target.value)}
            aria-label="Buscar na biblioteca"
          />
          <button type="submit" className="btn btn-primary">
            <Search />
            Buscar
          </button>
        </form>
      </section>

      <div className="library-toolbar">
        <section className="panel">
          <h3>Adicionar do catálogo</h3>
          <p className="panel-subtitle">
            Informe o ISBN-13 de uma obra oficial para incluí-la na sua
            estante.
          </p>
          <form className="search-row" onSubmit={adicionarPorIsbn}>
            <input
              type="text"
              className="field-input"
              placeholder="9788535902778"
              inputMode="numeric"
              maxLength={17}
              value={isbn}
              onChange={(evento) => setIsbn(evento.target.value)}
              aria-label="ISBN da obra"
            />
            <button
              type="submit"
              className="btn btn-gold"
              disabled={adicionando}
            >
              <Plus />
              {adicionando ? 'Adicionando...' : 'Adicionar'}
            </button>
          </form>
        </section>

        <section className="panel">
          <h3>Edição própria</h3>
          <p className="panel-subtitle">
            Registre uma edição não oficial, visível apenas para você.
          </p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setFormErro('');
              setFormAberto((valor) => !valor);
            }}
          >
            {formAberto ? <X /> : <Plus />}
            {formAberto ? 'Fechar formulário' : 'Nova edição própria'}
          </button>
        </section>
      </div>

      {formAberto && (
        <section className="panel own-edition-panel">
          <h3>Nova edição própria</h3>
          <p className="panel-subtitle">
            Edições próprias não passam pela verificação do catálogo. O ISBN é
            opcional, mas quando informado deve ter 13 dígitos.
          </p>

          <form className="form-grid" onSubmit={enviarEdicaoPropria}>
            <div className="field field-full">
              <label htmlFor="edicao-titulo">Título *</label>
              <input
                id="edicao-titulo"
                type="text"
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
              <div className="alert alert-error field-full">{formErro}</div>
            )}

            <div className="form-actions field-full">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={salvando}
              >
                <Plus />
                {salvando ? 'Salvando...' : 'Salvar edição'}
              </button>
            </div>
          </form>
        </section>
      )}

      {carregando ? (
        <div className="alert alert-info">Carregando sua biblioteca...</div>
      ) : itens.length === 0 ? (
        <div className="empty-state">
          <LibraryBig />
          <h3>
            {termoAplicado
              ? 'Nenhuma obra encontrada'
              : 'Sua estante está vazia'}
          </h3>
          <p>
            {termoAplicado
              ? 'Tente outro termo de busca ou limpe o filtro.'
              : 'Adicione uma obra pelo ISBN ou registre sua própria edição.'}
          </p>
        </div>
      ) : (
        <div className="library-grid">
          {itens.map((item) => {
            const edicao = item.edicao;

            return (
              <article className="book-item" key={item.id}>
                <div className="book-item-header">
                  <div>
                    <h3>{edicao.titulo}</h3>
                    {edicao.autor && (
                      <p className="book-item-author">{edicao.autor}</p>
                    )}
                  </div>

                  <span
                    className={`badge ${edicao.propria ? 'badge-propria' : 'badge-oficial'}`}
                  >
                    {edicao.propria ? 'Edição própria' : 'Catálogo'}
                  </span>
                </div>

                <dl className="book-item-meta">
                  <div>
                    <dt>
                      <Barcode />
                      ISBN
                    </dt>
                    <dd>{edicao.isbn || 'Não informado'}</dd>
                  </div>

                  <div>
                    <dt>
                      <Building2 />
                      Editora
                    </dt>
                    <dd>{edicao.editora || 'Não informada'}</dd>
                  </div>

                  <div>
                    <dt>
                      <CalendarDays />
                      Publicação
                    </dt>
                    <dd>{formatarData(edicao.data_publicacao)}</dd>
                  </div>

                  <div>
                    <dt>
                      <BookOpen />
                      Formato
                    </dt>
                    <dd>{edicao.formato || 'Não informado'}</dd>
                  </div>

                  <div>
                    <dt>
                      <FileText />
                      Páginas
                    </dt>
                    <dd>{edicao.num_paginas || 'Não informado'}</dd>
                  </div>

                  <div>
                    <dt>
                      <CalendarDays />
                      Adicionado
                    </dt>
                    <dd>{formatarDataHora(item.criado_em)}</dd>
                  </div>
                </dl>

                <div className="book-item-footer">
                  <button
                    type="button"
                    className="btn-danger-link"
                    onClick={() => remover(item)}
                  >
                    <Trash2 />
                    Remover
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {!carregando && itens.length > 0 && totalPaginas > 1 && (
        <div className="pagination">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => irParaPagina(Math.max(1, page - 1))}
            disabled={page <= 1}
          >
            Anterior
          </button>

          <span>
            Página {page} de {totalPaginas}
          </span>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => irParaPagina(Math.min(totalPaginas, page + 1))}
            disabled={page >= totalPaginas}
          >
            Próxima
          </button>
        </div>
      )}
    </>
  );
}

export default Biblioteca;
