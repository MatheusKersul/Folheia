# Folheia
Sistema baseado em microsserviços na AWS para agregação de ofertas de livros em múltiplos e-commerces, monitoramento assíncrono de preços, gestão de biblioteca virtual e telemetria de infraestrutura.

---

## 📌 Histórico de Entregas

### Segunda Entrega: Conexão Cliente-Servidor e Deploy Inicial
* Desenvolvimento da primeira conexão entre cliente e servidor, tornando possível que o usuário pesquise obras registradas no banco de dados.
* Primeiro deploy na AWS, configurando portas para comunicação com a rede externa.
* Definição da stack inicial:
  * **Backend:** FastAPI + Uvicorn + SQLAlchemy + PostgreSQL (AWS RDS).
  * **Frontend:** Node.js + React.
* Carga inicial com acervo bibliográfico do OpenLibrary.

### Terceira Entrega: Coordenação Distribuída, Replicação e Alta Disponibilidade

Nesta etapa foram implementados os pilares de **Sistemas Distribuídos** no ecossistema de mensageria e cache (Redis) e no banco relacional (AWS RDS):

#### 1. Mecanismos de Coordenação Distribuída
* **Exclusão Mútua (Distributed Locks):**
  * Implementação em [`backend/services/queue_service.py`](backend/services/queue_service.py) utilizando o padrão atômico `SET lock:scrape:<isbn> <uuid> NX EX 120`.
  * Garante que múltiplos workers concorrentes não processem o mesmo ISBN simultaneamente, prevenindo sobrecarga em marketplaces externos e chamadas redundantes.
  * O TTL intrínseco previne *deadlocks* caso um worker sofra terminação abrupta.
* **Eleição de Líder e Consenso Distribuído (Redis Sentinel):**
  * Configuração de 3 instâncias de Sentinel ([`backend/sentinel/sentinel.conf`](backend/sentinel/sentinel.conf)) com quórum de maioria (2 de 3), eliminando riscos de *split-brain*.
  * Monitoramento constante do Master: transição automática de `SDOWN` (falha subjetiva) para `ODOWN` (falha objetiva) e promoção dinâmica de uma réplica a novo líder (`SLAVEOF NO ONE` e `+switch-master`) em caso de queda.
  * Inclusão de endpoint de Chaos Engineering (`POST /admin/chaos/derrubar-master`) para simular panes no Master e validar a eleição em tempo real.
* **Coordenação Produtor-Consumidor e Anti-Duplicação:**
  * Enfileiramento via `LPUSH`/`RPUSH` com suporte a prioridade e consumo bloqueante eficiente via `BRPOP`.
  * Conjunto temporário `fila:itens` gerenciado com `SADD`, `SISMEMBER` e `SREM` para evitar duplicidade de tarefas enquanto aguardam atendimento.

#### 2. Esquema de Nomeação de Recursos e Serviços
* **Namespaces Hierárquicos:**
  * `queue:scrape`: Lista da fila principal de tarefas de raspagem.
  * `fila:itens`: Set de deduplicação temporária na fila.
  * `lock:scrape:<isbn>`: Locks distribuídos de exclusão mútua por recurso.
  * `resultado:scrape:<isbn>`: Cache individual por livro com ofertas em JSON (TTL 24h).
  * `worker:heartbeat:<worker_id>`: Heartbeats efêmeros dos nós consumidores (TTL 25s).
  * `metrics:worker:<worker_id>`: Hashmap com snapshots de desempenho do worker.
  * `metrics:worker:historico`: Lista deslizante com as últimas 50 execuções.
  * `ryw:user:<usuario_id>`: Flag temporária de consistência Read-Your-Writes (TTL 5s).
  * `livro:<id_ou_isbn>`: Cache das informações catalogadas da obra.
* **Descoberta Dinâmica de Serviços (Service Discovery):**
  * A aplicação conecta ao cluster usando o nome lógico do serviço (`mymaster`) via `redis.sentinel.Sentinel`. A resolução do IP do Master é dinâmica, restabelecendo conexões automaticamente após failovers sem reiniciar containers.

