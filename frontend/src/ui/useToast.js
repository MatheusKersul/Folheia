import { useContext } from 'react';

import { ToastContext } from './context';

export function useToast() {
  const contexto = useContext(ToastContext);

  if (!contexto) {
    throw new Error('useToast deve ser usado dentro de um ToastProvider.');
  }

  return contexto;
}
