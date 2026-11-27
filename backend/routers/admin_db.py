import re
import time
import json
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.database import engine, get_db

router = APIRouter(prefix="/db", tags=["Administração - Banco de Dados"])

IDENTIFICADOR_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")

TIPOS_BASE_PERMITIDOS = {
    "SMALLINT",
    "INTEGER",
    "INT",
    "BIGINT",
    "SERIAL",
    "BIGSERIAL",
    "REAL",
    "FLOAT",
    "DOUBLE PRECISION",
    "BOOLEAN",
    "BOOL",
    "TEXT",
    "DATE",
    "TIME",
    "TIMESTAMP",
    "TIMESTAMPTZ",
    "TIMESTAMP WITH TIME ZONE",
    "TIMESTAMP WITHOUT TIME ZONE",
    "JSON",
    "JSONB",
    "UUID",
    "BYTEA",
}

TIPO_PARAMETRIZADO_REGEX = re.compile(
    r"^(VARCHAR|CHARACTER VARYING|CHAR|CHARACTER)\s*\(\s*\d{1,5}\s*\)$"
    r"|^(NUMERIC|DECIMAL)\s*\(\s*\d{1,3}(\s*,\s*\d{1,3})?\s*\)$",
    re.IGNORECASE,
)


class ColunaDefinicao(BaseModel):
    nome: str = Field(..., description="Nome da coluna (apenas letras, números e underscore)")
    tipo: str = Field(..., description="Tipo SQL PostgreSQL (ex: VARCHAR(255), INTEGER, TEXT, BOOLEAN)")
    nullable: bool = Field(True, description="Se a coluna aceita valores NULL")
    primary_key: bool = Field(False, description="Se a coluna faz parte da chave primária")
    default: Optional[str] = Field(None, description="Valor padrão opcional")


class CriarTabelaRequest(BaseModel):
    nome: str = Field(..., description="Nome da nova tabela no schema public")
    colunas: List[ColunaDefinicao] = Field(..., min_length=1)


class InserirRegistroRequest(BaseModel):
    dados: Dict[str, Any] = Field(..., description="Mapa coluna -> valor a inserir")


class AtualizarRegistroRequest(BaseModel):
    pk: Dict[str, Any] = Field(..., description="Mapa coluna_pk -> valor para localizar a linha")
    dados: Dict[str, Any] = Field(..., description="Mapa coluna -> novo valor")


class DeletarRegistroRequest(BaseModel):
    pk: Dict[str, Any] = Field(..., description="Mapa coluna_pk -> valor para excluir a linha")


class ConsultaSQLRequest(BaseModel):
    sql: str = Field(..., min_length=1, description="Consulta SQL a ser executada")
    permitir_escrita: bool = Field(
        False,
        description="Habilita comandos DDL/DML além de SELECT/EXPLAIN/SHOW",
    )


def _validar_identificador(nome: str, rotulo: str = "identificador") -> str:
    limpo = nome.strip()
    if not IDENTIFICADOR_REGEX.match(limpo):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{rotulo.capitalize()} inválido: '{nome}'. "
                "Use apenas letras, números e underscore, começando por letra ou underscore."
            ),
        )
    return limpo


def _validar_tipo_sql(tipo: str) -> str:
    limpo = re.sub(r"\s+", " ", tipo.strip()).upper()
    if limpo in TIPOS_BASE_PERMITIDOS or TIPO_PARAMETRIZADO_REGEX.match(limpo):
        return limpo
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            f"Tipo SQL não suportado ou inválido: '{tipo}'. "
            "Exemplos válidos: VARCHAR(255), TEXT, INTEGER, BIGINT, SERIAL, BOOLEAN, NUMERIC(10,2), TIMESTAMP, JSONB."
        ),
    )


def _formatar_default(valor_default: Optional[str]) -> Optional[str]:
    if valor_default is None:
        return None
    limpo = valor_default.strip()
    if not limpo:
        return None

    upper = limpo.upper()
    if upper in {"NULL", "TRUE", "FALSE", "CURRENT_TIMESTAMP", "CURRENT_DATE", "NOW()"}:
        return upper
    if re.match(r"^-?\d+(\.\d+)?$", limpo):
        return limpo

    # Qualquer outro valor é tratado como string literal escapada com segurança
    escapado = limpo.replace("'", "''")
    return f"'{escapado}'"


