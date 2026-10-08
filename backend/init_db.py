import os
import duckdb as db
from dotenv import load_dotenv
import bcrypt

load_dotenv()

FILE_AUTHORS = os.getenv("FILE_AUTHORS")
FILE_EDITIONS = os.getenv("FILE_EDITIONS")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


def validate_environment():
    required = {
        "FILE_AUTHORS": FILE_AUTHORS,
        "FILE_EDITIONS": FILE_EDITIONS,
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_NAME": DB_NAME,
        "ADMIN_EMAIL": ADMIN_EMAIL,
        "ADMIN_PASSWORD": ADMIN_PASSWORD,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "Variáveis de ambiente ausentes: " + ", ".join(missing)
        )

def load_books():
    livros = db.read_csv(
        FILE_EDITIONS,
        max_line_size=10_000_000
    ).select("""
        regexp_replace(
            json_extract_string(column4, '$.isbn_13[0]'),
            '[^0-9]',
            '',
            'g'
        ) AS isbn_13,

        NULLIF(
            TRIM(json_extract_string(column4, '$.title')),
            ''
        ) AS titulo,

        NULLIF(
            TRIM(json_extract_string(column4, '$.publish_date')),
            ''
        ) AS data_publicacao,

        NULLIF(
            TRIM(json_extract_string(column4, '$.physical_format')),
            ''
        ) AS formato,

        TRY_CAST(
            json_extract_string(column4, '$.number_of_pages') AS INTEGER
        ) AS num_paginas,

        NULLIF(
            TRIM(json_extract_string(column4, '$.publishers[0]')),
            ''
        ) AS editora,

        json_extract_string(column4, '$.authors[0].key') AS autor_key
    """).filter("""
        isbn_13 IS NOT NULL
        AND isbn_13 <> ''
        AND (
            isbn_13 LIKE '97885%'
            OR isbn_13 LIKE '97865%'
            OR isbn_13 LIKE '97800%'
            OR isbn_13 LIKE '97801%'
        )
    """)
    return livros

def load_authors():
    autores = db.read_csv(
        FILE_AUTHORS,
        max_line_size=10_000_000
    ).select("""
        NULLIF(
            TRIM(json_extract_string(column4, '$.name')),
            ''
        ) AS autor,

        json_extract_string(column4, '$.key') AS autor_key
    """)
    return autores

def join_books_and_authors(livros, autores):
    livros_com_autores = db.sql("""
        SELECT
            livros.isbn_13,
            livros.titulo,
            livros.data_publicacao,
            livros.formato,
            livros.num_paginas,
            livros.editora,
            autores.autor
        FROM livros
        LEFT JOIN autores
            ON livros.autor_key = autores.autor_key
    """)
    return livros_com_autores

def deduplicate_books(livros_com_autores):
    livros_final = db.sql("""
        WITH base AS (
            SELECT
                regexp_replace(isbn_13, '[^0-9]', '', 'g') AS isbn_13,
                NULLIF(TRIM(titulo), '') AS titulo,
                NULLIF(TRIM(autor), '') AS autor,
                NULLIF(TRIM(editora), '') AS editora,
                NULLIF(TRIM(data_publicacao), '') AS data_publicacao,
                NULLIF(TRIM(formato), '') AS formato,
                num_paginas
            FROM livros_com_autores
            WHERE isbn_13 IS NOT NULL
              AND TRIM(isbn_13) <> ''
        ),
        consolidado AS (
            SELECT
                isbn_13,
                ANY_VALUE(titulo) FILTER (WHERE titulo IS NOT NULL) AS titulo,
                ANY_VALUE(autor) FILTER (WHERE autor IS NOT NULL) AS autor,
                ANY_VALUE(editora) FILTER (WHERE editora IS NOT NULL) AS editora,
                ANY_VALUE(data_publicacao) FILTER (WHERE data_publicacao IS NOT NULL) AS data_publicacao,
                ANY_VALUE(formato) FILTER (WHERE formato IS NOT NULL) AS formato,
                ANY_VALUE(num_paginas) FILTER (WHERE num_paginas IS NOT NULL) AS num_paginas,
                COUNT(*) AS ocorrencias
            FROM base
            GROUP BY isbn_13
        )
        SELECT
            isbn_13,
            titulo,
            autor,
            data_publicacao,
            formato,
            num_paginas,
            editora,
            ocorrencias
        FROM consolidado
        ORDER BY isbn_13
    """)
    return livros_final

def connect_postgres():
    db.sql("INSTALL postgres")
    db.sql("LOAD postgres")

    connection_string = (
        f"dbname={DB_NAME} "
        f"user={DB_USER} "
        f"host={DB_HOST} "
        f"password={DB_PASSWORD} "
        f"port={DB_PORT}"
    )

    db.sql(f"""
        ATTACH '{connection_string}'
        AS aws_pg (TYPE POSTGRES)
    """)

