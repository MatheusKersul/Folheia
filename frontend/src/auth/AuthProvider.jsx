import { useCallback, useMemo, useState } from 'react';

import { api } from '../api';
import { AuthContext } from './context';

const TOKEN_KEY = 'folheia.token';
const USUARIO_KEY = 'folheia.usuario';

function lerUsuarioSalvo() {
  try {
    const bruto = localStorage.getItem(USUARIO_KEY);
    return bruto ? JSON.parse(bruto) : null;
  } catch {
    return null;
  }
}

function normalizarUsuario(usuario) {
  return {
    id: usuario?.id ?? null,
    nome: usuario?.Nome ?? usuario?.nome ?? '',
    email: usuario?.Email ?? usuario?.email ?? '',
    permissoes: usuario?.Permissoes ?? usuario?.permissoes ?? 'usuario',
  };
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [usuario, setUsuario] = useState(lerUsuarioSalvo);

  const salvarSessao = useCallback((dadosUsuario) => {
    const normalizado = normalizarUsuario(dadosUsuario);

    localStorage.setItem(TOKEN_KEY, dadosUsuario.token);
    localStorage.setItem(USUARIO_KEY, JSON.stringify(normalizado));

    setToken(dadosUsuario.token);
    setUsuario(normalizado);

    return normalizado;
  }, []);

  const login = useCallback(
    async (email, senha) => {
      const resposta = await api.login(email, senha);
      const dadosUsuario = resposta?.usuario;

      if (!dadosUsuario?.token) {
        throw new Error('Resposta de login inválida: token não recebido.');
      }

      return salvarSessao(dadosUsuario);
    },
    [salvarSessao],
  );

  const cadastrar = useCallback(
    async (nome, email, senha) => {
      await api.cadastrar(nome, email, senha);
      return login(email, senha);
    },
    [login],
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USUARIO_KEY);
    setToken(null);
    setUsuario(null);
  }, []);

  const valor = useMemo(
    () => ({
      token,
      usuario,
      autenticado: Boolean(token),
      login,
      cadastrar,
      logout,
    }),
    [token, usuario, login, cadastrar, logout],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