#### 3. Replicação de Dados e Modelos de Consistência
* **Topologia de Replicação Redis:**
  * 1 nó Master com persistência AOF habilitada.
  * 2 Réplicas ativas recebendo replicação contínua via `replicaof`.
* **Modelo de Consistência Semi-Síncrona (*Tunable Consistency*) via `WAIT`:**
  * Para zerar o risco de perda de dados (*RPO ≈ 0*) em cotações concluídas, o método `salvar_resultado` utiliza o comando nativo `WAIT 2 1000`.
  * A finalização da tarefa só é confirmada após pelo menos duas réplicas confirmarem via ACK o processamento do stream de replicação até aquele offset.
* **Consistência "Read-Your-Writes" (RYW) no Banco Relacional:**
  * Implementação em [`backend/database/replica_fallback.py`](backend/database/replica_fallback.py).
  * Roteamento de leituras públicas de catálogo (`/buscar-livros`) para a Réplica de Leitura da AWS RDS (`DB_REPLICA_HOST`).
  * Para a biblioteca pessoal (`/biblioteca`), mutações gravam a flag `ryw:user:<id>` no Redis. Durante a janela de 5 segundos de *replication lag*, qualquer leitura do usuário é direcionada à Primária, garantindo consistência estrita para o autor da escrita.

#### 4. Painel Exclusivo de Administração e Telemetria
* **Backend:** Endpoints em [`backend/routers/admin.py`](backend/routers/admin.py) para diagnóstico de memória, réplicas ativas, contagem de workers online, inspeção categorizada de chaves e purga de filas.
* **Frontend:** Interface React em [`frontend/src/AdminDashboard.jsx`](frontend/src/AdminDashboard.jsx) (acessível via rota `#admin` ou botão no cabeçalho), exibindo o papel do cluster (`MASTER`/`SLAVE`), réplicas conectadas e gráficos de uso de memória.

---

## 🏗️ Estrutura Atual do Repositório

