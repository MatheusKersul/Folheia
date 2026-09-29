import duckdb as db
import os
from dotenv import load_dotenv

load_dotenv()

FILE_AUTHORS = os.getenv("FILE_AUTHORS")
FILE_EDITIONS = os.getenv("FILE_EDITIONS")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

livros = (
    db.read_csv(f'{FILE_EDITIONS}', max_line_size=10000000)
    .select("""
        -- Extrai o primeiro ISBN da lista
        json_extract_string(column4, '$.isbn_13[0]') AS isbn_13,
        
        -- Textos simples
        json_extract_string(column4, '$.title') AS titulo,
        json_extract_string(column4, '$.publish_date') AS data_publicacao,
        json_extract_string(column4, '$.physical_format') AS formato,
        
        -- Converte o número de páginas para um tipo numérico inteiro
        CAST(json_extract_string(column4, '$.number_of_pages') AS INTEGER) AS num_paginas,
        
        -- Extrai a primeira editora da lista
        json_extract_string(column4, '$.publishers[0]') AS editora,
        
        -- Extrai a chave de identificação do primeiro autor do array de objetos
        json_extract_string(column4, '$.authors[0].key') AS autor_key
    """)
    .filter("replace(isbn_13, '-', '') LIKE '97885%' OR replace(isbn_13, '-', '') LIKE '97865%' OR replace(isbn_13, '-', '') LIKE '97800%' OR replace(isbn_13, '-', '') LIKE '97801%'")
)

autores = (
    db.read_csv(f'{FILE_AUTHORS}', max_line_size=10000000)
    .select("""

        -- Textos simples
        json_extract_string(column4, '$.name') AS autor,
        json_extract_string(column4, '$.key') AS autor_key,
        
    """)
)

livros_com_autores = db.sql("""
    SELECT 
        livros.isbn_13,
        livros.titulo,
        livros.data_publicacao,
        livros.formato,
        livros.num_paginas,
        livros.editora,
        autor.autor
    FROM livros
    LEFT JOIN autores AS autor 
        ON livros.autor_key = autor.autor_key
    
""")
print("duckdb criado com sucesso")

#comando para retirar itens duplicados do bd
# Comando para retirar itens duplicados lendo da relação em memória
livros_com_autores = db.sql("""
WITH base AS (
    SELECT
        regexp_replace(isbn_13, '[^0-9]', '', 'g') AS isbn_13,

        NULLIF(TRIM(titulo), '') AS titulo,
        NULLIF(TRIM(autor), '') AS autor_nome, -- Ajustado para a coluna 'autor' vinda do JOIN
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

        ANY_VALUE(titulo) FILTER (
            WHERE titulo IS NOT NULL
        ) AS titulo,

        ANY_VALUE(autor_nome) FILTER (
            WHERE autor_nome IS NOT NULL
        ) AS autor_nome,

        ANY_VALUE(editora) FILTER (
            WHERE editora IS NOT NULL
        ) AS editora,

        ANY_VALUE(data_publicacao) FILTER (
            WHERE data_publicacao IS NOT NULL
        ) AS data_publicacao,

        ANY_VALUE(formato) FILTER (
            WHERE formato IS NOT NULL
        ) AS formato,

        ANY_VALUE(num_paginas) FILTER (
            WHERE num_paginas IS NOT NULL
        ) AS num_paginas,

        COUNT(*) AS copias_encontradas

    FROM base

    GROUP BY isbn_13
)

SELECT *
FROM consolidado
ORDER BY isbn_13
""")

#criação da tabela de usuarios
db.sql("CREATE SEQUENCE seq_users_id")
db.sql("""

    CREATE TYPE permissoes_enum AS ENUM ('usuario', 'funcionario', 'admin');
    CREATE TABLE users (
        id INT DEFAULT nextval('seq_users_id') PRIMARY KEY,
        Nome VARCHAR(255),
        Email VARCHAR(255),
        Senha VARCHAR(255),
        Permissoes permissoes_enum DEFAULT 'usuario'
    )
""")

#criação da tabela de biblioteca

db.sql("""
    CREATE TABLE library (
        id INT DEFAULT nextval('seq_users_id') PRIMARY KEY,
        id_usuario INTEGER,
        id_bilioteca INTEGER,
        nome VARCHAR(255)
    )
""")

#criação da tabela link_biblioteca
db.sql("""
    CREATE TABLE link_library (
        id INT DEFAULT nextval('seq_users_id') PRIMARY KEY,
        id_bilioteca INTEGER,
        id_livro INTEGER
    )
""")


db.sql(f"""
    INSTALL postgres;
    LOAD postgres;
    ATTACH 'dbname={DB_NAME} user={DB_USER} host={DB_HOST} password={DB_PASSWORD} port={DB_PORT}' AS aws_pg (TYPE POSTGRES);

    CALL postgres_execute('aws_pg', '
        DROP TABLE IF EXISTS link_library;
        DROP TABLE IF EXISTS library;
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS editions;
        DROP TYPE IF EXISTS permissoes_enum;
    ');

    CALL postgres_execute('aws_pg', '
        CREATE TABLE IF NOT EXISTS editions (
            id SERIAL PRIMARY KEY,
            isbn_13 VARCHAR(255),
            titulo TEXT,
            data_publicacao VARCHAR(255),
            formato VARCHAR(255),
            num_paginas INTEGER,
            editora TEXT,
            autor TEXT
        );

        CREATE TYPE permissoes_enum AS ENUM (''usuario'', ''funcionario'', ''admin'');

        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            Nome VARCHAR(255),
            Email VARCHAR(255),
            Senha VARCHAR(255),
            Permissoes permissoes_enum DEFAULT ''usuario''
        );

        CREATE TABLE IF NOT EXISTS library (
            id SERIAL PRIMARY KEY,
            id_usuario INTEGER,
            id_bilioteca INTEGER,
            nome VARCHAR(255)
        );

        CREATE TABLE IF NOT EXISTS link_library (
            id SERIAL PRIMARY KEY,
            id_bilioteca INTEGER,
            id_livro INTEGER
        );
    ');

    INSERT INTO aws_pg.editions (isbn_13, titulo, data_publicacao, formato, num_paginas, editora, autor) 
    SELECT isbn_13, titulo, data_publicacao, formato, num_paginas, editora, autor_nome
    FROM livros_com_autores;
""")
print("bd criado com sucesso")