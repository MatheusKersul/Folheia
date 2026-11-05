import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Adiciona o diretório backend ao sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from core.database import Base, get_db
from models.book import Edition
from server import app


class TestBibliotecaAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.test_engine
        )
        Base.metadata.create_all(bind=cls.test_engine)

        def override_get_db():
            db = cls.TestSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

        # Duas obras oficiais no catálogo
        with cls.TestSessionLocal() as session:
            session.add_all(
                [
                    Edition(
                        isbn_13="9780000000011",
                        titulo="Livro Oficial Um",
                        autor="Autora Um",
                        editora="Editora Oficial",
                        num_paginas=200,
                        formato="Capa Comum",
                        data_publicacao="2020",
                    ),
                    Edition(
                        isbn_13="9780000000028",
                        titulo="Livro Oficial Dois",
                        autor="Autor Dois",
                        editora="Editora Oficial",
                        num_paginas=300,
                    ),
                ]
            )
            session.commit()

        # Usuários A e B com tokens reais (fluxo de cadastro + login)
        cls.token_a = cls._registrar_e_logar("Ana", "ana@exemplo.com")
        cls.token_b = cls._registrar_e_logar("Bruno", "bruno@exemplo.com")

    @classmethod
    def _registrar_e_logar(cls, nome: str, email: str) -> str:
        resposta = cls.client.post(
            "/auth/register",
            json={"nome": nome, "email": email, "senha": "senhaSegura123"},
        )
        assert resposta.status_code == 201, resposta.text

        resposta = cls.client.post(
            "/auth/login",
            json={"email": email, "senha": "senhaSegura123"},
        )
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["usuario"]["token"]

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    # ------------------------------ helpers ------------------------------
    @staticmethod
    def _auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _criar_biblioteca_pessoal(self, titulo: str) -> dict:
        resposta = self.client.post(
            "/biblioteca/edicoes-proprias",
            json={"titulo": titulo, "autor": "Autor Próprio"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        return resposta.json()

    # ------------------------------ testes ------------------------------
    def test_01_endpoints_exigem_token(self):
        self.assertEqual(self.client.get("/biblioteca").status_code, 401)
        self.assertEqual(self.client.get("/biblioteca/edicoes-proprias").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/biblioteca/livros", json={"edition_id": 1}
            ).status_code,
            401,
        )
        self.assertEqual(
            self.client.post(
                "/biblioteca/edicoes-proprias", json={"titulo": "X"}
            ).status_code,
            401,
        )
        self.assertEqual(self.client.get("/biblioteca/itens/1").status_code, 401)
        self.assertEqual(self.client.delete("/biblioteca/itens/1").status_code, 401)

    def test_02_token_invalido(self):
        resposta = self.client.get(
            "/biblioteca", headers={"Authorization": "Bearer token-invalido"}
        )
        self.assertEqual(resposta.status_code, 401)
        self.assertIn("WWW-Authenticate", resposta.headers)

    def test_03_token_expirado(self):
        payload = {
            "sub": "1",
            "email": "ana@exemplo.com",
            "permissoes": "usuario",
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        resposta = self.client.get("/biblioteca", headers=self._auth(token))
        self.assertEqual(resposta.status_code, 401)

    def test_04_biblioteca_vazia(self):
        resposta = self.client.get("/biblioteca", headers=self._auth(self.token_a))
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(corpo["total"], 0)
        self.assertEqual(corpo["itens"], [])

    def test_05_adicionar_livro_por_isbn(self):
        resposta = self.client.post(
            "/biblioteca/livros",
            json={"isbn": "978-00-000-0001-1"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        item = resposta.json()
        self.assertTrue(item["edicao"]["verificada"])
        self.assertFalse(item["edicao"]["propria"])
        self.assertEqual(item["edicao"]["titulo"], "Livro Oficial Um")
        self.assertEqual(item["biblioteca"]["nome"], "Minha Biblioteca")

        listagem = self.client.get("/biblioteca", headers=self._auth(self.token_a))
        self.assertEqual(listagem.json()["total"], 1)

    def test_06_adicionar_duplicado(self):
        resposta = self.client.post(
            "/biblioteca/livros",
            json={"isbn": "9780000000011"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(resposta.status_code, 409)

    def test_07_adicionar_livro_por_edition_id(self):
        with self.TestSessionLocal() as session:
            edition = (
                session.query(Edition)
                .filter(Edition.isbn_13 == "9780000000028")
                .one()
            )
            edition_id = edition.id

        resposta = self.client.post(
            "/biblioteca/livros",
            json={"edition_id": edition_id},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        self.assertEqual(resposta.json()["edicao"]["titulo"], "Livro Oficial Dois")

    def test_08_payload_ambiguo_ou_vazio(self):
        ambos = self.client.post(
            "/biblioteca/livros",
            json={"edition_id": 1, "isbn": "9780000000011"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(ambos.status_code, 422)

        nenhum = self.client.post(
            "/biblioteca/livros", json={}, headers=self._auth(self.token_a)
        )
        self.assertEqual(nenhum.status_code, 422)

    def test_09_criar_edicao_propria(self):
        item = self._criar_biblioteca_pessoal("Minha Edição Artesanal")
        self.assertFalse(item["edicao"]["verificada"])
        self.assertTrue(item["edicao"]["propria"])
        self.assertIsNone(item["edicao"]["isbn"])

        listagem = self.client.get(
            "/biblioteca",
            params={"q": "Artesanal"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(listagem.status_code, 200)
        self.assertEqual(listagem.json()["total"], 1)

        proprias = self.client.get(
            "/biblioteca/edicoes-proprias", headers=self._auth(self.token_a)
        )
        self.assertEqual(proprias.status_code, 200)
        self.assertEqual(proprias.json()["total"], 1)

    def test_10_edicao_propria_com_isbn_do_catalogo(self):
        resposta = self.client.post(
            "/biblioteca/edicoes-proprias",
            json={"titulo": "Cópia do catálogo", "isbn": "9780000000011"},
            headers=self._auth(self.token_a),
        )
        self.assertEqual(resposta.status_code, 409)

    def test_11_edicao_propria_nao_aparece_na_busca_publica(self):
        # Usuário A possui a edição "Minha Edição Artesanal" (privada).
        resposta = self.client.get(
            "/buscar-livros?tipo=titulo&termo=Artesanal",
        )
        self.assertEqual(resposta.status_code, 404)

    def test_12_privacidade_listagem_de_outro_usuario(self):
        listagem_b = self.client.get("/biblioteca", headers=self._auth(self.token_b))
        self.assertEqual(listagem_b.status_code, 200)
        self.assertEqual(listagem_b.json()["total"], 0)

        proprias_b = self.client.get(
            "/biblioteca/edicoes-proprias", headers=self._auth(self.token_b)
        )
        self.assertEqual(proprias_b.json()["total"], 0)

    def test_13_privacidade_item_de_outro_usuario(self):
        itens_a = self.client.get("/biblioteca", headers=self._auth(self.token_a)).json()
        item_id = itens_a["itens"][0]["id"]

        consulta = self.client.get(
            f"/biblioteca/itens/{item_id}", headers=self._auth(self.token_b)
        )
        self.assertEqual(consulta.status_code, 404)

        remocao = self.client.delete(
            f"/biblioteca/itens/{item_id}", headers=self._auth(self.token_b)
        )
        self.assertEqual(remocao.status_code, 404)

        # O item continua existindo para o dono.
        ainda_existe = self.client.get(
            f"/biblioteca/itens/{item_id}", headers=self._auth(self.token_a)
        )
        self.assertEqual(ainda_existe.status_code, 200)

    def test_14_privacidade_edicao_propria_por_edition_id(self):
        proprias = self.client.get(
            "/biblioteca/edicoes-proprias", headers=self._auth(self.token_a)
        ).json()
        edicao_id = proprias["edicoes"][0]["id"]

        resposta = self.client.post(
            "/biblioteca/livros",
            json={"edition_id": edicao_id},
            headers=self._auth(self.token_b),
        )
        self.assertEqual(resposta.status_code, 404)

        # Nem por ISBN/informação direta o item privado de A é acessível a B.
        consulta = self.client.get(
            f"/biblioteca/itens/{edicao_id}", headers=self._auth(self.token_b)
        )
        self.assertEqual(consulta.status_code, 404)

    def test_15_remover_item_proprio(self):
        itens = self.client.get(
            "/biblioteca", params={"limit": 100}, headers=self._auth(self.token_a)
        ).json()
        total_antes = itens["total"]
        item_id = itens["itens"][0]["id"]

        remocao = self.client.delete(
            f"/biblioteca/itens/{item_id}", headers=self._auth(self.token_a)
        )
        self.assertEqual(remocao.status_code, 204)

        depois = self.client.get(
            "/biblioteca", params={"limit": 100}, headers=self._auth(self.token_a)
        ).json()
        self.assertEqual(depois["total"], total_antes - 1)

    def test_16_busca_publica_continua_funcionando(self):
        resposta = self.client.get("/buscar-livros?tipo=titulo&termo=Oficial Um")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["isbn"], "9780000000011")


if __name__ == "__main__":
    unittest.main()
