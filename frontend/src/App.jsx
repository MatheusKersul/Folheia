import { useState, useEffect } from 'react';

function App() {
  const [dadosLivro, setDadosLivro] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    
    fetch('http://localhost:8000/buscar-precos/O%20Hobbit?isbn=123456')
      .then((res) => res.json())
      .then((data) => {
        setDadosLivro(data); 
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching data:", err);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ textAlign: 'center', marginTop: '50px' }}>
      <h1>React + FastAPI Connection</h1>
      
      {loading ? (
        <p>Buscando preços do livro...</p>
      ) : dadosLivro ? (
        <div>
          <h2>Resultados para: {dadosLivro.titulo}</h2>
          <p>ISBN: {dadosLivro.isbn}</p>
          
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {dadosLivro.ofertas.map((oferta, index) => (
              <li key={index} style={{ marginBottom: '10px' }}>
                <strong>{oferta.loja}</strong>: R$ {oferta.preco.toFixed(2)}{' '}
                <a href={oferta.link} target="_blank" rel="noreferrer">
                  (Ir para a loja)
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>Não foi possível carregar os dados.</p>
      )}
    </div>
  );
}

export default App;