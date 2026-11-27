import { useState, useEffect, useCallback } from 'react';
import {
  Database,
  Table2,
  Plus,
  Trash2,
  Pencil,
  Columns3,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Terminal,
  AlertCircle,
  CheckCircle2,
  KeyRound,
  X,
  ArrowUpDown,
  Play,
} from 'lucide-react';
import { api } from '../api';

const TIPOS_SQL_COMUNS = [
  'VARCHAR(255)',
  'VARCHAR(100)',
  'TEXT',
  'INTEGER',
  'BIGINT',
  'SERIAL',
  'BIGSERIAL',
  'BOOLEAN',
  'NUMERIC(10,2)',
  'DOUBLE PRECISION',
  'DATE',
  'TIMESTAMP',
  'TIMESTAMPTZ',
  'JSONB',
  'UUID',
];

function formatarCelula(valor) {
  if (valor === null || valor === undefined) {
    return <span className="db-null-badge">NULL</span>;
  }
  if (typeof valor === 'boolean') {
    return (
      <span className={`badge-tag ${valor ? 'badge-green' : 'badge-gray'}`}>
        {valor ? 'true' : 'false'}
      </span>
    );
  }
  if (typeof valor === 'object') {
    const str = JSON.stringify(valor);
    return <code className="db-cell-code">{str.length > 60 ? `${str.slice(0, 60)}…` : str}</code>;
  }
  const texto = String(valor);
  return texto.length > 80 ? <span title={texto}>{texto.slice(0, 80)}…</span> : texto;
}

