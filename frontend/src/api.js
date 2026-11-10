const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(mensagem, status) {
    super(mensagem);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      'Não foi possível conectar ao servidor. Verifique se a API está em execução.',
      0,
    );
  }

  if (response.status === 204) {
    return null;
  }

  const texto = await response.text();
  let dados = null;

  if (texto) {
    try {
      dados = JSON.parse(texto);
    } catch {
      dados = texto;
    }
  }

  if (!response.ok) {
    const detalhe = typeof dados === 'string' ? dados : dados?.detail;
    const mensagem = Array.isArray(detalhe)
      ? detalhe.map((item) => item?.msg ?? String(item)).join(' ')
      : detalhe || `Erro ${response.status} ao chamar a API.`;

    throw new ApiError(mensagem, response.status);
  }

  return dados;
}

export const api = {
  baseUrl: API_BASE_URL,

  login: (email, senha) =>
    request('/auth/login', { method: 'POST', body: { email, senha } }),

  cadastrar: (nome, email, senha) =>
    request('/auth/register', { method: 'POST', body: { nome, email, senha } }),

  buscarLivros: ({ tipo, termo }) =>
    request(
      `/buscar-livros?tipo=${encodeURIComponent(tipo)}&termo=${encodeURIComponent(termo)}`,
    ),

  listarBiblioteca: (token, { page = 1, limit = 20, q = '' } = {}) => {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });

    if (q && q.trim()) {
      params.set('q', q.trim());
    }

    return request(`/biblioteca?${params.toString()}`, { token });
  },

  listarEdicoesProprias: (token, { page = 1, limit = 20 } = {}) =>
    request(
      `/biblioteca/edicoes-proprias?page=${page}&limit=${limit}`,
      { token },
    ),

  adicionarLivro: (token, payload) =>
    request('/biblioteca/livros', { method: 'POST', body: payload, token }),

  criarEdicaoPropria: (token, payload) =>
    request('/biblioteca/edicoes-proprias', {
      method: 'POST',
      body: payload,
      token,
    }),

  removerItem: (token, itemId) =>
    request(`/biblioteca/itens/${itemId}`, { method: 'DELETE', token }),
};
