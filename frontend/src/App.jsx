import { useState, useEffect } from 'react';

import {
  Barcode,
  CalendarDays,
  BookOpen,
  FileText,
  Building2,
  User
} from 'lucide-react';

import './App.css';

import HeaderDecoration from './HeaderDecoration';

function App() {
  const [dadosLivro, setDadosLivro] = useState(null);
  const [loading, setLoading] = useState(false);
  const [termoBusca, setTermoBusca] = useState('');
  const [erroInput, setErroInput] = useState(false); // Estado para controlar o erro de input vazio
  const [tipoBusca, setTipoBusca] = useState('titulo'); 

  const realizarBusca = (e) => {
    e.preventDefault();

    if (!termoBusca.trim()) {
      setErroInput(true);
      return;
    }
    
    setErroInput(false);
    setLoading(true);

    // Agora enviamos 'tipo' e 'termo' como parâmetros para o FastAPI
    fetch(`http://localhost:8000/buscar-livros?tipo=${tipoBusca}&termo=${encodeURIComponent(termoBusca)}`)
      .then((res) => res.json())
      .then((data) => {
        setDadosLivro(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Erro ao buscar dados:", err);
        setLoading(false);
      });
  };

  return (
  <div className="app">
    <header className="header">
    <HeaderDecoration />
      <h1>Folheia</h1>
    </header>

    <main className="container">
      {/* Formulário de Pesquisa */}
     <form 
        className={`search-form ${loading ? 'fade-out' : ''}`} 
        onSubmit={realizarBusca}
      >
        {/* Nova caixa de seleção com a "setinha" */}
        <select 
          className="search-select"
          value={tipoBusca}
          onChange={(e) => setTipoBusca(e.target.value)}
        >
          <option value="titulo">Título</option>
          <option value="autor">Autor</option>
          <option value="isbn">ISBN</option>
        </select>

        <input 
          type="text" 
          className={`search-input ${erroInput ? 'input-error' : ''}`}
          placeholder={`Buscar por ${tipoBusca}...`} // O placeholder muda dinamicamente
          value={termoBusca}
          onChange={(e) => {
            setTermoBusca(e.target.value);
            setErroInput(false);
          }}
        />
        <button type="submit" className="search-button">
          Buscar
        </button>
      </form>

      {erroInput && (
        <p className="error-message">Por favor, digite algum termo para pesquisar.</p>
      )}

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
                <strong>Data de publicação:</strong>
                  {dadosLivro.data_publicacao
                  ? dadosLivro.data_publicacao.split("-").reverse().join("/")
                  : "Não informado"}
              </span>
            </p>

            <p>
              <BookOpen />
              <span>
                <strong>Formato:</strong> {dadosLivro.formato}
              </span>
            </p>

            <p>
              <FileText />
              <span>
                <strong>Páginas:</strong> {dadosLivro.num_paginas}
              </span>
            </p>

            <p>
              <Building2 />
              <span>
                <strong>Editora:</strong> {dadosLivro.editora}
              </span>
            </p>

            <p>
             <User />
              <span>
                <strong>Autor:</strong>
                {dadosLivro.autor}
              </span>
            </p>
          </div>
        </div>
      ) : (
        <p>Não foi possível carregar os dados.</p>
      )}
    </main>
  </div>
  );
}

export default App;