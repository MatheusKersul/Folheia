import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, UserPlus } from 'lucide-react';

import { useAuth } from '../auth/useAuth';
import AuthLayout from '../components/AuthLayout';
import PasswordField from '../components/PasswordField';
import { useToast } from '../ui/useToast';

function calcularForca(senha) {
  if (!senha) {
    return 0;
  }

  let pontos = 0;

  if (senha.length >= 6) pontos += 1;
  if (senha.length >= 10) pontos += 1;
  if (/[a-z]/.test(senha) && /[A-Z]/.test(senha)) pontos += 1;
  if (/\d/.test(senha)) pontos += 1;
  if (/[^A-Za-z0-9]/.test(senha)) pontos += 1;

  return Math.min(4, pontos);
}

function classificarForca(pontos) {
  if (pontos <= 1) {
    return { classe: 'strength--fraca', rotulo: 'Fraca' };
  }

  if (pontos <= 3) {
    return { classe: 'strength--media', rotulo: 'Média' };
  }

  return { classe: 'strength--forte', rotulo: 'Forte' };
}

function Cadastro() {
  const { autenticado, cadastrar } = useAuth();
  const { notificar } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const destino = location.state?.from || '/biblioteca';

  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erro, setErro] = useState('');
  const [carregando, setCarregando] = useState(false);

  const forca = calcularForca(senha);
  const classificacao = classificarForca(forca);

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
      notificar('Conta criada com sucesso. Bem-vindo ao Folheia!', 'success');
      navigate(destino, { replace: true });
    } catch (falha) {
      setErro(falha.message);
    } finally {
      setCarregando(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Comece sua coleção"
      title="Criar conta"
      subtitle="Leva menos de um minuto. Depois é só montar sua biblioteca e descobrir novas leituras."
      footer={
        <>
          Já tem uma conta?{' '}
          <Link to="/login" state={{ from: location.state?.from }}>
            Entrar
          </Link>
        </>
      }
      legal="Seus dados são usados apenas para autenticação e para manter sua biblioteca pessoal neste projeto."
    >
      {erro && (
        <div className="alert alert--error" role="alert">
          {erro}
        </div>
      )}

      <form className="auth-form" onSubmit={enviar}>
        <div className="field">
          <label htmlFor="cadastro-nome">Nome</label>
          <input
            id="cadastro-nome"
            type="text"
            autoComplete="name"
            placeholder="Como você quer ser chamado"
            value={nome}
            onChange={(evento) => {
              setNome(evento.target.value);
              setErro('');
            }}
            data-autofocus
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
            onChange={(evento) => {
              setEmail(evento.target.value);
              setErro('');
            }}
          />
        </div>

        <PasswordField
          id="cadastro-senha"
          label="Senha"
          value={senha}
          onChange={(evento) => {
            setSenha(evento.target.value);
            setErro('');
          }}
          autoComplete="new-password"
          placeholder="Mínimo de 6 caracteres"
        />

        {senha && (
          <div className={`strength ${classificacao.classe}`}>
            <div className="strength__bars" aria-hidden="true">
              {[0, 1, 2, 3].map((indice) => (
                <span
                  key={indice}
                  className={`strength__bar ${indice < forca ? 'is-on' : ''}`}
                />
              ))}
            </div>
            <span className="strength__label" aria-live="polite">
              Força da senha: <strong>{classificacao.rotulo}</strong>
            </span>
          </div>
        )}

        <PasswordField
          id="cadastro-confirmacao"
          label="Confirmar senha"
          value={confirmacao}
          onChange={(evento) => {
            setConfirmacao(evento.target.value);
            setErro('');
          }}
          autoComplete="new-password"
          placeholder="Repita a senha"
          hint={
            confirmacao && confirmacao !== senha
              ? 'As senhas ainda não coincidem.'
              : undefined
          }
        />

        <button
          type="submit"
          className="btn btn--primary btn--block"
          disabled={carregando}
        >
          {carregando ? (
            <span className="btn__spinner" aria-hidden="true" />
          ) : (
            <UserPlus aria-hidden="true" />
          )}
          {carregando ? 'Criando conta...' : 'Criar minha conta'}
          {!carregando && <ArrowRight aria-hidden="true" />}
        </button>
      </form>
    </AuthLayout>
  );
}

export default Cadastro;
