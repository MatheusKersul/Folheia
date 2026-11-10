import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Barcode,
  CalendarDays,
  BookOpen,
  BookPlus,
  FileText,
  Building2,
  User,
} from 'lucide-react';

import { api } from '../api';
import { useAuth } from '../auth/useAuth';

const OPCOES_BUSCA = [
  { valor: 'titulo', rotulo: 'Título' },
  { valor: 'autor', rotulo: 'Autor' },
  { valor: 'isbn', rotulo: 'ISBN' },
];

function formatarData(valor) {
  return valor ? valor.split('-').reverse().join('/') : 'Não informado';
}

function Home() {
  const { autenticado, token, logout } = useAuth();
  const navigate = useNavigate();

  const [dadosLivro, setDadosLivro] = useState(null);
  const [loading, setLoading] = useState(false);
  const [termoBusca, setTermoBusca] = useState('');
  const [tipoBusca, setTipoBusca] = useState('titulo');
  const [erro, setErro] = useState('');
  const [adicionando, setAdicionando] = useState(false);
  const [mensagemBiblioteca, setMensagemBiblioteca] = useState(null);

  const realizarBusca = async (evento) => {
    evento.preventDefault();

    if (!termoBusca.trim()) {
      setErro('Por favor, digite algum termo para pesquisar.');
      return;
    }

    setErro('');
    setMensagemBiblioteca(null);
    setDadosLivro(null);
    setLoading(true);

    try {
      const resultado = await api.buscarLivros({
        tipo: tipoBusca,
        termo: termoBusca.trim(),
      });
      setDadosLivro(resultado);
    } catch (falha) {
      if (falha.status === 401) {
        logout();
      }
      setErro(falha.message);
    } finally {
      setLoading(false);
    }
  };

  const adicionarNaBiblioteca = async () => {
    if (!autenticado) {
      navigate('/login', { state: { from: '/' } });
      return;
    }

    setAdicionando(true);
    setMensagemBiblioteca(null);

    try {
      await api.adicionarLivro(token, { isbn: dadosLivro.isbn });
      setMensagemBiblioteca({
        tipo: 'sucesso',
        texto: 'Obra adicionada à sua biblioteca.',
      });
    } catch (falha) {
      if (falha.status === 401) {
        logout();
        navigate('/login', { state: { from: '/' } });
        return;
      }

      setMensagemBiblioteca({
        tipo: falha.status === 409 ? 'info' : 'erro',
        texto: falha.message,
      });
    } finally {
      setAdicionando(false);
    }
  };

  return (
    <>
      <form
        className={`search-form ${loading ? 'fade-out' : ''}`}
        onSubmit={realizarBusca}
      >
        <select
          className="search-select"
          value={tipoBusca}
          onChange={(evento) => setTipoBusca(evento.target.value)}
          aria-label="Tipo de busca"
        >
          {OPCOES_BUSCA.map((opcao) => (
            <option key={opcao.valor} value={opcao.valor}>
              {opcao.rotulo}
            </option>
          ))}
        </select>

        <input
          type="text"
          className={`search-input ${erro ? 'input-error' : ''}`}
          placeholder={`Buscar por ${tipoBusca}...`}
          value={termoBusca}
          onChange={(evento) => {
            setTermoBusca(evento.target.value);
            setErro('');
          }}
        />

        <button type="submit" className="search-button">
          Buscar
        </button>
      </form>

      {erro && <div className="alert alert-error alert-center">{erro}</div>}

      {loading ? (
        <p className="loading-message">Buscando dados do livro...</p>
      ) : dadosLivro ? (
        <div className="book-card">
          <h2>{dadosLivro.titulo}</h2>

          <div className="book-info">
            <p>
              <Barcode />
              <span>
                <strong>ISBN:</strong> {dadosLivro.isbn}
              </span>
            </p>

            <p>
              <CalendarDays />
              <span>
                <strong>Data de publicação:</strong>{' '}
                {formatarData(dadosLivro.data_publicacao)}
              </span>
            </p>

            <p>
              <BookOpen />
              <span>
                <strong>Formato:</strong> {dadosLivro.formato || 'Não informado'}
              </span>
            </p>

            <p>
              <FileText />
              <span>
                <strong>Páginas:</strong>{' '}
                {dadosLivro.num_paginas || 'Não informado'}
              </span>
            </p>

            <p>
              <Building2 />
              <span>
                <strong>Editora:</strong>{' '}
                {dadosLivro.editora || 'Não informado'}
              </span>
            </p>

            <p>
              <User />
              <span>
                <strong>Autor:</strong> {dadosLivro.autor || 'Não informado'}
              </span>
            </p>
          </div>

          {mensagemBiblioteca && (
            <div className={`alert alert-${mensagemBiblioteca.tipo}`}>
              {mensagemBiblioteca.texto}
            </div>
          )}

          <div className="book-card-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={adicionarNaBiblioteca}
              disabled={adicionando}
            >
              <BookPlus />
              {adicionando ? 'Adicionando...' : 'Adicionar à minha biblioteca'}
            </button>
          </div>
        </div>
      ) : (
        !erro && (
          <div className="search-hint">
            Pesquise uma obra por título, autor ou ISBN para ver seus dados.
          </div>
        )
      )}
    </>
  );
}

export default Home;
