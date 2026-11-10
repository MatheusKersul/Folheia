import { useContext } from 'react';

import { AuthContext } from './context';

export function useAuth() {
  const contexto = useContext(AuthContext);

  if (!contexto) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider.');
  }

  return contexto;
}
