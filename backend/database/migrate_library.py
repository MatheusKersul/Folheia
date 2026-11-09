"""
Migração idempotente do schema para a biblioteca pessoal e edições próprias.

Aplica, em uma única transação, as alterações necessárias no PostgreSQL (RDS):

1. ``editions.verificada`` (BOOLEAN, default TRUE) — FALSE marca edição própria;
2. ``editions.id_usuario_criador`` — dono da edição própria;
3. ``editions.isbn_13`` passa a aceitar NULL;
4. remove o UNIQUE global de ``isbn_13`` e cria índice único PARCIAL que só
   vale para edições oficiais;
5. consolida bibliotecas duplicadas e garante ``UNIQUE (library.id_usuario)``;
6. adiciona ``link_library.criado_em``.

Uso:
    python database/migrate_library.py            # aplica
    python database/migrate_library.py --dry-run  # apenas exibe o SQL

Execute a partir do diretório ``backend`` (ou ajuste o ``sys.path`` abaixo).
"""
import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from core.database import engine  # noqa: E402

# Ordem importa: colunas antes dos índices/constraints.
COMANDOS = [
    # ---------------------------------------------------------------- editions
    """
    ALTER TABLE editions
        ADD COLUMN IF NOT EXISTS verificada BOOLEAN NOT NULL DEFAULT TRUE
    """,
    """
    ALTER TABLE editions
        ADD COLUMN IF NOT EXISTS id_usuario_criador INTEGER
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'fk_editions_criador'
              AND conrelid = 'editions'::regclass
        ) THEN
            ALTER TABLE editions
                ADD CONSTRAINT fk_editions_criador
                FOREIGN KEY (id_usuario_criador)
                REFERENCES users(id)
                ON DELETE CASCADE;
        END IF;
    END $$;
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'ck_editions_privada_tem_dono'
              AND conrelid = 'editions'::regclass
        ) THEN
            ALTER TABLE editions
                ADD CONSTRAINT ck_editions_privada_tem_dono
                CHECK (verificada OR id_usuario_criador IS NOT NULL);
        END IF;
    END $$;
    """,
    "ALTER TABLE editions ALTER COLUMN isbn_13 DROP NOT NULL",
    # Remove qualquer UNIQUE global que incida apenas sobre isbn_13.
    """
    DO $$
    DECLARE
        c record;
        attnum smallint;
    BEGIN
        SELECT a.attnum INTO attnum
        FROM pg_attribute a
        WHERE a.attrelid = 'editions'::regclass
          AND a.attname = 'isbn_13';

        FOR c IN
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'editions'::regclass
              AND contype = 'u'
              AND conkey = ARRAY[attnum]
        LOOP
            EXECUTE format('ALTER TABLE editions DROP CONSTRAINT %I', c.conname);
        END LOOP;
    END $$;
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_editions_isbn_oficial
        ON editions (isbn_13)
        WHERE isbn_13 IS NOT NULL AND verificada
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_editions_criador
        ON editions (id_usuario_criador)
    """,
    # ----------------------------------------------------------------- library
    # Consolida eventuais duplicatas antes de aplicar o UNIQUE.
    """
    DELETE FROM library l
    USING library l2
    WHERE l.id_usuario = l2.id_usuario
      AND l.id > l2.id
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_library_usuario'
              AND conrelid = 'library'::regclass
        ) THEN
            ALTER TABLE library
                ADD CONSTRAINT uq_library_usuario UNIQUE (id_usuario);
        END IF;
    END $$;
    """,
    # ------------------------------------------------------------ link_library
    """
    ALTER TABLE link_library
        ADD COLUMN IF NOT EXISTS criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
    """,
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra o schema para biblioteca pessoal e edições próprias."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas exibe os comandos, sem executar.",
    )
    args = parser.parse_args()

    dialeto = engine.dialect.name
    if dialeto != "postgresql":
        print(
            f"[ERRO] Este script é específico para PostgreSQL (dialeto atual: {dialeto})."
        )
        return 1

    if args.dry_run:
        for indice, comando in enumerate(COMANDOS, start=1):
            print(f"--- [{indice}/{len(COMANDOS)}] ---")
            print(comando.strip())
        print("\n[dry-run] Nenhuma alteração foi aplicada.")
        return 0

    print(f"[1/{len(COMANDOS)}] Aplicando migração em transação única...")
    with engine.begin() as conexao:
        for indice, comando in enumerate(COMANDOS, start=1):
            print(f"  [{indice}/{len(COMANDOS)}] executando...")
            conexao.execute(text(comando))

    print("Migração concluída com sucesso.")
    print(
        "Verifique: editions.verificada, editions.id_usuario_criador, "
        "uq_editions_isbn_oficial, uq_library_usuario, link_library.criado_em."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
