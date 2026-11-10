import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';

import { useAuth } from '../auth/useAuth';

function Cadastro() {
  const { autenticado, cadastrar } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = location.state?.from || '/biblioteca';

  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  if (autenticado) {
    return <Navigate to={destino} replace />;
  }

  const enviar = async (evento) => {
    evento.preventDefault();
    setErro('');

    if (!nome.trim() || !email.trim() || !senha) {
      setErro('Preencha nome, e-mail e senha.');
      return;
    }

    if (senha.length < 6) {
      setErro('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    if (senha !== confirmacao) {
      setErro('As senhas não coincidem.');
      return;
    }

    setCarregando(true);

    try {
      await cadastrar(nome.trim(), email.trim(), senha);
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="auth-card">
      <h2>Criar conta</h2>
      <p className="auth-subtitle">
        Cadastre-se para montar sua biblioteca pessoal e acompanhar suas
        edições.
      </p>

      {erro && <div className="alert alert-error">{erro}</div>}

      <form className="auth-form" onSubmit={enviar}>
        <div className="field">
          <label htmlFor="cadastro-nome">Nome</label>
          <input
            id="cadastro-nome"
            type="text"
            autoComplete="name"
            placeholder="Como você quer ser chamado"
            value={nome}
            onChange={(evento) => setNome(evento.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="cadastro-email">E-mail</label>
          <input
            id="cadastro-email"
            type="email"
            autoComplete="email"
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="cadastro-senha">Senha</label>
          <input
            id="cadastro-senha"
            type="password"
            autoComplete="new-password"
            placeholder="Mínimo de 6 caracteres"
            value={senha}
            onChange={(evento) => setSenha(evento.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="cadastro-confirmacao">Confirmar senha</label>
          <input
            id="cadastro-confirmacao"
            type="password"
            autoComplete="new-password"
            placeholder="Repita a senha"
            value={confirmacao}
            onChange={(evento) => setConfirmacao(evento.target.value)}
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={carregando}
        >
          <UserPlus />
          {carregando ? 'Criando conta...' : 'Criar conta'}
        </button>
      </form>

      <div className="auth-footer">
        Já tem uma conta?{' '}
        <Link to="/login" state={{ from: location.state?.from }}>
          Entrar
        </Link>
      </div>
    </div>
  );
}

export default Cadastro;
