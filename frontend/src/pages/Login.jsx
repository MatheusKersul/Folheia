import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, LogIn } from 'lucide-react';

import { useAuth } from '../auth/useAuth';
import AuthLayout from '../components/AuthLayout';
import PasswordField from '../components/PasswordField';
import { useToast } from '../ui/useToast';

function Login() {
  const { autenticado, login } = useAuth();
  const { notificar } = useToast();
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
      notificar('Bem-vindo de volta! Boa leitura.', 'success');
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Boas-vindas de volta"
      title="Entrar na sua conta"
      subtitle="Acesse sua biblioteca pessoal, acompanhe suas edições e continue de onde parou."
      footer={
        <>
          Ainda não tem conta?{' '}
          <Link to="/cadastro" state={{ from: location.state?.from }}>
            Criar conta
          </Link>
        </>
      }
      legal="Ao entrar, você concorda com o uso responsável dos dados da sua conta neste projeto acadêmico."
    >
      {mensagemInicial && (
        <div className="alert alert--success" role="status">
          {mensagemInicial}
        </div>
      )}

      {erro && (
        <div className="alert alert--error" role="alert">
          {erro}
        </div>
      )}

      <form className="auth-form" onSubmit={enviar}>
        <div className="field">
          <label htmlFor="login-email">E-mail</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(evento) => {
              setEmail(evento.target.value);
              setErro('');
            }}
            data-autofocus
          />
        </div>

        <PasswordField
          id="login-senha"
          label="Senha"
          value={senha}
          onChange={(evento) => {
            setSenha(evento.target.value);
            setErro('');
          }}
          autoComplete="current-password"
          placeholder="Digite sua senha"
        />

        <button
          type="submit"
          className="btn btn--primary btn--block"
          disabled={carregando}
        >
          {carregando ? (
            <span className="btn__spinner" aria-hidden="true" />
          ) : (
            <LogIn aria-hidden="true" />
          )}
          {carregando ? 'Entrando...' : 'Entrar'}
          {!carregando && <ArrowRight aria-hidden="true" />}
        </button>
      </form>
    </AuthLayout>
  );
}

export default Login;