def _serializar_valor(valor: Any) -> Any:
    if valor is None:
        return None
    if isinstance(valor, (datetime, date, dt_time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, UUID):
        return str(valor)
    if isinstance(valor, (bytes, memoryview)):
        raw = bytes(valor)
        return f"<bytes:{len(raw)}>"
    if isinstance(valor, (dict, list)):
        return valor
    return valor


def _obter_tabelas_public(db: Session) -> List[str]:
    rows = db.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
    ).fetchall()
    return [r[0] for r in rows]


def _garantir_tabela_existe(db: Session, tabela: str) -> str:
    nome = _validar_identificador(tabela, "nome da tabela")
    tabelas = _obter_tabelas_public(db)
    if nome not in tabelas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tabela '{nome}' não encontrada no schema public.",
        )
    return nome


def _obter_metadados_tabela(db: Session, tabela: str) -> Dict[str, Any]:
    insp = inspect(engine)
    pk_info = insp.get_pk_constraint(tabela, schema="public") or {}
    pks = set(pk_info.get("constrained_columns") or [])

    cols_rows = db.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :tabela
            ORDER BY ordinal_position
            """
        ),
        {"tabela": tabela},
    ).fetchall()

    colunas = []
    for row in cols_rows:
        col_name, data_type, udt_name, max_len, num_prec, num_scale, is_null, col_def = row
        tipo_formatado = data_type
        if data_type == "character varying" and max_len:
            tipo_formatado = f"varchar({max_len})"
        elif data_type == "numeric" and num_prec:
            tipo_formatado = f"numeric({num_prec},{num_scale or 0})"
        elif data_type == "USER-DEFINED":
            tipo_formatado = udt_name

        colunas.append(
            {
                "nome": col_name,
                "tipo": tipo_formatado,
                "nullable": is_null == "YES",
                "default": col_def,
                "pk": col_name in pks,
            }
        )

    return {
        "colunas": colunas,
        "chaves_primarias": list(pk_info.get("constrained_columns") or []),
    }


def _converter_valor_entrada(valor: Any, tipo_coluna: str) -> Any:
    if valor is None:
        return None
    if isinstance(valor, str):
        if valor == "":
            # Para campos não-texto, string vazia vira NULL
            tipo_l = tipo_coluna.lower()
            if not any(t in tipo_l for t in ("char", "text")):
                return None
        tipo_l = tipo_coluna.lower()
        if "bool" in tipo_l:
            lower = valor.strip().lower()
            if lower in ("true", "1", "t", "sim", "yes"):
                return True
            if lower in ("false", "0", "f", "nao", "não", "no"):
                return False
        if "json" in tipo_l:
            try:
                return json.dumps(json.loads(valor))
            except Exception:
                pass
    if isinstance(valor, (dict, list)):
        return json.dumps(valor)
    return valor


@router.get("/tabelas", summary="Lista todas as tabelas do banco PostgreSQL")
def listar_tabelas(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        rows = db.execute(
            text(
                """
                SELECT
                    t.table_name,
                    COALESCE(s.n_live_tup, 0) AS linhas_estimadas,
                    pg_size_pretty(pg_total_relation_size(format('%I.%I', t.table_schema, t.table_name))) AS tamanho,
                    (
                        SELECT COUNT(*)
                        FROM information_schema.columns c
                        WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name
                    ) AS total_colunas
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s
                    ON s.schemaname = t.table_schema AND s.relname = t.table_name
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name
                """
            )
        ).fetchall()

        info_db = db.execute(
            text("SELECT current_database(), version(), pg_size_pretty(pg_database_size(current_database()))")
        ).fetchone()

        insp = inspect(engine)
        tabelas = []
        for r in rows:
            pk_info = insp.get_pk_constraint(r[0], schema="public") or {}
            tabelas.append(
                {
                    "nome": r[0],
                    "linhas_estimadas": int(r[1] or 0),
                    "tamanho": r[2],
                    "total_colunas": int(r[3] or 0),
                    "chaves_primarias": list(pk_info.get("constrained_columns") or []),
                }
            )

        return {
            "status": "online",
            "banco": info_db[0] if info_db else "desconhecido",
            "versao": (info_db[1].split(",")[0] if info_db and info_db[1] else "PostgreSQL"),
            "tamanho_total": info_db[2] if info_db else "N/A",
            "total_tabelas": len(tabelas),
            "tabelas": tabelas,
        }
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro ao consultar tabelas do PostgreSQL: {str(e)}",
        )


@router.get("/tabelas/{tabela}", summary="Consulta estrutura e registros de uma tabela específica")
def consultar_tabela(
    tabela: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    busca: str = Query("", description="Filtro textual em todas as colunas"),
    order_by: Optional[str] = Query(None, description="Coluna para ordenação"),
    order_dir: str = Query("asc", pattern="^(asc|desc|ASC|DESC)$"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    meta = _obter_metadados_tabela(db, nome_tabela)
    colunas = meta["colunas"]
    nomes_colunas = [c["nome"] for c in colunas]
    pks = meta["chaves_primarias"]

    if not nomes_colunas:
        return {
            "tabela": nome_tabela,
            "colunas": [],
            "chaves_primarias": [],
            "total_registros": 0,
            "page": page,
            "limit": limit,
            "total_paginas": 1,
            "registros": [],
        }

    params: Dict[str, Any] = {}
    where_sql = ""
    if busca and busca.strip():
        condicoes = [f'CAST("{col}" AS TEXT) ILIKE :busca' for col in nomes_colunas]
        where_sql = " WHERE " + " OR ".join(condicoes)
        params["busca"] = f"%{busca.strip()}%"

    coluna_ordem = None
    if order_by and order_by in nomes_colunas:
        coluna_ordem = order_by
    elif pks:
        coluna_ordem = pks[0]
    else:
        coluna_ordem = nomes_colunas[0]

    direcao = "DESC" if order_dir.lower() == "desc" else "ASC"
    offset = (page - 1) * limit

    try:
        total_registros = db.execute(
            text(f'SELECT COUNT(*) FROM "public"."{nome_tabela}"{where_sql}'),
            params,
        ).scalar() or 0

        params_query = {**params, "limit": limit, "offset": offset}
        rows = db.execute(
            text(
                f'SELECT * FROM "public"."{nome_tabela}"{where_sql} '
                f'ORDER BY "{coluna_ordem}" {direcao} '
                f"LIMIT :limit OFFSET :offset"
            ),
            params_query,
        ).mappings().all()

        registros = [
            {col: _serializar_valor(row.get(col)) for col in nomes_colunas}
            for row in rows
        ]

        total_paginas = max(1, (int(total_registros) + limit - 1) // limit)
        return {
            "tabela": nome_tabela,
            "colunas": colunas,
            "chaves_primarias": pks,
            "total_registros": int(total_registros),
            "page": page,
            "limit": limit,
            "total_paginas": total_paginas,
            "order_by": coluna_ordem,
            "order_dir": direcao.lower(),
            "registros": registros,
        }
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar registros da tabela '{nome_tabela}': {str(e)}",
        )


@router.post("/tabelas", status_code=status.HTTP_201_CREATED, summary="Cria uma nova tabela no PostgreSQL")
def criar_tabela(payload: CriarTabelaRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    nome_tabela = _validar_identificador(payload.nome, "nome da tabela")
    if nome_tabela in _obter_tabelas_public(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tabela '{nome_tabela}' já existe.",
        )

    definicoes_sql = []
    pks = []
    nomes_vistos = set()

    for col in payload.colunas:
        nome_col = _validar_identificador(col.nome, "nome da coluna")
        if nome_col in nomes_vistos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coluna duplicada: '{nome_col}'.",
            )
        nomes_vistos.add(nome_col)

        tipo_sql = _validar_tipo_sql(col.tipo)
        partes = [f'"{nome_col}" {tipo_sql}']

        if not col.nullable or col.primary_key:
            partes.append("NOT NULL")

        default_sql = _formatar_default(col.default)
        if default_sql is not None:
            partes.append(f"DEFAULT {default_sql}")

        definicoes_sql.append(" ".join(partes))
        if col.primary_key:
            pks.append(f'"{nome_col}"')

    if pks:
        definicoes_sql.append(f"PRIMARY KEY ({', '.join(pks)})")

    ddl = f'CREATE TABLE "public"."{nome_tabela}" ({", ".join(definicoes_sql)})'

    try:
        db.execute(text(ddl))
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Tabela '{nome_tabela}' criada com sucesso.",
            "sql": ddl,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao criar tabela '{nome_tabela}': {str(e.__cause__ or e)}",
        )


@router.delete("/tabelas/{tabela}", summary="Remove uma tabela inteira do banco")
def excluir_tabela(
    tabela: str,
    cascade: bool = Query(False, description="Remove também objetos/FKs dependentes (CASCADE)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    sufixo = " CASCADE" if cascade else ""
    ddl = f'DROP TABLE "public"."{nome_tabela}"{sufixo}'

    try:
        db.execute(text(ddl))
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Tabela '{nome_tabela}' removida com sucesso.",
            "sql": ddl,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não foi possível remover a tabela '{nome_tabela}': {str(e.__cause__ or e)}",
        )


@router.post("/tabelas/{tabela}/colunas", status_code=status.HTTP_201_CREATED, summary="Adiciona uma coluna à tabela")
def adicionar_coluna(
    tabela: str,
    payload: ColunaDefinicao,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    nome_col = _validar_identificador(payload.nome, "nome da coluna")
    tipo_sql = _validar_tipo_sql(payload.tipo)

    meta = _obter_metadados_tabela(db, nome_tabela)
    if any(c["nome"] == nome_col for c in meta["colunas"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A coluna '{nome_col}' já existe na tabela '{nome_tabela}'.",
        )

    partes = [f'ALTER TABLE "public"."{nome_tabela}" ADD COLUMN "{nome_col}" {tipo_sql}']
    default_sql = _formatar_default(payload.default)
    if default_sql is not None:
        partes.append(f"DEFAULT {default_sql}")
    if not payload.nullable:
        partes.append("NOT NULL")

    ddl = " ".join(partes)

    try:
        db.execute(text(ddl))
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Coluna '{nome_col}' adicionada à tabela '{nome_tabela}'.",
            "sql": ddl,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao adicionar coluna '{nome_col}': {str(e.__cause__ or e)}",
        )


@router.delete("/tabelas/{tabela}/colunas/{coluna}", summary="Remove uma coluna de uma tabela")
def remover_coluna(
    tabela: str,
    coluna: str,
    cascade: bool = Query(False, description="Remove dependências da coluna (CASCADE)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    nome_col = _validar_identificador(coluna, "nome da coluna")

    meta = _obter_metadados_tabela(db, nome_tabela)
    if not any(c["nome"] == nome_col for c in meta["colunas"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coluna '{nome_col}' não encontrada na tabela '{nome_tabela}'.",
        )

    sufixo = " CASCADE" if cascade else ""
    ddl = f'ALTER TABLE "public"."{nome_tabela}" DROP COLUMN "{nome_col}"{sufixo}'

    try:
        db.execute(text(ddl))
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Coluna '{nome_col}' removida da tabela '{nome_tabela}'.",
            "sql": ddl,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao remover coluna '{nome_col}': {str(e.__cause__ or e)}",
        )


@router.post("/tabelas/{tabela}/registros", status_code=status.HTTP_201_CREATED, summary="Insere um novo registro")
def inserir_registro(
    tabela: str,
    payload: InserirRegistroRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    meta = _obter_metadados_tabela(db, nome_tabela)
    mapa_tipos = {c["nome"]: c["tipo"] for c in meta["colunas"]}

    if not payload.dados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe pelo menos um campo para inserir.",
        )

    colunas_sql = []
    placeholders = []
    params: Dict[str, Any] = {}

    for idx, (col, val) in enumerate(payload.dados.items()):
        if col not in mapa_tipos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coluna '{col}' não existe na tabela '{nome_tabela}'.",
            )
        colunas_sql.append(f'"{col}"')
        p_name = f"v_{idx}"
        placeholders.append(f":{p_name}")
        params[p_name] = _converter_valor_entrada(val, mapa_tipos[col])

    sql = (
        f'INSERT INTO "public"."{nome_tabela}" ({", ".join(colunas_sql)}) '
        f'VALUES ({", ".join(placeholders)}) RETURNING *'
    )

    try:
        row = db.execute(text(sql), params).mappings().first()
        db.commit()
        registro = {k: _serializar_valor(v) for k, v in dict(row).items()} if row else {}
        return {
            "status": "sucesso",
            "mensagem": f"Registro inserido na tabela '{nome_tabela}'.",
            "registro": registro,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao inserir registro: {str(e.__cause__ or e)}",
        )


@router.put("/tabelas/{tabela}/registros", summary="Atualiza um registro existente pela chave primária")
def atualizar_registro(
    tabela: str,
    payload: AtualizarRegistroRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    meta = _obter_metadados_tabela(db, nome_tabela)
    mapa_tipos = {c["nome"]: c["tipo"] for c in meta["colunas"]}
    pks = meta["chaves_primarias"]

    if not pks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A tabela '{nome_tabela}' não possui chave primária definida para edição segura.",
        )

    if not payload.dados:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo informado para atualização.",
        )

    set_clauses = []
    where_clauses = []
    params: Dict[str, Any] = {}

    for idx, (col, val) in enumerate(payload.dados.items()):
        if col not in mapa_tipos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Coluna '{col}' não existe na tabela '{nome_tabela}'.",
            )
        p_name = f"u_{idx}"
        set_clauses.append(f'"{col}" = :{p_name}')
        params[p_name] = _converter_valor_entrada(val, mapa_tipos[col])

    for idx, pk_col in enumerate(pks):
        if pk_col not in payload.pk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chave primária '{pk_col}' ausente na requisição.",
            )
        p_name = f"pk_{idx}"
        where_clauses.append(f'"{pk_col}" = :{p_name}')
        params[p_name] = payload.pk[pk_col]

    sql = (
        f'UPDATE "public"."{nome_tabela}" SET {", ".join(set_clauses)} '
        f'WHERE {" AND ".join(where_clauses)} RETURNING *'
    )

    try:
        row = db.execute(text(sql), params).mappings().first()
        if not row:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro não encontrado para atualização.",
            )
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Registro atualizado na tabela '{nome_tabela}'.",
            "registro": {k: _serializar_valor(v) for k, v in dict(row).items()},
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao atualizar registro: {str(e.__cause__ or e)}",
        )


@router.post("/tabelas/{tabela}/registros/deletar", summary="Remove um registro existente pela chave primária")
def deletar_registro(
    tabela: str,
    payload: DeletarRegistroRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    nome_tabela = _garantir_tabela_existe(db, tabela)
    meta = _obter_metadados_tabela(db, nome_tabela)
    pks = meta["chaves_primarias"]

    if not pks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A tabela '{nome_tabela}' não possui chave primária definida para exclusão segura.",
        )

    where_clauses = []
    params: Dict[str, Any] = {}
    for idx, pk_col in enumerate(pks):
        if pk_col not in payload.pk:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chave primária '{pk_col}' ausente na requisição.",
            )
        p_name = f"pk_{idx}"
        where_clauses.append(f'"{pk_col}" = :{p_name}')
        params[p_name] = payload.pk[pk_col]

    sql = f'DELETE FROM "public"."{nome_tabela}" WHERE {" AND ".join(where_clauses)}'

    try:
        res = db.execute(text(sql), params)
        if res.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro não encontrado para exclusão.",
            )
        db.commit()
        return {
            "status": "sucesso",
            "mensagem": f"Registro excluído da tabela '{nome_tabela}'.",
            "linhas_afetadas": res.rowcount,
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao excluir registro: {str(e.__cause__ or e)}",
        )


@router.post("/consulta", summary="Executa consulta SQL direta no banco")
def executar_consulta_sql(
    payload: ConsultaSQLRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    sql_limpo = payload.sql.strip()
    if not sql_limpo:
        raise HTTPException(status_code=400, detail="A consulta SQL não pode estar vazia.")

    primeiro_token = sql_limpo.split()[0].upper().lstrip("(")
    somente_leitura = primeiro_token in {"SELECT", "WITH", "SHOW", "EXPLAIN"}

    if not somente_leitura and not payload.permitir_escrita:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Comando '{primeiro_token}' requer marcar a opção 'Permitir comandos de escrita (DDL/DML)'."
            ),
        )

    inicio = time.perf_counter()
    try:
        resultado = db.execute(text(sql_limpo))
        duracao_ms = round((time.perf_counter() - inicio) * 1000, 2)

        if resultado.returns_rows:
            colunas = list(resultado.keys())
            linhas = resultado.fetchmany(200)
            registros = [
                {col: _serializar_valor(row[idx]) for idx, col in enumerate(colunas)}
                for row in linhas
            ]
            if not somente_leitura:
                db.commit()
            return {
                "status": "sucesso",
                "tipo": "consulta",
                "colunas": colunas,
                "registros": registros,
                "total_retornado": len(registros),
                "limitado_200": len(registros) == 200,
                "tempo_ms": duracao_ms,
            }

        db.commit()
        return {
            "status": "sucesso",
            "tipo": "comando",
            "colunas": [],
            "registros": [],
            "linhas_afetadas": resultado.rowcount,
            "tempo_ms": duracao_ms,
            "mensagem": f"Comando executado com sucesso ({resultado.rowcount} linha(s) afetada(s)).",
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro SQL: {str(e.__cause__ or e)}",
        )
