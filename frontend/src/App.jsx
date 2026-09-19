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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/buscar-livros?isbn=9788595084742&titulo=O%20Hobbit')
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
        setDadosLivro(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Erro ao buscar dados:", err);
        setLoading(false);
      });
  }, []);

  return (
  <div className="app">
    <header className="header">
    <HeaderDecoration />
      <h1>Folheia</h1>
    </header>

    <main className="container">
      {loading ? (
        <p>Buscando dados do livro...</p>
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