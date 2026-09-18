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

db.sql(f"""
    INSTALL postgres;
    LOAD postgres;
    ATTACH 'dbname={DB_NAME} user={DB_USER} host={DB_HOST} password={DB_PASSWORD} port={DB_PORT}' AS aws_pg (TYPE POSTGRES);

    CALL postgres_execute('aws_pg', 'DROP TABLE IF EXISTS editions;');
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
    ');
        INSERT INTO aws_pg.editions (isbn_13, titulo, data_publicacao, formato, num_paginas, editora, autor) 
        SELECT isbn_13, titulo, data_publicacao, formato, num_paginas, editora, autor 
        FROM livros_com_autores;
""")
print("bd criado com sucesso")