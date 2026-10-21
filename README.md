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

## Replicação de dados no Amazon RDS (Master + Read Replica)

Experimento de Sistemas Distribuídos que demonstra, na prática, a replicação nativa do Amazon RDS para PostgreSQL: uma instância **primária** recebe as escritas e uma **read replica** é consultada até convergir, comprovando a *eventual consistency* e medindo o lag em milissegundos.

Toda a infraestrutura é provisionada por **Python + Boto3**, de forma idempotente, sem cliques no console da AWS.

### Arquitetura

```
                    ┌───────────────────────────┐
  INSERT/DELETE ───►│ Master (RDS PostgreSQL)   │
  (script)          └─────────────┬─────────────┘
                                  │ replicação nativa (assíncrona)
                                  ▼
                    ┌───────────────────────────┐
  SELECT (polling) ◄┤ Read Replica              │
                    └───────────────────────────┘
```

- Engine obrigatória: **PostgreSQL**.
- Banco: `money` · tabela: `users` (mesmo schema da aplicação).
- TLS com `sslmode=verify-full` + CA bundle oficial da AWS.
- Credenciais: `.env` local (gitignored) e/ou **AWS Secrets Manager**; nada hardcoded.

### Estrutura

```
infra/
  provision.py            # provisiona rede, primária e read replica (idempotente)
  destroy.py              # remove tudo o que foi criado (controle de custos)
  requirements.txt
  .env.example            # modelo de configuração
  state.json              # gerado em runtime (gitignored, sem senhas)
  certs/global-bundle.pem # CA da AWS (baixado automaticamente)
  aws/
    config.py             # env/região/profile, tags, sessão Boto3
    state.py              # estado local (adoção e limpeza seguras)
    net.py                # VPC, sub-redes, IGW, rotas e Security Group
    rds.py                # adoção, ajustes, criação e exclusão de instâncias
    secrets.py            # Secrets Manager e resolução de credenciais
    db.py                 # conexões PostgreSQL, banco e tabela users
    certs.py              # download do CA bundle
scripts/
  replication_test.py     # INSERT no Master -> polling na Réplica -> lag
```

### Pré-requisitos

1. Python 3.12+
2. Credenciais AWS com permissão para EC2 (VPC/Security Group), RDS e Secrets Manager:

```powershell
aws configure          # access key, secret, região us-east-1
aws sts get-caller-identity
```

3. Dependências:

```powershell
python -m venv infra/.venv
infra\.venv\Scripts\python -m pip install -r infra/requirements.txt
```

Se você não quiser instalar a AWS CLI, o Boto3 também aceita credenciais em `%USERPROFILE%\.aws\credentials`:

```ini
[default]
aws_access_key_id = SUA_ACCESS_KEY
aws_secret_access_key = SEU_SECRET
```

e `%USERPROFILE%\.aws\config`:

```ini
[default]
region = us-east-1
```

Também é possível usar as variáveis `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_REGION`.

4. Configuração: copie `infra/.env.example` para `infra/.env` e ajuste `AWS_PROFILE`, `ALLOWED_CIDR` etc. O `.env` já está no `.gitignore`.

### Provisionamento

O modo **`--create-new`** cumpre o critério do PRD (o código cria Master **e** Réplica sem intervenção manual no console):

```powershell
infra\.venv\Scripts\python infra\provision.py --create-new --dry-run
infra\.venv\Scripts\python infra\provision.py --create-new
```

O modo **`--adopt-existing`** reaproveita uma primária já existente (usado neste projeto, pois o banco já estava na AWS):

```powershell
infra\.venv\Scripts\python infra\provision.py --adopt-existing acervo-1 --dry-run
infra\.venv\Scripts\python infra\provision.py --adopt-existing acervo-1
```

Antes de provisionar, é possível conferir a qual instância o segredo pertence (sem exibir a senha):

