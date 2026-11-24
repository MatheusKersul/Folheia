import React, { useState, useRef, useEffect } from 'react';
import { ReactReader, ReactReaderStyle } from 'react-reader';

export default function EbookReader() {
  // URL padrão: arquivo local de Duna na pasta public do frontend
  const [bookUrl, setBookUrl] = useState('/duna.epub');
  
  // Recupera a última posição salva ou inicia do começo (0)
  const [location, setLocation] = useState(() => {
    return localStorage.getItem('ebook-location-duna') || 0;
  });

  const [fontSize, setFontSize] = useState(100);
  const [darkMode, setDarkMode] = useState(false);
  const renditionRef = useRef(null);

  // Salva o progresso sempre que o usuário muda de página
  const handleLocationChanged = (epubcfi) => {
    setLocation(epubcfi);
    localStorage.setItem('ebook-location-duna', epubcfi);
  };

  // Carrega um arquivo .epub do computador do usuário
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setBookUrl(e.target.result); // Passa o ArrayBuffer direto para o leitor
        setLocation(0); // Reinicia na primeira página
      };
      reader.readAsArrayBuffer(file);
    }
  };

  // Aplica tamanho de fonte e tema sempre que forem alterados
  useEffect(() => {
    if (renditionRef.current) {
      renditionRef.current.themes.fontSize(`${fontSize}%`);
      renditionRef.current.themes.override(
        'color',
        darkMode ? '#e5e7eb' : '#111827'
      );
      renditionRef.current.themes.override(
        'background',
        darkMode ? '#1f2937' : '#ffffff'
      );
    }
  }, [fontSize, darkMode]);

  // Customização visual da moldura do ReactReader para o modo escuro
  const readerStyles = darkMode
    ? {
        ...ReactReaderStyle,
        readerArea: {
          ...ReactReaderStyle.readerArea,
          backgroundColor: '#1f2937',
          transition: 'background-color 0.2s ease',
        },
        titleArea: {
          ...ReactReaderStyle.titleArea,
          color: '#9ca3af',
        },
        tocArea: {
          ...ReactReaderStyle.tocArea,
          background: '#111827',
          color: '#f3f4f6',
        },
      }
    : ReactReaderStyle;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Barra de Ferramentas Superior */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 20px',
          backgroundColor: darkMode ? '#111827' : '#f3f4f6',
          color: darkMode ? '#f9fafb' : '#111827',
          borderBottom: '1px solid #d1d5db',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <label
            style={{
              cursor: 'pointer',
              padding: '6px 12px',
              backgroundColor: '#2563eb',
              color: '#fff',
              borderRadius: '6px',
              fontSize: '14px',
            }}
          >
            Abrir arquivo .EPUB
            <input
              type="file"
              accept=".epub"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
          </label>
        </div>

        {/* Controles de Leitura */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setFontSize((prev) => Math.max(70, prev - 10))}
            style={buttonStyle}
            title="Diminuir fonte"
          >
            A-
          </button>
          <span style={{ fontSize: '14px', minWidth: '45px', textAlign: 'center' }}>
            {fontSize}%
          </span>
          <button
            onClick={() => setFontSize((prev) => Math.min(180, prev + 10))}
            style={buttonStyle}
            title="Aumentar fonte"
          >
            A+
          </button>

          <button
            onClick={() => setDarkMode((prev) => !prev)}
            style={{ ...buttonStyle, marginLeft: '10px' }}
          >
            {darkMode ? '☀️ Claro' : '🌙 Escuro'}
          </button>
        </div>
      </header>

      {/* Área Principal do Leitor (precisa ter altura definida) */}
      <main style={{ flex: 1, position: 'relative' }}>
        <ReactReader
          url={bookUrl}
          location={location}
          locationChanged={handleLocationChanged}
          readerStyles={readerStyles}
          getRendition={(rendition) => {
            renditionRef.current = rendition;
            rendition.themes.fontSize(`${fontSize}%`);
          }}
        />
      </main>
    </div>
  );
}

const buttonStyle = {
  padding: '6px 10px',
  borderRadius: '6px',
  border: '1px solid #9ca3af',
  backgroundColor: 'transparent',
  color: 'inherit',
  cursor: 'pointer',
  fontSize: '14px',
};