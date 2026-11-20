import { AlertTriangle } from 'lucide-react';

import Modal from './Modal';

function ConfirmDialog({
  open,
  titulo = 'Confirmar ação',
  mensagem,
  confirmarLabel = 'Confirmar',
  cancelarLabel = 'Cancelar',
  processando = false,
  onConfirmar,
  onCancelar,
}) {
  return (
    <Modal open={open} titulo={titulo} onClose={onCancelar} size="sm">
      <div className="confirm-icon" aria-hidden="true">
        <AlertTriangle />
      </div>

      <p className="confirm-text">{mensagem}</p>

      <div className="modal__footer">
        <button
          type="button"
          className="btn btn--ghost"
          onClick={onCancelar}
          disabled={processando}
          data-autofocus
        >
          {cancelarLabel}
        </button>
        <button
          type="button"
          className="btn btn--danger"
          onClick={onConfirmar}
          disabled={processando}
        >
          {processando && <span className="btn__spinner" aria-hidden="true" />}
          {processando ? 'Removendo...' : confirmarLabel}
        </button>
      </div>
    </Modal>
  );
}

export default ConfirmDialog;