```text
Folheia/
├── backend/
│   ├── core/                        # Configurações globais, dependências e clientes
│   │   ├── config.py                # Leitura e parsing de variáveis de ambiente (.env)
│   │   ├── database.py              # Engines SQLAlchemy (Primária e Réplica RDS)
│   │   ├── deps.py                  # Injeção de dependências (JWT e autenticação)
│   │   ├── redis_client.py          # Cliente resiliente com suporte ao Sentinel
│   │   └── security.py              # Hashing de senhas (bcrypt) e geração de JWT
│   ├── database/                    # Scripts de migração, fallback e inicialização
│   │   ├── init_db.py               # Criação do schema inicial das tabelas
│   │   ├── migrate_library.py       # Migração idempotente da biblioteca
│   │   └── replica_fallback.py      # Roteamento dinâmico Read-Your-Writes (RYW)
│   ├── models/                      # Entidades relacionais do SQLAlchemy (ORM)
│   │   ├── book.py                  # Modelos de autores, obras e edições
│   │   └── user.py                  # Modelos de usuários e bibliotecas pessoais
│   ├── schemas/                     # Schemas de validação e serialização do Pydantic
│   │   ├── book.py                  # DTOs de livros e busca
│   │   ├── common.py                # DTOs compartilhados e paginação
│   │   ├── library.py               # DTOs de biblioteca e edições próprias
│   │   ├── scrap.py                 # DTOs de enfileiramento e cotações de preços
│   │   └── user.py                  # DTOs de cadastro e autenticação
│   ├── routers/                     # Controladores e endpoints da API FastAPI
│   │   ├── admin.py                 # Telemetria do Redis, inspeção de chaves e testes de caos
│   │   ├── auth.py                  # Cadastro, login e renovação de tokens
│   │   ├── books.py                 # Busca pública de catálogo na Réplica RDS
│   │   ├── library.py               # Gestão de biblioteca pessoal com consistência RYW
│   │   ├── scrap.py                 # Enfileiramento, testes em lote e status de cotações
│   │   └── system.py                # Endpoints de healthcheck do sistema
│   ├── services/                    # Regras de negócio e serviços de coordenação
│   │   ├── auth_service.py          # Lógica de validação de credenciais e tokens
│   │   ├── book_service.py          # Consultas otimizadas com cache
│   │   ├── library_service.py       # CRUD seguro com tratamento contextual de erros
│   │   ├── queue_service.py         # Locks, filas, deduplicação e WAIT semi-síncrono
│   │   ├── scraper_client.py        # Chamadas para microsserviços de scraping
│   │   └── service_discovery.py     # Resolução dinâmica via AWS Cloud Map
│   ├── scrappers/                   # Módulos de extração de dados em marketplaces
│   │   ├── scraper_amazon.py        # Scraper Bright Data / Amazon Brasil
│   │   └── scraper_mercadolivre.py  # Scraper Mercado Livre
│   ├── sentinel/                    # Infraestrutura do Redis Sentinel
│   │   └── sentinel.conf            # Regras de monitoramento, timeouts e quórum
│   ├── tests/                       # Suíte de testes unitários e de integração
│   │   ├── test_api.py              # Testes dos endpoints do sistema
│   │   └── test_library.py          # Testes de autenticação e privacidade da biblioteca
│   ├── server.py                    # Inicialização e inclusão dos routers do FastAPI
│   ├── worker.py                    # Worker consumidor de tarefas com graceful shutdown
│   ├── docker-compose.yaml          # Orquestração (API, Workers, Cluster Redis e Sentinels)
│   ├── Dockerfile                   # Imagem da API
│   └── Dockerfile.worker            # Imagem dos Workers de scraping
│
├── frontend/                        # Interface de usuário (React 19 + Vite)
│   ├── public/                      # Assets estáticos públicos (favicon.svg, icons.svg)
│   ├── src/
│   │   ├── assets/                  # Imagens e vetores (hero.png, react.svg, vite.svg)
│   │   ├── auth/                    # Gerenciamento de estado de autenticação
│   │   │   ├── AuthProvider.jsx     # Context Provider de sessão e token JWT
│   │   │   ├── context.js           # Criação do React Context de autenticação
│   │   │   └── useAuth.js           # Hook customizado de acesso ao contexto
│   │   ├── components/              # Componentes visuais reutilizáveis
│   │   │   ├── Header.jsx           # Barra de navegação superior e links
│   │   │   ├── Layout.jsx           # Estrutura base padrão de layout
│   │   │   └── ProtectedRoute.jsx   # Guarda de rota para páginas autenticadas
│   │   ├── pages/                   # Views e telas principais da aplicação
│   │   │   ├── Home.jsx             # Busca e listagem do catálogo de livros
│   │   │   ├── Biblioteca.jsx       # Gestão da biblioteca pessoal do usuário
│   │   │   ├── Login.jsx            # Autenticação de usuários existentes
│   │   │   └── Cadastro.jsx         # Registro de novos usuários
│   │   ├── AdminDashboard.jsx       # Painel de controle e telemetria do Redis / Workers
│   │   ├── AdminDashboard.css       # Estilização exclusiva do painel administrativo
│   │   ├── App.jsx                  # Roteador principal e orquestração de telas
│   │   ├── App.css                  # Estilos globais e tema (Azul #14213d e Dourado #fca311)
│   │   ├── HeaderDecoration.jsx     # Elementos visuais decorativos do cabeçalho
│   │   ├── api.js                   # Instância de comunicação HTTP com interceptors de token
│   │   ├── index.css                # Reset e estilos base de tipografia
│   │   └── main.jsx                 # Ponto de montagem da aplicação React
│   ├── Dockerfile                   # Configuração de build e containerização do frontend
│   ├── index.html                   # Entrada HTML raiz
│   ├── package.json                 # Dependências e scripts do projeto (Vite, React 19)
│   └── vite.config.js               # Configurações do bundler Vite
│
├── acervo_data/                     # Dumps bibliográficos e documentações técnicas
│   └── docs/                        # Relatórios de arquitetura e coordenação
│
├── .env                             # Variáveis de ambiente e credenciais locais
└── README.md                        # Documentação do projeto
```

