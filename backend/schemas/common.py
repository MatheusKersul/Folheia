from pydantic import BaseModel

class DadosMensagem(BaseModel):
    """Schema para mensagens genéricas enviadas à API."""
    mensagem: str


# Alias para total retrocompatibilidade com o nome usado no server.py original
Dadosmensagem = DadosMensagem


class StatusConexao(BaseModel):
    """Schema de status para o endpoint de health check."""
    status: str
    mensagem: str
