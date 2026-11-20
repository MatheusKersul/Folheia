import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

function Modal({ open, titulo, subtitulo, onClose, children, size = 'md' }) {
  const idTitulo = useId();
  const caixaRef = useRef(null);
  const focoAnterior = useRef(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    focoAnterior.current = document.activeElement;

    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const aoTeclar = (evento) => {
      if (evento.key === 'Escape') {
        onClose();
        return;
      }

      if (evento.key !== 'Tab' || !caixaRef.current) {
        return;
      }

      const focaveis = caixaRef.current.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );

      if (focaveis.length === 0) {
        return;
      }

      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];

      if (evento.shiftKey && document.activeElement === primeiro) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primeiro.focus();
      }
    };

    document.addEventListener('keydown', aoTeclar);

    const timer = window.setTimeout(() => {
      const alvo =
        caixaRef.current?.querySelector('[data-autofocus]') ||
        caixaRef.current?.querySelector(
          'input:not([type="hidden"]), textarea, select, button',
        );

      alvo?.focus();
    }, 60);

    return () => {
      document.removeEventListener('keydown', aoTeclar);
      document.body.style.overflow = overflowAnterior;
      window.clearTimeout(timer);
      if (focoAnterior.current instanceof HTMLElement) {
        focoAnterior.current.focus();
      }
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div
      className="modal-backdrop"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className={`modal ${size === 'sm' ? 'modal--sm' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        ref={caixaRef}
      >
        <div className="modal__header">
          <div>
            <h2 className="modal__title" id={idTitulo}>
              {titulo}
            </h2>
            {subtitulo && <p className="modal__subtitle">{subtitulo}</p>}
          </div>

          <button
            type="button"
            className="modal__close"
            onClick={onClose}
            aria-label="Fechar janela"
          >
            <X />
          </button>
        </div>

        <div className="modal__body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

export default Modal;
