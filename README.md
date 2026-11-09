# Folheia
Sistema baseado em microsserviços na AWS para agregação de ofertas de livros em múltiplos e-commerces, monitoramento assíncrono de preços e gestão de biblioteca virtual com identificação multimodal (texto e OCR).

Segunda entrega:
                    -> Desenvolvimento da primeira conexão entre cliente e servidor, tornando possível que o usuário consiga pesquisar obras registradas no banco de dados.
                    -> Primeiro deploy na plataforma AWS, configurando as portas para o servidor conseguir se comunicar com a rede externa
                    -> Definição dos frameworks que irão ser utilizados (inicialmente):
                        - Backend: FastAPI + Uvicorn
                        - Frontend: Node.js + React

Inicialmente o servidor será carregado com um acervo de obras disponibilizado pelo site OpenLibrary (https://openlibrary.org/). A primeira funcionalidade do sistema será uma
consulta no banco de dados integrado na aws para que o cliente (frontend) consiga se comunicar com o servidor (backend)

**Estruturação inicial do trabalho**

Folheia/

├── backend/                 Aplicação do backend via FastAPI e configuração do banco de dados PostgreSQL  
│   ├── main.py              Inicialização do servidor (FastAPI)
│   ├── database.py          Configuração de conexão com o PostgreSQL (AWS RDS)  
│   ├── models.py            Modelos do banco de dados (SQLAlchemy)  
│   ├── schemas.py           Validação dos dados (Pydantic)  
│   ├── init_db.py           Script isolado para criar as tabelas no banco  
│   └── requirements.txt     Dependências do Python (FastAPI, Uvicorn, etc.)  
│  
├── frontend/                Desenvolvimento da interface de usuário para realizar requisições do servidor
│   ├── index.html           Estrutura visual  
│   ├── style.css            Design  
│   └── script.js            Lógica de comunicação com o backend  
│  
├── .env                      
├── .gitignore              
└── README.md               

---

## Biblioteca pessoal e edições próprias

Cada usuário autenticado possui **uma** biblioteca pessoal (`library`), criada
automaticamente no primeiro acesso com o nome "Minha Biblioteca". Os itens são
os vínculos (`link_library`) entre essa biblioteca e as edições (`editions`).

### Endpoints

Todas as rotas exigem `Authorization: Bearer <token>` (token devolvido por
`POST /auth/login`). Sem token válido a resposta é sempre `401`.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/biblioteca?page=1&limit=20&q=` | Lista a biblioteca pessoal (paginada, busca por título/autor/editora) |
| `GET` | `/biblioteca/itens/{item_id}` | Detalha um item da biblioteca |
| `POST` | `/biblioteca/livros` | Adiciona obra do catálogo — body `{"edition_id": 1}` **ou** `{"isbn": "978..."}` |
| `POST` | `/biblioteca/edicoes-proprias` | Cria edição própria (não verificada) e a adiciona à biblioteca |
| `GET` | `/biblioteca/edicoes-proprias` | Lista as edições próprias do usuário |
| `DELETE` | `/biblioteca/itens/{item_id}` | Remove o item da biblioteca |

### Exemplo

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
    -ContentType "application/json" `
    -Body '{"email":"ana@exemplo.com","senha":"senhaSegura123"}'
$h = @{ Authorization = "Bearer $($login.usuario.token)" }

# Adicionar obra do catálogo por ISBN
Invoke-RestMethod -Method Post -Uri http://localhost:8000/biblioteca/livros `
    -Headers $h -ContentType "application/json" `
    -Body '{"isbn":"9788535902778"}'

# Criar edição própria (ISBN é opcional)
Invoke-RestMethod -Method Post -Uri http://localhost:8000/biblioteca/edicoes-proprias `
    -Headers $h -ContentType "application/json" `
    -Body '{"titulo":"Minha edição artesanal","autor":"Autor Desconhecido"}'

# Listar
Invoke-RestMethod -Method Get -Uri http://localhost:8000/biblioteca -Headers $h
```

### Edições verificadas × próprias

A coluna `editions.verificada` distingue:

| `verificada` | Significado | Visibilidade |
|---|---|---|
| `TRUE` | Obra do catálogo oficial (OpenLibrary) | Todos os usuários |
| `FALSE` | Edição própria, informação **não oficial e não verificada** | Apenas o usuário que a criou (`id_usuario_criador`) |

Consequências práticas:

- `POST /biblioteca/edicoes-proprias` grava `verificada=false` e
  `id_usuario_criador` = usuário autenticado, e vincula a edição à biblioteca
  na mesma transação.
- `isbn_13` aceita `NULL`; a unicidade é garantida por um **índice único
  parcial** válido apenas para edições oficiais
  (`uq_editions_isbn_oficial`).
- Se o ISBN informado já existir no catálogo oficial, a API responde `409`
  orientando o uso de `POST /biblioteca/livros` (evita duplicar obra oficial).
- `/buscar-livros` filtra `verificada = TRUE`, portanto edições privadas
  **nunca** aparecem na busca pública nem no cache Redis (que é compartilhado).

### Garantias de privacidade

- O identificador do usuário vem **exclusivamente** do token JWT assinado
  (`core/deps.py`); nenhuma rota aceita `user_id`/`id_usuario` do cliente.
- Toda consulta da biblioteca é filtrada por `library.id_usuario = <token>`.
- Item ou edição de outro usuário responde `404` (e não `403`), para não
  revelar a existência do recurso.
- A dependência `get_current_user_optional` existe para rotas públicas que
  eventualmente queiram enriquecer a resposta, mas não é usada na biblioteca.
- Erros de token (ausente, inválido, expirado) usam mensagem genérica única.

### Migração do banco existente

O schema de um banco já provisionado precisa da migração idempotente:

```powershell
cd backend
python database/migrate_library.py --dry-run   # confere o SQL
python database/migrate_library.py             # aplica
```

A migração adiciona `verificada`, `id_usuario_criador`, `link_library.criado_em`,
relaxa `editions.isbn_13` para `NULL`, troca o `UNIQUE` global pelo índice
parcial e garante `UNIQUE (library.id_usuario)`.

Para instalações novas, `database/init_db.py` já cria o schema atualizado.

### Testes

```powershell
cd backend
python -m unittest discover -s tests -v
```

`tests/test_library.py` cobre autenticação, inclusão por ISBN/`edition_id`,
edição própria, duplicidade, remoção e os cenários de privacidade entre dois
usuários (listagem, item individual e busca pública).
