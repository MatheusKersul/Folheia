import { useState, useEffect, useCallback } from 'react';
import {
  Server,
  HardDrive,
  Layers,
  Cpu,
  Clock,
  Key,
  RefreshCw,
  Trash2,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Database,
  Activity,
  Layers3
} from 'lucide-react';
import './AdminDashboard.css';

export default function AdminDashboard({ onVoltar }) {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [filtroCategoria, setFiltroCategoria] = useState('Todas');
  const [acaoStatus, setAcaoStatus] = useState(null);

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/admin/telemetria/redis');
      if (!res.ok) {
        throw new Error(`Erro ${res.status}: Não foi possível carregar a telemetria.`);
      }
      const data = await res.json();
      setDados(data);
      setErro(null);
    } catch (err) {
      setErro(err.message || 'Falha ao conectar com o backend/Redis.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      carregarDados();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, carregarDados]);

  const handleLimparFila = async () => {
    if (!window.confirm('Tem certeza que deseja limpar todas as tarefas pendentes da fila?')) return;
    try {
      const res = await fetch('http://localhost:8000/admin/limpar-fila', { method: 'POST' });
      const data = await res.json();
      setAcaoStatus(data.mensagem);
      setTimeout(() => setAcaoStatus(null), 3000);
      carregarDados();
    } catch (err) {
      alert('Erro ao limpar fila: ' + err.message);
    }
  };

  const handleExcluirChave = async (chave) => {
    if (!window.confirm(`Deseja remover a chave "${chave}" do Redis?`)) return;
    try {
      const res = await fetch(`http://localhost:8000/admin/chaves/${encodeURIComponent(chave)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        carregarDados();
      }
    } catch (err) {
      alert('Erro ao excluir chave: ' + err.message);
    }
  };

  const chavesFiltradas = dados?.chaves?.lista?.filter((c) => {
    if (filtroCategoria === 'Todas') return true;
    return c.categoria === filtroCategoria;
  }) || [];

  const categorias = dados?.chaves?.por_categoria ? ['Todas', ...Object.keys(dados.chaves.por_categoria)] : ['Todas'];

  return (
    <div className="admin-page">
      {/* Cabeçalho Admin (Folheia Style) */}
      <header className="admin-header">
        <div className="admin-header-title">
          <h1>
            Folheia
            <span className="badge-adm">ADMIN</span>
          </h1>
          <p>Painel de Controle e Telemetria do Sistema</p>
        </div>

        <div className="admin-header-nav">
          <button className="btn-voltar" onClick={onVoltar} title="Voltar para a busca de livros">
            <ArrowLeft size={16} />
            Voltar ao Catálogo
          </button>
        </div>
      </header>

      <main className="admin-container">
        {/* Barra de Status e Ações */}
        <section className="admin-toolbar">
          <div className="admin-status-indicator">
            <div className={`status-dot ${erro ? 'status-dot-error' : ''}`} />
            <div className="status-text">
              <strong>Redis Broker: {erro ? 'Desconectado' : 'Operacional'}</strong>
              <span>
                {dados?.servidor?.versao && `v${dados.servidor.versao}`}
                {dados?.servidor?.uptime_formatado && ` • Ativo há ${dados.servidor.uptime_formatado}`}
                {dados?.replicacao?.papel && ` • Papel: ${dados.replicacao.papel.toUpperCase()} (${dados.replicacao.replicas_conectadas} réplica${dados.replicacao.replicas_conectadas !== 1 ? 's' : ''})`}
              </span>
            </div>
          </div>

          <div className="admin-actions">
            <label className="toggle-autorefresh">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Atualização automática (5s)
            </label>

            <button
              className={`btn-refresh ${loading ? 'rotating' : ''}`}
              onClick={carregarDados}
              disabled={loading}
            >
              <RefreshCw size={14} />
              Atualizar Agora
            </button>
          </div>
        </section>

        {acaoStatus && (
          <div style={{ background: '#dcfce7', color: '#166534', padding: '12px 18px', borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
            ✓ {acaoStatus}
          </div>
        )}

        {erro && (
          <div style={{ background: '#fee2e2', color: '#991b1b', padding: '16px 20px', borderRadius: 10, marginBottom: 24, display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertCircle size={20} />
            <div>
              <strong>Erro de Conexão:</strong> {erro}
            </div>
          </div>
        )}

        {/* Grid de Métricas Principais (Cards Dourados) */}
        <section className="admin-grid-metricas">
          {/* Card 1: Memória */}
          <div className="metric-card">
            <div className="metric-header">
              <span className="label">Memória Redis</span>
              <div className="icon-wrapper"><HardDrive size={20} /></div>
            </div>
            <div className="metric-value">
              {dados?.memoria?.usada_human || '--'}
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{ width: `${Math.min(dados?.memoria?.porcentagem_uso || 0, 100)}%` }}
              />
            </div>
            <div className="metric-subtext">
              Limite máx: {dados?.memoria?.max_human || '256M'} ({dados?.memoria?.porcentagem_uso || 0}% em uso)
            </div>
          </div>

          {/* Card 2: Fila de Scraping */}
          <div className="metric-card">
            <div className="metric-header">
              <span className="label">Fila de Tarefas</span>
              <div className="icon-wrapper"><Layers size={20} /></div>
            </div>
            <div className="metric-value">
              {dados?.fila?.total_pendentes ?? '--'}
            </div>
            <div className="metric-subtext">
              {dados?.fila?.total_itens_espera || 0} ISBN(s) no set de deduplicação
            </div>
          </div>

          {/* Card 3: Workers Ativos */}
          <div className="metric-card">
            <div className="metric-header">
              <span className="label">Workers Ativos</span>
              <div className="icon-wrapper"><Cpu size={20} /></div>
            </div>
            <div className="metric-value">
              {dados?.workers?.total_online ?? '--'}
            </div>
            <div className="metric-subtext">
              {dados?.workers?.total_online === 3 ? 'Todas as 3 réplicas ativas' : 'Réplicas conectadas via heartbeat'}
            </div>
          </div>

          {/* Card 4: Tempo Médio de Scraping */}
          <div className="metric-card">
            <div className="metric-header">
              <span className="label">Tempo Médio</span>
              <div className="icon-wrapper"><Clock size={20} /></div>
            </div>
            <div className="metric-value">
              {dados?.workers?.tempo_medio_segundos ? `${dados.workers.tempo_medio_segundos}s` : '--'}
            </div>
            <div className="metric-subtext">
              Por consulta na Bright Data / Scraper
            </div>
          </div>
        </section>

        {/* Seção 1: Workers e Monitoramento de Processamento */}
        <section className="admin-section-card">
          <div className="section-title">
            <div>
              <h2><Activity size={20} color="#fca311" /> Réplicas do Worker & Processamento</h2>
              <p>Status em tempo real das instâncias do scraper-worker e histórico de execuções</p>
            </div>
          </div>

          {/* Cards dos Workers Online */}
          <div className="workers-list">
            {dados?.workers?.lista_online?.length > 0 ? (
              dados.workers.lista_online.map((w) => (
                <div key={w.worker_id} className="worker-item">
                  <div className="worker-item-header">
                    <strong>ID: {w.worker_id}</strong>
                    <span className="badge-tag badge-green">ONLINE</span>
                  </div>
                  <div className="worker-item-body">
                    <span>Último ISBN: <strong>{w.ultimo_isbn}</strong></span>
                    <span>Tempo da última tarefa: <strong>{w.ultima_duracao_s !== '-' ? `${w.ultima_duracao_s}s` : '-'}</strong></span>
                    <span>Status: <span style={{ textTransform: 'capitalize' }}>{w.ultimo_status}</span></span>
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: '#64748b', fontSize: 13, margin: '8px 0' }}>
                Nenhum worker detectado via heartbeat recente. Verifique se os containers <code>scraper-worker</code> estão rodando.
              </p>
            )}
          </div>

          {/* Tabela de Tarefas Recentes */}
          <h3 style={{ fontSize: 15, color: '#14213d', margin: '20px 0 10px 0', textTransform: 'uppercase', letterSpacing: 0.8 }}>
            Últimas Tarefas Concluídas
          </h3>
          {dados?.workers?.tarefas_recentes?.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Horário</th>
                    <th>Worker</th>
                    <th>ISBN</th>
                    <th>Duração</th>
                    <th>Ofertas</th>
                    <th>Resultado</th>
                  </tr>
                </thead>
                <tbody>
                  {dados.workers.tarefas_recentes.map((t, idx) => (
                    <tr key={idx}>
                      <td>{new Date(t.timestamp * 1000).toLocaleTimeString()}</td>
                      <td><code>{t.worker_id}</code></td>
                      <td><strong>{t.isbn}</strong></td>
                      <td>{t.duracao_s}s</td>
                      <td>{t.ofertas} oferta(s)</td>
                      <td>
                        <span className={`badge-tag ${t.sucesso ? 'badge-green' : 'badge-gold'}`}>
                          {t.sucesso ? 'Sucesso' : 'Vazio / Não Encontrado'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ color: '#64748b', fontSize: 13 }}>
              Nenhuma tarefa registrada no histórico ainda. Enfileire um ISBN para visualizar as métricas aqui.
            </p>
          )}
        </section>

        {/* Seção 2: Fila e Locks Ativos */}
        <section className="admin-section-card">
          <div className="section-title">
            <div>
              <h2><Layers3 size={20} color="#fca311" /> Fila e Locks Distribuídos</h2>
              <p>Coordenação de concorrência e tarefas bloqueadas temporariamente</p>
            </div>
            {dados?.fila?.total_pendentes > 0 && (
              <button
                onClick={handleLimparFila}
                style={{ background: '#fee2e2', border: '1px solid #fca5a5', color: '#991b1b', padding: '6px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer', fontWeight: 600 }}
              >
                Purgar Fila
              </button>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            <div style={{ background: '#f8fafc', padding: 18, borderRadius: 10, border: '1px solid #e2e8f0' }}>
              <strong style={{ fontSize: 13, textTransform: 'uppercase', color: '#14213d' }}>
                Itens na Fila Temporária (Anti-duplicação):
              </strong>
              <div style={{ marginTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {dados?.fila?.itens_em_espera?.length > 0 ? (
                  dados.fila.itens_em_espera.map((isbn) => (
                    <span key={isbn} className="badge-tag badge-blue">{isbn}</span>
                  ))
                ) : (
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Nenhum item aguardando no momento</span>
                )}
              </div>
            </div>

            <div style={{ background: '#f8fafc', padding: 18, borderRadius: 10, border: '1px solid #e2e8f0' }}>
              <strong style={{ fontSize: 13, textTransform: 'uppercase', color: '#14213d' }}>
                Locks Ativos no Redis:
              </strong>
              <div style={{ marginTop: 10 }}>
                {dados?.fila?.locks_ativos?.length > 0 ? (
                  dados.fila.locks_ativos.map((lock) => (
                    <div key={lock.chave} style={{ fontSize: 13, color: '#334155', display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                      <span>ISBN: <strong>{lock.isbn}</strong></span>
                      <span className="badge-tag badge-gold">TTL: {lock.ttl_segundos}s</span>
                    </div>
                  ))
                ) : (
                  <span style={{ color: '#94a3b8', fontSize: 13 }}>Nenhum recurso bloqueado no momento</span>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Seção 3: Inspeção de Chaves Armazenadas no Redis */}
        <section className="admin-section-card">
          <div className="section-title">
            <div>
              <h2><Key size={20} color="#fca311" /> Chaves Armazenadas no Redis ({dados?.chaves?.total || 0})</h2>
              <p>Inspeção granular de chaves de cache, resultados, locks e filas</p>
            </div>
          </div>

          {/* Filtros por Categoria */}
          <div className="keys-filter-bar">
            {categorias.map((cat) => (
              <button
                key={cat}
                className={`filter-chip ${filtroCategoria === cat ? 'active' : ''}`}
                onClick={() => setFiltroCategoria(cat)}
              >
                {cat} {cat !== 'Todas' && dados?.chaves?.por_categoria?.[cat] ? `(${dados.chaves.por_categoria[cat]})` : ''}
              </button>
            ))}
          </div>

          <div style={{ overflowX: 'auto', maxHeight: 420, overflowY: 'auto' }}>
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Chave</th>
                  <th>Categoria</th>
                  <th>Tipo</th>
                  <th>TTL</th>
                  <th>Prévia do Conteúdo</th>
                  <th style={{ textAlign: 'center' }}>Ação</th>
                </tr>
              </thead>
              <tbody>
                {chavesFiltradas.length > 0 ? (
                  chavesFiltradas.map((c) => (
                    <tr key={c.chave}>
                      <td><code style={{ color: '#14213d', fontWeight: 600 }}>{c.chave}</code></td>
                      <td><span className="badge-tag badge-blue">{c.categoria}</span></td>
                      <td><span className="badge-tag badge-gray">{c.tipo}</span></td>
                      <td>
                        <span className="badge-tag badge-gold">
                          {typeof c.ttl === 'number' ? `${c.ttl}s` : c.ttl}
                        </span>
                      </td>
                      <td style={{ color: '#64748b', fontSize: 12 }}>{c.preview}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          onClick={() => handleExcluirChave(c.chave)}
                          title="Excluir chave"
                          style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 4 }}
                          onMouseEnter={(e) => (e.currentTarget.style.color = '#ef4444')}
                          onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: '#94a3b8', padding: 24 }}>
                      Nenhuma chave encontrada para esta categoria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Seção 4: Placeholder Banco de Dados (RDS) para o futuro */}
        <section className="placeholder-db-card">
          <Database size={28} color="#94a3b8" style={{ marginBottom: 8 }} />
          <h3>Monitoramento de Banco de Dados (RDS PostgreSQL)</h3>
          <p>Métricas de replicação (Master + Read Replica) e volumetria de tabelas serão integradas aqui nesta mesma tela.</p>
        </section>
      </main>
    </div>
  );
}