```powershell
infra\.venv\Scripts\python infra\provision.py --inspect-secret
```

O que o `provision.py` faz, em ordem:

1. valida a identidade AWS e a conta do segredo;
2. adota ou cria a VPC/sub-redes públicas/Security Group (porta 5432);
3. garante `PubliclyAccessible=true` e backup automático ≥ 1 dia (obrigatório para réplica);
4. cria o banco `money` e a tabela `users` (idempotente);
5. cria a **read replica** na mesma AZ da primária e espera ficar `available`;
6. grava endpoints em `infra/state.json` + `infra/generated.env` (sem senha).

Para executar duas vezes sem efeitos colaterais, basta repetir o comando: cada etapa consulta a AWS antes de criar.

### Teste de replicação (comprovação)

```powershell
infra\.venv\Scripts\python scripts\replication_test.py --rows 1000 --cleanup
```

Saída esperada (valores de lag variam):

```
[MASTER  <endpoint-master>:5432 -> WRITE]
[REPLICA <endpoint-replica>:5432 -> READ]
[0/5] validando papéis das instâncias
  master  pg_is_in_recovery() = False (esperado: False)
  replica pg_is_in_recovery() = True (esperado: True)
[1/5] INSERT de 1000 registros no MASTER (prefixo replica-test-...)
[2/5] polling na RÉPLICA a cada 100 ms (timeout 60s)
  +   120.3 ms ->     0/1000 registros visíveis na réplica
  +   219.8 ms ->   998/1000 registros visíveis na réplica
  +   320.1 ms ->  1000/1000 registros visíveis na réplica
...
  lag total de replicação       : 320.1 ms
  réplica somente leitura       : SIM
```

O script garante o roteamento exigido:

- `INSERT`/`DELETE` usam **somente** a conexão do Master;
- `SELECT` usam **somente** a conexão da Réplica;
- a réplica rejeita escrita (`ReadOnlySqlTransaction`), provando o papel de read-only.

### Limpeza (evitar custos)

```powershell
infra\.venv\Scripts\python infra\destroy.py --dry-run
infra\.venv\Scripts\python infra\destroy.py --drop-database --delete-secret
```

- A instância primária **adotada** nunca é removida sem `--force-delete-primary`.
- `--drop-database` remove o banco `money`; `--delete-secret` remove o segredo criado pelo `--publish-secret`.
- Recursos de rede criados pelo `--create-new` são removidos na ordem reversa.

### Segurança

- Nenhuma senha no código ou no Git: `infra/.env` é gitignored e `state.json` guarda apenas endpoints/ARNs.
- Ordem de resolução da senha: `DB_PASSWORD` → Secrets Manager → prompt interativo (`getpass`).
- Conexões somente com TLS verificado (`verify-full` + `global-bundle.pem`).
- O Security Group é liberado para `ALLOWED_CIDR` (padrão `0.0.0.0/0` por ser trabalho acadêmico; em produção use o IP do cliente, `/32`).

### Critérios de aceite × evidência

| Critério | Como comprovar |
|---|---|
| Infra provisiona Master e Réplica sem console | `provision.py --create-new` |
| `INSERT` estritamente no Master | log `[MASTER ... -> WRITE]` |
| `SELECT` estritamente na Réplica | log `[REPLICA ... -> READ]` + `pg_is_in_recovery() = True` |
| README com setup e execução | esta seção |

### Solução de problemas

| Sintoma | Causa provável |
|---|---|
| `não foi possível autenticar na AWS` | access key/profile ausente → `aws configure` |
| `AccessDenied` no Secrets Manager | credencial de outra conta ou sem permissão |
| Host do segredo diferente da primária | o segredo pertence a outro stack/instância → confirme com `--inspect-secret` |
| `InvalidDBInstanceState` ao criar réplica | primária sem backup automático ou ainda criando |
| `connection timed out` | Security Group sem a regra 5432 para o seu IP |
