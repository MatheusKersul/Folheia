import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

import { ToastContext } from './context';

const ICONES = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

const DURACAO = 4400;

function ToastItem({ toast, onClose }) {
  const Icone = ICONES[toast.tipo] || Info;

  useEffect(() => {
    const timer = window.setTimeout(() => onClose(toast.id), DURACAO);
    return () => window.clearTimeout(timer);
  }, [toast.id, onClose]);

  return (
    <div
      className={`toast toast--${toast.tipo}`}
      role={toast.tipo === 'error' ? 'alert' : 'status'}
    >
      <span className="toast__icon" aria-hidden="true">
        <Icone />
      </span>
      <p className="toast__message">{toast.mensagem}</p>
      <button
        type="button"
        className="toast__close"
        onClick={() => onClose(toast.id)}
        aria-label="Fechar aviso"
      >
        <X />
      </button>
      <span className="toast__bar" aria-hidden="true" />
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const sequencia = useRef(0);

  const fechar = useCallback((id) => {
    setToasts((atual) => atual.filter((toast) => toast.id !== id));
  }, []);

  const notificar = useCallback((mensagem, tipo = 'info') => {
    if (!mensagem) {
      return null;
    }

    sequencia.current += 1;
    const id = sequencia.current;
    const toast = { id, mensagem, tipo };

    setToasts((atual) => [...atual.slice(-3), toast]);
    return id;
  }, []);

  const valor = useMemo(() => ({ notificar }), [notificar]);

  return (
    <ToastContext.Provider value={valor}>
      {children}

      <div className="toast-viewport" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={fechar} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
