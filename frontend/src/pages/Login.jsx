import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';

import { useAuth } from '../auth/useAuth';

function Login() {
  const { autenticado, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = location.state?.from || '/biblioteca';
  const mensagemInicial = location.state?.mensagem || '';

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  if (autenticado) {
    return <Navigate to={destino} replace />;
  }

  const enviar = async (evento) => {
    evento.preventDefault();
    setErro('');

    if (!email.trim() || !senha) {
      setErro('Informe e-mail e senha para entrar.');
      return;
    }

    setCarregando(true);

    try {
      await login(email.trim(), senha);
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="auth-card">
      <h2>Entrar</h2>
      <p className="auth-subtitle">
        Acesse sua conta para consultar e gerenciar sua biblioteca pessoal.
      </p>

      {mensagemInicial && (
        <div className="alert alert-success">{mensagemInicial}</div>
      )}

      {erro && <div className="alert alert-error">{erro}</div>}

      <form className="auth-form" onSubmit={enviar}>
        <div className="field">
          <label htmlFor="login-email">E-mail</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="login-senha">Senha</label>
          <input
            id="login-senha"
            type="password"
            autoComplete="current-password"
            placeholder="Sua senha"
            value={senha}
            onChange={(evento) => setSenha(evento.target.value)}
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary btn-block"
          disabled={carregando}
        >
          <LogIn />
          {carregando ? 'Entrando...' : 'Entrar'}
        </button>
      </form>

      <div className="auth-footer">
        Ainda não tem conta?{' '}
        <Link
          to="/cadastro"
          state={{ from: location.state?.from }}
        >
          Cadastre-se
        </Link>
      </div>
    </div>
  );
}

export default Login;
