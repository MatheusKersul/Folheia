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

├── backend/                # Aplicação do backend via FastAPI e configuração do banco de dados PostgreSQL  
│   ├── main.py             # Inicialização do servidor (FastAPI)
│   ├── database.py         # Configuração de conexão com o PostgreSQL (AWS RDS)  
│   ├── models.py           # Modelos do banco de dados (SQLAlchemy)  
│   ├── schemas.py          # Validação dos dados (Pydantic)  
│   ├── init_db.py          # Script isolado para criar as tabelas no banco  
│   └── requirements.txt    # Dependências do Python (FastAPI, Uvicorn, etc.)  
│  
├── frontend/               # Desenvolvimento da interface de usuário para realizar requisições do servidor
│   ├── index.html          # Estrutura visual  
│   ├── style.css           # Design  
│   └── script.js           # Lógica de comunicação com o backend  
│  
├── .env                      
├── .gitignore              
└── README.md               