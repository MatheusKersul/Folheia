function HeaderDecoration() {
  return (
    <svg
      className="header-decoration-left"
      viewBox="0 0 260 150"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Galho */}
      <path
        d="M18 132 C55 108, 67 78, 105 51 C130 33, 158 24, 190 15"
        fill="none"
        stroke="#FCA311"
        strokeWidth="2"
        opacity="0.65"
      />

      {/* Folha 1 */}
      <path
        d="M101 53 C88 38, 91 23, 112 18 C120 34, 116 45, 101 53Z"
        fill="#FCA311"
        opacity="0.72"
      />

      {/* Folha 2 */}
      <path
        d="M135 34 C137 17, 151 8, 168 11 C164 27, 153 35, 135 34Z"
        fill="#FCA311"
        opacity="0.48"
      />

      {/* Folha 3 */}
      <path
        d="M69 83 C52 72, 51 59, 64 48 C76 59, 78 72, 69 83Z"
        fill="#FCA311"
        opacity="0.38"
      />

      {/* Livro inferior */}
      <path
        d="M22 126
           C39 120, 65 120, 92 124
           L205 124
           C211 124, 215 128, 215 133
           L215 138
           L22 138
           Z"
        fill="#14213D"
        stroke="#FCA311"
        strokeWidth="2"
        opacity="0.95"
      />

      {/* Páginas */}
      <path
        d="M24 126 C43 121, 67 121, 92 125"
        fill="none"
        stroke="#FCA311"
        strokeWidth="2"
        opacity="0.65"
      />

      <path
        d="M28 130 C49 126, 69 126, 91 129"
        fill="none"
        stroke="#FCA311"
        strokeWidth="1"
        opacity="0.42"
      />

      {/* Livro superior */}
      <path
        d="M53 108
           C82 103, 120 104, 158 108
           L202 108
           C208 108, 212 112, 212 117
           L212 120
           L53 120
           Z"
        fill="#14213D"
        stroke="#FCA311"
        strokeWidth="2"
        opacity="0.9"
      />

      {/* Lombada */}
      <path
        d="M53 108 C49 111, 49 116, 53 120"
        fill="none"
        stroke="#FCA311"
        strokeWidth="2"
        opacity="0.6"
      />

      {/* Pequenas páginas */}
      <path
        d="M58 111 L82 111"
        stroke="#FCA311"
        strokeWidth="1"
        opacity="0.45"
      />

      <path
        d="M58 115 L78 115"
        stroke="#FCA311"
        strokeWidth="1"
        opacity="0.35"
      />
    </svg>
  );
}

export default HeaderDecoration;