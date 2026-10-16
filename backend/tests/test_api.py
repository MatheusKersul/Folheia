import unittest
import sys
from pathlib import Path

# Adiciona o diretório backend ao sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from core.database import Base, get_db
from models.user import User
from models.book import Edition
from server import app

class TestFolheiaAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configura banco SQLite em memória compartilhado via StaticPool
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

        # Popula um livro de exemplo para testes de busca
        with cls.TestSessionLocal() as session:
            livro = Edition(
                isbn_13="9780000000001",
                titulo="Estrutura de Dados e Algoritmos",
                data_publicacao="2020",
                formato="Capa Comum",
                num_paginas=400,
                editora="Editora Exemplo",
                autor="Alan Turing",
            )
            session.add(livro)
            session.commit()

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    def test_01_health_check(self):
        response = self.client.get("/testar-conexao")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "sucesso")

    def test_02_receive_message(self):
        payload = {"mensagem": "Teste de integracao"}
        response = self.client.post("/receive-message", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["received"], "Teste de integracao")

    def test_03_cadastro_sucesso(self):
        payload = {
            "nome": "Usuario Teste",
            "email": "usuario.teste@exemplo.com",
            "senha": "senhaSegura123",
        }
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["usuario"]["Email"], "usuario.teste@exemplo.com")
        self.assertEqual(data["usuario"]["Nome"], "Usuario Teste")

    def test_04_cadastro_duplicado(self):
        payload = {
            "nome": "Usuario Duplicado",
            "email": "usuario.teste@exemplo.com",
            "senha": "outrasenha123",
        }
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("já cadastrado", response.json()["detail"])

    def test_05_login_sucesso(self):
        payload = {
            "email": "usuario.teste@exemplo.com",
            "senha": "senhaSegura123",
        }
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("token", data["usuario"])
        self.assertEqual(data["usuario"]["Email"], "usuario.teste@exemplo.com")

    def test_06_login_senha_invalida(self):
        payload = {
            "email": "usuario.teste@exemplo.com",
            "senha": "senhaIncorreta",
        }
        response = self.client.post("/auth/login", json=payload)
        self.assertEqual(response.status_code, 401)

    def test_07_busca_livro_titulo(self):
        response = self.client.get("/buscar-livros?tipo=titulo&termo=Estrutura")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["isbn"], "9780000000001")

    def test_08_busca_livro_isbn(self):
        response = self.client.get("/buscar-livros?tipo=isbn&termo=978-00-000-0000-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["isbn"], "9780000000001")

    def test_09_busca_livro_autor(self):
        response = self.client.get("/buscar-livros?tipo=autor&termo=Turing")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["autor"], "Alan Turing")

    def test_10_busca_livro_nao_encontrado(self):
        response = self.client.get("/buscar-livros?tipo=titulo&termo=Inexistente123")
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
