import io
import logging
from typing import Optional
import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError

from core.config import AWS_REGION_S3, S3_BUCKET_NAME

logger = logging.getLogger(__name__)

s3_client = boto3.client("s3", region_name=AWS_REGION_S3)


def upload_capa_por_url(image_url: str, isbn: str) -> Optional[str]:
    """
    Baixa uma imagem da URL externa diretamente para buffer em memória (BytesIO)
    e envia para o bucket S3, sem tocar no disco.

    Retorna a URL final da imagem no S3 ou None em caso de falha.
    """
    if not image_url or not isbn:
        return None

    clean_isbn = "".join(filter(str.isalnum, str(isbn)))
    if not clean_isbn:
        return None

    try:
        response = requests.get(
            image_url,
            stream=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if response.status_code != 200:
            logger.warning("Falha ao baixar imagem %s (Status: %s)", image_url, response.status_code)
            return None

        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        ext = "jpg"
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"

        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                buffer.write(chunk)

        buffer.seek(0)
        file_size = buffer.getbuffer().nbytes
        if file_size == 0:
            logger.warning("Imagem vazia recebida de %s", image_url)
            return None

        if file_size > 10 * 1024 * 1024:
            logger.warning("Imagem de %s excede 10MB (%s bytes)", image_url, file_size)
            return None

        s3_key = f"capas/{clean_isbn}.{ext}"

        s3_client.upload_fileobj(
            buffer,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )

        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION_S3}.amazonaws.com/{s3_key}"
        logger.info("Upload da capa concluído com sucesso: %s -> %s", clean_isbn, s3_url)
        return s3_url

    except (requests.RequestException, BotoCoreError, ClientError) as e:
        logger.error("Erro ao enviar capa para o S3 (ISBN %s): %s", isbn, e)
        return None
    except Exception as e:
        logger.error("Erro inesperado no upload da capa (ISBN %s): %s", isbn, e)
        return None
