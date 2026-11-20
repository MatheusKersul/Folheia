import { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

function PasswordField({
  id,
  label,
  value,
  onChange,
  autoComplete = 'current-password',
  placeholder = 'Sua senha',
  hint,
}) {
  const [visivel, setVisivel] = useState(false);

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>

      <div className="password-field">
        <input
          id={id}
          type={visivel ? 'text' : 'password'}
          autoComplete={autoComplete}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisivel((atual) => !atual)}
          aria-label={visivel ? 'Ocultar senha' : 'Mostrar senha'}
          aria-pressed={visivel}
        >
          {visivel ? <EyeOff /> : <Eye />}
        </button>
      </div>

      {hint && <span className="field__hint">{hint}</span>}
    </div>
  );
}

export default PasswordField;