def create_postgres_schema():
    db.sql("""
        CALL postgres_execute(
            'aws_pg',
            $$
            CREATE TABLE IF NOT EXISTS editions (
                id SERIAL PRIMARY KEY,
                isbn_13 VARCHAR(13) NOT NULL UNIQUE,
                titulo TEXT,
                data_publicacao VARCHAR(255),
                formato VARCHAR(255),
                num_paginas INTEGER,
                editora TEXT,
                autor TEXT
            );

            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                senha VARCHAR(255) NOT NULL,
                permissoes VARCHAR(20) NOT NULL DEFAULT 'usuario',
                CONSTRAINT users_permissoes_check
                    CHECK (permissoes IN ('usuario', 'funcionario', 'admin'))
            );

            CREATE UNIQUE INDEX IF NOT EXISTS unique_admin
                ON users (permissoes)
                WHERE permissoes = 'admin';

            CREATE TABLE IF NOT EXISTS library (
                id SERIAL PRIMARY KEY,
                id_usuario INTEGER NOT NULL,
                nome VARCHAR(255) NOT NULL,
                CONSTRAINT fk_library_usuario
                    FOREIGN KEY (id_usuario)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS link_library (
                id SERIAL PRIMARY KEY,
                id_biblioteca INTEGER NOT NULL,
                id_livro INTEGER NOT NULL,
                CONSTRAINT fk_link_library_biblioteca
                    FOREIGN KEY (id_biblioteca)
                    REFERENCES library(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_link_library_livro
                    FOREIGN KEY (id_livro)
                    REFERENCES editions(id)
                    ON DELETE CASCADE,
                CONSTRAINT unique_livro_biblioteca
                    UNIQUE (id_biblioteca, id_livro)
            );
            $$
        )
    """)

def create_admin():
    password_hash = bcrypt.hashpw(
        ADMIN_PASSWORD.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    admin_email = ADMIN_EMAIL.replace("'", "''")

    db.sql(f"""
        INSERT INTO aws_pg.users (
            nome,
            email,
            senha,
            permissoes
        )
        SELECT
            'admin',
            '{admin_email}',
            '{password_hash}',
            'admin'
        WHERE NOT EXISTS (
            SELECT 1
            FROM aws_pg.users
            WHERE permissoes = 'admin'
        )
    """)

def insert_books(livros):
    db.register("livros_temp", livros)
    # 1. Atualiza os livros que já existem no PostgreSQL
    db.sql("""
        UPDATE aws_pg.editions
        SET
            titulo = COALESCE(livros_temp.titulo, aws_pg.editions.titulo),
            data_publicacao = COALESCE(livros_temp.data_publicacao, aws_pg.editions.data_publicacao),
            formato = COALESCE(livros_temp.formato, aws_pg.editions.formato),
            num_paginas = COALESCE(livros_temp.num_paginas, aws_pg.editions.num_paginas),
            editora = COALESCE(livros_temp.editora, aws_pg.editions.editora),
            autor = COALESCE(livros_temp.autor, aws_pg.editions.autor)
        FROM livros_temp
        WHERE aws_pg.editions.isbn_13 = livros_temp.isbn_13
    """)

    # 2. Insere apenas os registros novos
    db.sql("""
        INSERT INTO aws_pg.editions (
            isbn_13,
            titulo,
            data_publicacao,
            formato,
            num_paginas,
            editora,
            autor
        )
        SELECT
            livros_temp.isbn_13,
            livros_temp.titulo,
            livros_temp.data_publicacao,
            livros_temp.formato,
            livros_temp.num_paginas,
            livros_temp.editora,
            livros_temp.autor
        FROM livros_temp
        WHERE NOT EXISTS (
            SELECT 1 
            FROM aws_pg.editions e 
            WHERE e.isbn_13 = livros_temp.isbn_13
        )
    """)

def main():
    print("Iniciando ETL...")

    validate_environment()
    print("Variáveis de ambiente OK.")

    print("Lendo arquivo de edições...")
    livros = load_books()

    print("Lendo arquivo de autores...")
    autores = load_authors()
    print("Arquivos carregados com sucesso.")

    print("Relacionando livros e autores...")
    livros_com_autores = join_books_and_authors(livros, autores)

    print("Removendo duplicidades...")
    livros_final = deduplicate_books(livros_com_autores)
    print("Dados tratados com sucesso.")

    print("Conectando ao PostgreSQL...")
    connect_postgres()
    print("PostgreSQL conectado.")

    print("Criando/verificando tabelas...")
    create_postgres_schema()
    print("Schema criado/verificado.")

    print("Verificando usuário administrador...")
    create_admin()
    print("Administrador verificado.")

    print("Inserindo/atualizando livros...")
    insert_books(livros_final)
    print("Livros inseridos/atualizados com sucesso.")

    print()
    print("========================================")
    print("ETL concluído com sucesso!")
    print("========================================")


if __name__ == "__main__":
    main()