export default function AdminDatabasePanel() {
  const baseUrl = api.baseUrl;

  // Lista de tabelas e info geral do banco
  const [infoBanco, setInfoBanco] = useState(null);
  const [loadingTabelas, setLoadingTabelas] = useState(true);
  const [erroGlobal, setErroGlobal] = useState(null);
  const [feedback, setFeedback] = useState(null);

  // Tabela selecionada e seus dados
  const [tabelaAtiva, setTabelaAtiva] = useState(null);
  const [subAba, setSubAba] = useState('dados'); // 'dados' | 'estrutura'
  const [dadosTabela, setDadosTabela] = useState(null);
  const [loadingDados, setLoadingDados] = useState(false);

  // Paginação, busca e ordenação
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [buscaInput, setBuscaInput] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [orderBy, setOrderBy] = useState(null);
  const [orderDir, setOrderDir] = useState('asc');

  // Modais
  const [modalNovaTabela, setModalNovaTabela] = useState(false);
  const [modalNovaColuna, setModalNovaColuna] = useState(false);
  const [modalRegistro, setModalRegistro] = useState(null); // { modo: 'inserir' | 'editar', registro?: obj }
  const [mostrarSql, setMostrarSql] = useState(false);

  // Formulário: Nova Tabela
  const [novaTabelaNome, setNovaTabelaNome] = useState('');
  const [novaTabelaColunas, setNovaTabelaColunas] = useState([
    { nome: 'id', tipo: 'SERIAL', nullable: false, primary_key: true, default: '' },
    { nome: 'nome', tipo: 'VARCHAR(255)', nullable: false, primary_key: false, default: '' },
  ]);

  // Formulário: Nova Coluna
  const [novaColuna, setNovaColuna] = useState({
    nome: '',
    tipo: 'VARCHAR(255)',
    nullable: true,
    default: '',
  });

  // Formulário: Inserir / Editar Registro
  const [formRegistro, setFormRegistro] = useState({});
  const [salvando, setSalvando] = useState(false);

  // Console SQL
  const [sqlTexto, setSqlTexto] = useState('SELECT table_name FROM information_schema.tables WHERE table_schema = \'public\';');
  const [permitirEscritaSql, setPermitirEscritaSql] = useState(false);
  const [resultadoSql, setResultadoSql] = useState(null);
  const [executandoSql, setExecutandoSql] = useState(false);

  const mostrarMensagem = (texto, tipo = 'sucesso') => {
    setFeedback({ texto, tipo });
    setTimeout(() => setFeedback(null), 5000);
  };

  const fetchJson = async (path, options = {}) => {
    const res = await fetch(`${baseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data?.detail || `Erro HTTP ${res.status}`);
    }
    return data;
  };

  const carregarTabelas = useCallback(async (manterSelecionada = true) => {
    try {
      setLoadingTabelas(true);
      const data = await fetchJson('/admin/db/tabelas');
      setInfoBanco(data);
      setErroGlobal(null);

      setTabelaAtiva((atual) => {
        if (manterSelecionada && atual && data.tabelas.some((t) => t.nome === atual)) {
          return atual;
        }
        return data.tabelas.length > 0 ? data.tabelas[0].nome : null;
      });
    } catch (err) {
      setErroGlobal(err.message);
    } finally {
      setLoadingTabelas(false);
    }
  }, [baseUrl]);

  const carregarDadosTabela = useCallback(async () => {
    if (!tabelaAtiva) {
      setDadosTabela(null);
      return;
    }
    try {
      setLoadingDados(true);
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        order_dir: orderDir,
      });
      if (buscaAplicada) params.set('busca', buscaAplicada);
      if (orderBy) params.set('order_by', orderBy);

      const data = await fetchJson(`/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}?${params.toString()}`);
      setDadosTabela(data);
      setErroGlobal(null);
    } catch (err) {
      setErroGlobal(err.message);
    } finally {
      setLoadingDados(false);
    }
  }, [tabelaAtiva, page, limit, buscaAplicada, orderBy, orderDir, baseUrl]);

  useEffect(() => {
    carregarTabelas();
  }, [carregarTabelas]);

  useEffect(() => {
    carregarDadosTabela();
  }, [carregarDadosTabela]);

  const selecionarTabela = (nome) => {
    setTabelaAtiva(nome);
    setPage(1);
    setBuscaInput('');
    setBuscaAplicada('');
    setOrderBy(null);
    setOrderDir('asc');
  };

  const handleOrdenar = (coluna) => {
    if (orderBy === coluna) {
      setOrderDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setOrderBy(coluna);
      setOrderDir('asc');
    }
    setPage(1);
  };

  const handleBuscar = (e) => {
    e.preventDefault();
    setPage(1);
    setBuscaAplicada(buscaInput.trim());
  };

  // --- Ações de Tabela (CREATE / DROP) ---
  const handleCriarTabela = async (e) => {
    e.preventDefault();
    try {
      setSalvando(true);
      const payload = {
        nome: novaTabelaNome.trim(),
        colunas: novaTabelaColunas.map((c) => ({
          nome: c.nome.trim(),
          tipo: c.tipo,
          nullable: c.nullable,
          primary_key: c.primary_key,
          default: c.default.trim() || null,
        })),
      };
      const res = await fetchJson('/admin/db/tabelas', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      mostrarMensagem(res.mensagem);
      setModalNovaTabela(false);
      const nomeCriado = payload.nome;
      setNovaTabelaNome('');
      setNovaTabelaColunas([
        { nome: 'id', tipo: 'SERIAL', nullable: false, primary_key: true, default: '' },
        { nome: 'nome', tipo: 'VARCHAR(255)', nullable: false, primary_key: false, default: '' },
      ]);
      await carregarTabelas(false);
      selecionarTabela(nomeCriado);
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    } finally {
      setSalvando(false);
    }
  };

  const handleExcluirTabela = async () => {
    if (!tabelaAtiva) return;
    const confirmacao = window.prompt(
      `ATENÇÃO: Esta ação excluirá permanentemente a tabela "${tabelaAtiva}" e TODOS os seus dados.\n\nDigite o nome da tabela (${tabelaAtiva}) para confirmar:`
    );
    if (confirmacao !== tabelaAtiva) {
      if (confirmacao !== null) {
        mostrarMensagem('Nome incorreto. Exclusão cancelada.', 'erro');
      }
      return;
    }

    const usarCascade = window.confirm(
      'Deseja usar CASCADE (remover também chaves estrangeiras ou views dependentes)?\nClique em OK para CASCADE ou Cancelar para DROP simples.'
    );

    try {
      const res = await fetchJson(
        `/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}?cascade=${usarCascade}`,
        { method: 'DELETE' }
      );
      mostrarMensagem(res.mensagem);
      setTabelaAtiva(null);
      await carregarTabelas(false);
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    }
  };

  // --- Ações de Coluna (ADD / DROP) ---
  const handleAdicionarColuna = async (e) => {
    e.preventDefault();
    if (!tabelaAtiva) return;
    try {
      setSalvando(true);
      const res = await fetchJson(`/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}/colunas`, {
        method: 'POST',
        body: JSON.stringify({
          nome: novaColuna.nome.trim(),
          tipo: novaColuna.tipo,
          nullable: novaColuna.nullable,
          default: novaColuna.default.trim() || null,
        }),
      });
      mostrarMensagem(res.mensagem);
      setModalNovaColuna(false);
      setNovaColuna({ nome: '', tipo: 'VARCHAR(255)', nullable: true, default: '' });
      carregarTabelas(true);
      carregarDadosTabela();
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    } finally {
      setSalvando(false);
    }
  };

  const handleRemoverColuna = async (nomeColuna) => {
    if (!tabelaAtiva) return;
    if (
      !window.confirm(
        `Tem certeza que deseja remover a coluna "${nomeColuna}" da tabela "${tabelaAtiva}"? Todos os dados dessa coluna serão perdidos.`
      )
    ) {
      return;
    }
    const cascade = window.confirm(
      'Usar CASCADE caso haja restrições dependentes nesta coluna?\nOK = Sim (CASCADE) | Cancelar = Não'
    );
    try {
      const res = await fetchJson(
        `/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}/colunas/${encodeURIComponent(nomeColuna)}?cascade=${cascade}`,
        { method: 'DELETE' }
      );
      mostrarMensagem(res.mensagem);
      carregarTabelas(true);
      carregarDadosTabela();
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    }
  };

  // --- Ações de Registro (INSERT / UPDATE / DELETE) ---
  const abrirModalInserir = () => {
    if (!dadosTabela) return;
    const inicial = {};
    dadosTabela.colunas.forEach((col) => {
      // Deixa colunas com default (ex: nextval / SERIAL) vazias por padrão
      inicial[col.nome] = '';
    });
    setFormRegistro(inicial);
    setModalRegistro({ modo: 'inserir' });
  };

  const abrirModalEditar = (registro) => {
    const inicial = {};
    dadosTabela.colunas.forEach((col) => {
      const v = registro[col.nome];
      inicial[col.nome] =
        v === null || v === undefined
          ? ''
          : typeof v === 'object'
            ? JSON.stringify(v)
            : String(v);
    });
    setFormRegistro(inicial);
    setModalRegistro({ modo: 'editar', registroOriginal: registro });
  };

  const handleSalvarRegistro = async (e) => {
    e.preventDefault();
    if (!tabelaAtiva || !dadosTabela) return;

    try {
      setSalvando(true);
      if (modalRegistro.modo === 'inserir') {
        const dadosEnviar = {};
        dadosTabela.colunas.forEach((col) => {
          const val = formRegistro[col.nome];
          // Se vazio e tem default ou é nullable, omite para o PostgreSQL usar o default/NULL
          if (val === '' && (col.default || col.nullable)) {
            return;
          }
          dadosEnviar[col.nome] = val;
        });

        const res = await fetchJson(`/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}/registros`, {
          method: 'POST',
          body: JSON.stringify({ dados: dadosEnviar }),
        });
        mostrarMensagem(res.mensagem);
      } else {
        const pk = {};
        dadosTabela.chaves_primarias.forEach((pkCol) => {
          pk[pkCol] = modalRegistro.registroOriginal[pkCol];
        });

        const dadosAtualizar = {};
        dadosTabela.colunas.forEach((col) => {
          if (col.pk) return; // Não altera a PK no formulário de edição rápida
          const val = formRegistro[col.nome];
          dadosAtualizar[col.nome] = val === '' && col.nullable ? null : val;
        });

        const res = await fetchJson(`/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}/registros`, {
          method: 'PUT',
          body: JSON.stringify({ pk, dados: dadosAtualizar }),
        });
        mostrarMensagem(res.mensagem);
      }

      setModalRegistro(null);
      carregarDadosTabela();
      carregarTabelas(true);
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    } finally {
      setSalvando(false);
    }
  };

  const handleExcluirRegistro = async (registro) => {
    if (!tabelaAtiva || !dadosTabela?.chaves_primarias?.length) return;
    const pk = {};
    dadosTabela.chaves_primarias.forEach((pkCol) => {
      pk[pkCol] = registro[pkCol];
    });
    const resumoPk = Object.entries(pk)
      .map(([k, v]) => `${k}=${v}`)
      .join(', ');

    if (!window.confirm(`Deseja excluir o registro (${resumoPk}) da tabela "${tabelaAtiva}"?`)) {
      return;
    }

    try {
      const res = await fetchJson(
        `/admin/db/tabelas/${encodeURIComponent(tabelaAtiva)}/registros/deletar`,
        {
          method: 'POST',
          body: JSON.stringify({ pk }),
        }
      );
      mostrarMensagem(res.mensagem);
      carregarDadosTabela();
      carregarTabelas(true);
    } catch (err) {
      mostrarMensagem(err.message, 'erro');
    }
  };

  // --- Console SQL ---
  const handleExecutarSql = async (e) => {
    e.preventDefault();
    try {
      setExecutandoSql(true);
      const res = await fetchJson('/admin/db/consulta', {
        method: 'POST',
        body: JSON.stringify({
          sql: sqlTexto,
          permitir_escrita: permitirEscritaSql,
        }),
      });
      setResultadoSql({ ok: true, ...res });
      if (permitirEscritaSql) {
        carregarTabelas(true);
        carregarDadosTabela();
      }
    } catch (err) {
      setResultadoSql({ ok: false, erro: err.message });
    } finally {
      setExecutandoSql(false);
    }
  };

  const temPk = (dadosTabela?.chaves_primarias?.length || 0) > 0;

  return (
    <div className="db-manager-wrapper">
      {/* Barra de Status do PostgreSQL */}
      <section className="admin-toolbar">
        <div className="admin-status-indicator">
          <div className={`status-dot ${erroGlobal ? 'status-dot-error' : ''}`} />
          <div className="status-text">
            <strong>PostgreSQL RDS: {erroGlobal ? 'Erro de Conexão' : infoBanco?.banco || 'Conectado'}</strong>
            <span>
              {infoBanco?.versao && `${infoBanco.versao}`}
              {infoBanco?.tamanho_total && ` • Tamanho: ${infoBanco.tamanho_total}`}
              {infoBanco && ` • ${infoBanco.total_tabelas} tabela(s)`}
            </span>
          </div>
        </div>

        <div className="admin-actions">
          <button
            className={`db-btn-secondary ${mostrarSql ? 'active' : ''}`}
            onClick={() => setMostrarSql((v) => !v)}
          >
            <Terminal size={14} />
            Console SQL
          </button>

          <button
            className="db-btn-gold"
            onClick={() => setModalNovaTabela(true)}
          >
            <Plus size={14} />
            Nova Tabela
          </button>

          <button
            className={`btn-refresh ${loadingTabelas ? 'rotating' : ''}`}
            onClick={() => {
              carregarTabelas(true);
              carregarDadosTabela();
            }}
          >
            <RefreshCw size={14} />
            Atualizar
          </button>
        </div>
      </section>

      {feedback && (
        <div className={`db-alert ${feedback.tipo === 'erro' ? 'db-alert-error' : 'db-alert-success'}`}>
          {feedback.tipo === 'erro' ? <AlertCircle size={16} /> : <CheckCircle2 size={16} />}
          <span>{feedback.texto}</span>
        </div>
      )}

      {erroGlobal && (
        <div className="db-alert db-alert-error">
          <AlertCircle size={18} />
          <span><strong>Erro no Banco de Dados:</strong> {erroGlobal}</span>
        </div>
      )}

      {/* Console SQL Retrátil */}
      {mostrarSql && (
        <section className="admin-section-card db-sql-panel">
          <div className="section-title">
            <div>
              <h2><Terminal size={20} color="#fca311" /> Console SQL Direto</h2>
              <p>Execute consultas SELECT ou comandos DDL/DML diretamente na instância primária</p>
            </div>
            <button className="db-icon-btn" onClick={() => setMostrarSql(false)} title="Fechar console">
              <X size={18} />
            </button>
          </div>

          <form onSubmit={handleExecutarSql}>
            <textarea
              className="db-sql-textarea"
              rows={4}
              value={sqlTexto}
              onChange={(e) => setSqlTexto(e.target.value)}
              placeholder="SELECT * FROM users LIMIT 10;"
            />
            <div className="db-sql-controls">
              <label className="toggle-autorefresh">
                <input
                  type="checkbox"
                  checked={permitirEscritaSql}
                  onChange={(e) => setPermitirEscritaSql(e.target.checked)}
                />
                Permitir comandos de escrita (INSERT / UPDATE / DELETE / ALTER / DROP)
              </label>

              <button type="submit" className="btn-refresh" disabled={executandoSql}>
                <Play size={14} />
                {executandoSql ? 'Executando...' : 'Executar SQL'}
              </button>
            </div>
          </form>

          {resultadoSql && (
            <div className="db-sql-result">
              {!resultadoSql.ok ? (
                <div className="db-alert db-alert-error" style={{ marginBottom: 0 }}>
                  <AlertCircle size={16} />
                  <span>{resultadoSql.erro}</span>
                </div>
              ) : resultadoSql.tipo === 'comando' ? (
                <div className="db-alert db-alert-success" style={{ marginBottom: 0 }}>
                  <CheckCircle2 size={16} />
                  <span>{resultadoSql.mensagem} ({resultadoSql.tempo_ms} ms)</span>
                </div>
              ) : (
                <div>
                  <div className="db-sql-meta">
                    <span>{resultadoSql.total_retornado} linha(s) retornada(s){resultadoSql.limitado_200 ? ' (limite de 200)' : ''}</span>
                    <span>Tempo: {resultadoSql.tempo_ms} ms</span>
                  </div>
                  <div style={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
                    <table className="admin-table">
                      <thead>
                        <tr>
                          {resultadoSql.colunas.map((c) => (
                            <th key={c}>{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {resultadoSql.registros.map((row, i) => (
                          <tr key={i}>
                            {resultadoSql.colunas.map((c) => (
                              <td key={c}>{formatarCelula(row[c])}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Layout Principal: Sidebar de Tabelas + Explorador */}
      <div className="db-layout">
        {/* Lista Lateral de Tabelas */}
        <aside className="admin-section-card db-sidebar">
          <div className="db-sidebar-header">
            <h3><Database size={16} color="#fca311" /> Tabelas ({infoBanco?.total_tabelas || 0})</h3>
          </div>

          {loadingTabelas && !infoBanco ? (
            <p className="db-muted">Carregando tabelas...</p>
          ) : infoBanco?.tabelas?.length > 0 ? (
            <ul className="db-table-list">
              {infoBanco.tabelas.map((t) => (
                <li key={t.nome}>
                  <button
                    className={`db-table-item ${tabelaAtiva === t.nome ? 'active' : ''}`}
                    onClick={() => selecionarTabela(t.nome)}
                  >
                    <div className="db-table-item-top">
                      <Table2 size={14} />
                      <span className="db-table-name">{t.nome}</span>
                    </div>
                    <div className="db-table-item-meta">
                      <span>~{t.linhas_estimadas} lin.</span>
                      <span>{t.total_colunas} col.</span>
                      <span>{t.tamanho}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="db-muted">Nenhuma tabela encontrada no schema public.</p>
          )}
        </aside>

        {/* Painel da Tabela Selecionada */}
        <section className="admin-section-card db-workspace">
          {!tabelaAtiva ? (
            <div className="db-empty-state">
              <Database size={36} color="#94a3b8" />
              <p>Selecione uma tabela à esquerda ou crie uma nova tabela para começar.</p>
            </div>
          ) : (
            <>
              <div className="section-title db-workspace-header">
                <div>
                  <h2>
                    <Table2 size={20} color="#fca311" />
                    {tabelaAtiva}
                    {dadosTabela && (
                      <span className="badge-tag badge-blue">
                        {dadosTabela.total_registros} registro(s)
                      </span>
                    )}
                  </h2>
                  <p>
                    {dadosTabela?.chaves_primarias?.length > 0
                      ? `Chave Primária: ${dadosTabela.chaves_primarias.join(', ')}`
                      : 'Tabela sem chave primária (edição/exclusão por linha desabilitada)'}
                  </p>
                </div>

                <div className="db-workspace-actions">
                  <button className="db-btn-gold" onClick={abrirModalInserir}>
                    <Plus size={14} /> Novo Registro
                  </button>
                  <button className="db-btn-secondary" onClick={() => setModalNovaColuna(true)}>
                    <Columns3 size={14} /> + Coluna
                  </button>
                  <button className="db-btn-danger" onClick={handleExcluirTabela}>
                    <Trash2 size={14} /> Excluir Tabela
                  </button>
                </div>
              </div>

              {/* Sub-abas: Dados vs Estrutura */}
              <div className="db-subtabs">
                <button
                  className={`db-subtab ${subAba === 'dados' ? 'active' : ''}`}
                  onClick={() => setSubAba('dados')}
                >
                  <Table2 size={14} /> Dados da Tabela
                </button>
                <button
                  className={`db-subtab ${subAba === 'estrutura' ? 'active' : ''}`}
                  onClick={() => setSubAba('estrutura')}
                >
                  <Columns3 size={14} /> Estrutura / Colunas ({dadosTabela?.colunas?.length || 0})
                </button>
              </div>

              {subAba === 'dados' ? (
                <>
                  {/* Barra de Busca e Limite */}
                  <form className="db-filter-row" onSubmit={handleBuscar}>
                    <div className="db-search-box">
                      <Search size={15} color="#64748b" />
                      <input
                        type="text"
                        placeholder={`Pesquisar em todas as colunas de "${tabelaAtiva}"...`}
                        value={buscaInput}
                        onChange={(e) => setBuscaInput(e.target.value)}
                      />
                      {buscaAplicada && (
                        <button
                          type="button"
                          className="db-icon-btn"
                          onClick={() => {
                            setBuscaInput('');
                            setBuscaAplicada('');
                            setPage(1);
                          }}
                          title="Limpar busca"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>

                    <button type="submit" className="btn-refresh">Buscar</button>

                    <select
                      className="db-select"
                      value={limit}
                      onChange={(e) => {
                        setLimit(Number(e.target.value));
                        setPage(1);
                      }}
                    >
                      <option value={15}>15 / pág</option>
                      <option value={25}>25 / pág</option>
                      <option value={50}>50 / pág</option>
                      <option value={100}>100 / pág</option>
                    </select>
                  </form>

                  {/* Grade de Dados */}
                  <div className="db-table-scroll">
                    {loadingDados ? (
                      <p className="db-muted" style={{ padding: 24, textAlign: 'center' }}>
                        Carregando registros...
                      </p>
                    ) : dadosTabela?.colunas?.length > 0 ? (
                      <table className="admin-table">
                        <thead>
                          <tr>
                            {dadosTabela.colunas.map((col) => (
                              <th
                                key={col.nome}
                                className="db-sortable-th"
                                onClick={() => handleOrdenar(col.nome)}
                                title={`Ordenar por ${col.nome}`}
                              >
                                <span className="db-th-content">
                                  {col.pk && <KeyRound size={12} color="#fca311" />}
                                  {col.nome}
                                  <ArrowUpDown size={11} style={{ opacity: orderBy === col.nome ? 1 : 0.35 }} />
                                </span>
                              </th>
                            ))}
                            <th style={{ textAlign: 'center', width: 90 }}>Ações</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dadosTabela.registros.length > 0 ? (
                            dadosTabela.registros.map((row, idx) => (
                              <tr key={idx}>
                                {dadosTabela.colunas.map((col) => (
                                  <td key={col.nome}>{formatarCelula(row[col.nome])}</td>
                                ))}
                                <td style={{ textAlign: 'center', whiteSpace: 'nowrap' }}>
                                  <button
                                    className="db-row-action edit"
                                    disabled={!temPk}
                                    onClick={() => abrirModalEditar(row)}
                                    title={temPk ? 'Editar linha' : 'Requer chave primária'}
                                  >
                                    <Pencil size={14} />
                                  </button>
                                  <button
                                    className="db-row-action delete"
                                    disabled={!temPk}
                                    onClick={() => handleExcluirRegistro(row)}
                                    title={temPk ? 'Excluir linha' : 'Requer chave primária'}
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                </td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td
                                colSpan={dadosTabela.colunas.length + 1}
                                style={{ textAlign: 'center', color: '#94a3b8', padding: 28 }}
                              >
                                Nenhum registro encontrado.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    ) : null}
                  </div>

                  {/* Paginação */}
                  {dadosTabela && (
                    <div className="db-pagination">
                      <span className="db-muted">
                        Página <strong>{dadosTabela.page}</strong> de <strong>{dadosTabela.total_paginas}</strong> • Total: {dadosTabela.total_registros} registro(s)
                      </span>
                      <div className="db-pagination-btns">
                        <button
                          className="db-btn-secondary"
                          disabled={page <= 1}
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                        >
                          <ChevronLeft size={14} /> Anterior
                        </button>
                        <button
                          className="db-btn-secondary"
                          disabled={page >= dadosTabela.total_paginas}
                          onClick={() => setPage((p) => p + 1)}
                        >
                          Próxima <ChevronRight size={14} />
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                /* Sub-aba Estrutura / Colunas */
                <div className="db-table-scroll">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Coluna</th>
                        <th>Tipo SQL</th>
                        <th>Chave</th>
                        <th>Permite NULL</th>
                        <th>Valor Padrão (DEFAULT)</th>
                        <th style={{ textAlign: 'center' }}>Remover</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dadosTabela?.colunas?.map((col) => (
                        <tr key={col.nome}>
                          <td><strong>{col.nome}</strong></td>
                          <td><code className="db-cell-code">{col.tipo}</code></td>
                          <td>
                            {col.pk ? (
                              <span className="badge-tag badge-gold">PRIMARY KEY</span>
                            ) : (
                              <span style={{ color: '#94a3b8' }}>—</span>
                            )}
                          </td>
                          <td>
                            <span className={`badge-tag ${col.nullable ? 'badge-gray' : 'badge-blue'}`}>
                              {col.nullable ? 'NULL' : 'NOT NULL'}
                            </span>
                          </td>
                          <td>
                            {col.default ? (
                              <code className="db-cell-code">{col.default}</code>
                            ) : (
                              <span style={{ color: '#94a3b8' }}>—</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <button
                              className="db-row-action delete"
                              onClick={() => handleRemoverColuna(col.nome)}
                              title={`Remover coluna ${col.nome}`}
                            >
                              <Trash2 size={15} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      {/* MODAL: Criar Nova Tabela */}
      {modalNovaTabela && (
        <div className="db-modal-backdrop" onClick={() => setModalNovaTabela(false)}>
          <div className="db-modal db-modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-header">
              <h3><Table2 size={18} color="#fca311" /> Criar Nova Tabela</h3>
              <button className="db-icon-btn" onClick={() => setModalNovaTabela(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCriarTabela}>
              <div className="db-form-group">
                <label>Nome da Tabela (schema public)</label>
                <input
                  type="text"
                  required
                  placeholder="ex: anotacoes_leitura"
                  value={novaTabelaNome}
                  onChange={(e) => setNovaTabelaNome(e.target.value)}
                />
              </div>

              <div className="db-form-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <label style={{ margin: 0 }}>Colunas</label>
                  <button
                    type="button"
                    className="db-btn-secondary"
                    onClick={() =>
                      setNovaTabelaColunas((prev) => [
                        ...prev,
                        { nome: '', tipo: 'VARCHAR(255)', nullable: true, primary_key: false, default: '' },
                      ])
                    }
                  >
                    <Plus size={13} /> Adicionar Coluna
                  </button>
                </div>

                <div className="db-columns-builder">
                  {novaTabelaColunas.map((col, idx) => (
                    <div key={idx} className="db-column-row">
                      <input
                        type="text"
                        required
                        placeholder="nome_coluna"
                        value={col.nome}
                        onChange={(e) => {
                          const next = [...novaTabelaColunas];
                          next[idx].nome = e.target.value;
                          setNovaTabelaColunas(next);
                        }}
                      />
                      <select
                        value={col.tipo}
                        onChange={(e) => {
                          const next = [...novaTabelaColunas];
                          next[idx].tipo = e.target.value;
                          setNovaTabelaColunas(next);
                        }}
                      >
                        {TIPOS_SQL_COMUNS.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                      <input
                        type="text"
                        placeholder="Default (opc.)"
                        value={col.default}
                        onChange={(e) => {
                          const next = [...novaTabelaColunas];
                          next[idx].default = e.target.value;
                          setNovaTabelaColunas(next);
                        }}
                      />
                      <label className="db-check-inline">
                        <input
                          type="checkbox"
                          checked={col.primary_key}
                          onChange={(e) => {
                            const next = [...novaTabelaColunas];
                            next[idx].primary_key = e.target.checked;
                            if (e.target.checked) next[idx].nullable = false;
                            setNovaTabelaColunas(next);
                          }}
                        />
                        PK
                      </label>
                      <label className="db-check-inline">
                        <input
                          type="checkbox"
                          checked={col.nullable}
                          disabled={col.primary_key}
                          onChange={(e) => {
                            const next = [...novaTabelaColunas];
                            next[idx].nullable = e.target.checked;
                            setNovaTabelaColunas(next);
                          }}
                        />
                        NULL
                      </label>
                      {novaTabelaColunas.length > 1 && (
                        <button
                          type="button"
                          className="db-row-action delete"
                          onClick={() =>
                            setNovaTabelaColunas((prev) => prev.filter((_, i) => i !== idx))
                          }
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="db-modal-footer">
                <button type="button" className="db-btn-secondary" onClick={() => setModalNovaTabela(false)}>
                  Cancelar
                </button>
                <button type="submit" className="db-btn-gold" disabled={salvando}>
                  {salvando ? 'Criando...' : 'Criar Tabela'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Adicionar Coluna */}
      {modalNovaColuna && (
        <div className="db-modal-backdrop" onClick={() => setModalNovaColuna(false)}>
          <div className="db-modal" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-header">
              <h3><Columns3 size={18} color="#fca311" /> Adicionar Coluna em "{tabelaAtiva}"</h3>
              <button className="db-icon-btn" onClick={() => setModalNovaColuna(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleAdicionarColuna}>
              <div className="db-form-group">
                <label>Nome da Coluna</label>
                <input
                  type="text"
                  required
                  placeholder="ex: observacao"
                  value={novaColuna.nome}
                  onChange={(e) => setNovaColuna({ ...novaColuna, nome: e.target.value })}
                />
              </div>

              <div className="db-form-group">
                <label>Tipo de Dado PostgreSQL</label>
                <select
                  value={novaColuna.tipo}
                  onChange={(e) => setNovaColuna({ ...novaColuna, tipo: e.target.value })}
                >
                  {TIPOS_SQL_COMUNS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="db-form-group">
                <label>Valor Padrão (DEFAULT - opcional)</label>
                <input
                  type="text"
                  placeholder="ex: 0, TRUE, CURRENT_TIMESTAMP ou texto"
                  value={novaColuna.default}
                  onChange={(e) => setNovaColuna({ ...novaColuna, default: e.target.value })}
                />
              </div>

              <div className="db-form-group">
                <label className="db-check-inline">
                  <input
                    type="checkbox"
                    checked={novaColuna.nullable}
                    onChange={(e) => setNovaColuna({ ...novaColuna, nullable: e.target.checked })}
                  />
                  Permitir valores NULL (recomendado se a tabela já tiver linhas sem DEFAULT)
                </label>
              </div>

              <div className="db-modal-footer">
                <button type="button" className="db-btn-secondary" onClick={() => setModalNovaColuna(false)}>
                  Cancelar
                </button>
                <button type="submit" className="db-btn-gold" disabled={salvando}>
                  {salvando ? 'Adicionando...' : 'Adicionar Coluna'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: Inserir / Editar Registro */}
      {modalRegistro && dadosTabela && (
        <div className="db-modal-backdrop" onClick={() => setModalRegistro(null)}>
          <div className="db-modal" onClick={(e) => e.stopPropagation()}>
            <div className="db-modal-header">
              <h3>
                {modalRegistro.modo === 'inserir' ? (
                  <><Plus size={18} color="#fca311" /> Novo Registro em "{tabelaAtiva}"</>
                ) : (
                  <><Pencil size={18} color="#fca311" /> Editar Registro em "{tabelaAtiva}"</>
                )}
              </h3>
              <button className="db-icon-btn" onClick={() => setModalRegistro(null)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSalvarRegistro}>
              <div className="db-modal-scroll">
                {dadosTabela.colunas.map((col) => {
                  const bloqueado = modalRegistro.modo === 'editar' && col.pk;
                  return (
                    <div key={col.nome} className="db-form-group">
                      <label>
                        {col.nome}{' '}
                        <span className="db-field-type">
                          ({col.tipo}{col.pk ? ', PK' : ''}{!col.nullable ? ', NOT NULL' : ''})
                        </span>
                      </label>
                      <input
                        type="text"
                        disabled={bloqueado}
                        placeholder={
                          col.default
                            ? `Default: ${col.default}`
                            : col.nullable
                              ? 'NULL (deixe vazio)'
                              : 'Obrigatório'
                        }
                        value={formRegistro[col.nome] ?? ''}
                        onChange={(e) =>
                          setFormRegistro((prev) => ({ ...prev, [col.nome]: e.target.value }))
                        }
                      />
                    </div>
                  );
                })}
              </div>

              <div className="db-modal-footer">
                <button type="button" className="db-btn-secondary" onClick={() => setModalRegistro(null)}>
                  Cancelar
                </button>
                <button type="submit" className="db-btn-gold" disabled={salvando}>
                  {salvando ? 'Salvando...' : modalRegistro.modo === 'inserir' ? 'Inserir' : 'Salvar Alterações'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