---

## 📚 Biblioteca Pessoal e Edições Próprias

Cada usuário autenticado possui **uma** biblioteca pessoal (`library`), criada automaticamente no primeiro acesso com o nome "Minha Biblioteca". Os itens são os vínculos (`link_library`) entre essa biblioteca e as edições (`editions`).

### Endpoints da Biblioteca

Todas as rotas exigem `Authorization: Bearer <token>` (token devolvido por `POST /auth/login`). Sem token válido a resposta é sempre `401`.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/biblioteca?page=1&limit=20&q=` | Lista a biblioteca pessoal (paginada, busca por título/autor/editora) |
| `GET` | `/biblioteca/itens/{item_id}` | Detalha um item da biblioteca |
| `POST` | `/biblioteca/livros` | Adiciona obra do catálogo — body `{"edition_id": 1}` **ou** `{"isbn": "978..."}` |
| `POST` | `/biblioteca/edicoes-proprias` | Cria edição própria (não verificada) e a adiciona à biblioteca |
| `GET` | `/biblioteca/edicoes-proprias` | Lista as edições próprias do usuário |
| `DELETE` | `/biblioteca/itens/{item_id}` | Remove o item da biblioteca |

### Edições Verificadas × Próprias

A coluna `editions.verificada` distingue:

| `verificada` | Significado | Visibilidade |
|---|---|---|
| `TRUE` | Obra do catálogo oficial (OpenLibrary) | Todos os usuários |
| `FALSE` | Edição própria, informação **não oficial e não verificada** | Apenas o usuário que a criou (`id_usuario_criador`) |

Consequências práticas:
* `POST /biblioteca/edicoes-proprias` grava `verificada=false` e `id_usuario_criador` = usuário autenticado, vinculando a edição à biblioteca na mesma transação.
* `isbn_13` aceita `NULL`; a unicidade é garantida por um índice único parcial válido apenas para edições oficiais (`uq_editions_isbn_oficial`).
* `/buscar-livros` filtra `verificada = TRUE`, garantindo que edições privadas nunca apareçam na busca pública nem no cache compartilhado do Redis.

---

## 🚀 Como Executar o Projeto com Docker Compose

### 1. Inicializar toda a infraestrutura
Para subir a API, os 3 Workers concorrentes, o Frontend e o Cluster de Alta Disponibilidade do Redis (1 Master + 2 Réplicas + 3 Sentinels):

```bash
docker compose -f backend/docker-compose.yaml up -d --build
```

### 2. Acessar os Serviços
* **Aplicação Web / Catálogo:** `http://localhost:3000`
* **Painel de Telemetria e Administração:** `http://localhost:3000/#admin`
* **Documentação Interativa da API (Swagger):** `http://localhost:8000/docs`

### 3. Teste em Lote de Fila e Deduplicação
Você pode enfileirar uma carga de livros reais para testar o consumo concorrente e a checagem de memória executando:
```http
GET http://localhost:8000/scp/fila/teste
```

### 4. Teste de Caos e Eleição Automática (Failover)
Para testar a eleição de líder derrubando o Master atual:
```http
POST http://localhost:8000/admin/chaos/derrubar-master
```
Acompanhe a eleição nos logs dos Sentinels:
```bash
docker compose -f backend/docker-compose.yaml logs -f sentinel-1
```
*(Em ~3 segundos, os Sentinels detectarão a queda por quórum e promoverão uma das réplicas automaticamente).*

---

## 🧪 Testes Unitários

Para executar a suíte de testes de integração e regras de negócio:

```powershell
cd backend
python -m unittest discover -s tests -v
```
