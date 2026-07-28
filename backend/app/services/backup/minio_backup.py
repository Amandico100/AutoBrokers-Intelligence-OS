"""Backup do MinIO para um destino S3 externo. SPEC-062 §30.3.

O buraco que isto fecha
-----------------------
O Supabase faz backup do Postgres pelo plano. **O MinIO não tinha rotina
nenhuma.** E o MinIO guarda a única cópia de cada documento que a corretora
enviou — apólice, boleto, comprovante. O Postgres guarda o *ponteiro*, não o
arquivo. Se o volume morresse, não havia de onde reconstruir.

Antes desta rotina, o RPO real do MinIO era **"desde sempre"**.

Por que escrito em Python e não `mc mirror` / `rclone`
------------------------------------------------------
Porque os dois exigiriam instalar um binário na imagem Docker — uma dependência
nova para manter, atualizar e depurar quando o backup falhar às três da manhã.

A biblioteca `minio` já está instalada e **fala S3 com os dois lados**. Isso foi
verificado contra o Backblaze B2 em 28/07/2026 antes de uma linha ser escrita:
listar, gravar, ler de volta e conferir byte a byte. Zero dependência nova.

O que esta rotina NÃO faz, de propósito
---------------------------------------
**Não apaga nada no destino.** Não existe `--remove`, nem equivalente.

É a decisão mais importante do arquivo. Um "espelho" que replica exclusões é
inútil justamente no caso que mais importa: alguém apaga por engano, o espelho
apaga junto, e o backup vira uma cópia fiel do desastre.

O que existe no destino fica. O bucket está em *Keep all versions*, então
sobrescrever também não perde o anterior.
"""

from __future__ import annotations

import logging
import os
import time
from io import BytesIO
from typing import Any, Optional

logger = logging.getLogger(__name__)

FLAG = "MINIO_BACKUP_ENABLED"
PREFIXO_DESTINO = "documents/"

# Duas execuções ao mesmo tempo copiariam os mesmos objetos, dobrando egresso e
# custo sem nenhum ganho. O lease vive um pouco mais que a folga da rotina.
LOCK = "backup:minio"
LOCK_TTL_S = 3600


def ligado() -> bool:
    return str(os.getenv(FLAG, "0")).strip().lower() in ("1", "true", "on", "yes")


def _config() -> Optional[dict]:
    faltando = [k for k in ("MINIO_BACKUP_S3_ENDPOINT", "MINIO_BACKUP_S3_BUCKET",
                            "MINIO_BACKUP_S3_ACCESS_KEY_ID",
                            "MINIO_BACKUP_S3_SECRET_ACCESS_KEY")
                if not os.getenv(k)]
    if faltando:
        # Nomes de variável, jamais valores. Um log de backup é lido por muita
        # gente e fica guardado por muito tempo.
        logger.error("[Backup] faltam variáveis: %s", ", ".join(faltando))
        return None
    return {
        "endpoint": os.getenv("MINIO_BACKUP_S3_ENDPOINT", "").replace("https://", "")
                                                             .replace("http://", "").strip("/"),
        "bucket": os.getenv("MINIO_BACKUP_S3_BUCKET"),
        "chave": os.getenv("MINIO_BACKUP_S3_ACCESS_KEY_ID"),
        "segredo": os.getenv("MINIO_BACKUP_S3_SECRET_ACCESS_KEY"),
        "regiao": os.getenv("MINIO_BACKUP_S3_REGION") or None,
    }


def _destino(cfg: dict):
    from minio import Minio

    return Minio(cfg["endpoint"], access_key=cfg["chave"],
                 secret_key=cfg["segredo"], secure=True, region=cfg["regiao"])


def _origem():
    from ..minio_service import get_minio_service

    s = get_minio_service()
    return s.client, s.bucket_name


def _com_retentativa(fn, *, tentativas: int = 3, oque: str = ""):
    """Retentativa com espera crescente.

    Falha de rede em backup é banal e quase sempre passageira. Desistir na
    primeira transformaria um soluço de dez segundos numa hora sem cópia.
    """
    espera = 2.0
    for n in range(1, tentativas + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            if n == tentativas:
                raise
            logger.warning("[Backup] %s falhou (%s), tentativa %d/%d",
                           oque or "operação", type(exc).__name__, n, tentativas)
            time.sleep(espera)
            espera *= 2
    return None


def executar(*, limite: int = 5000) -> dict:
    """Copia o que falta. Idempotente: rodar duas vezes não copia duas vezes."""
    inicio = time.time()
    if not ligado():
        return {"ok": True, "pulado": "backup desligado nesta instalação"}

    cfg = _config()
    if not cfg:
        return {"ok": False, "erro": "configuração incompleta"}

    try:
        origem, bucket_origem = _origem()
        destino = _destino(cfg)
    except Exception as exc:  # noqa: BLE001
        logger.error("[Backup] não conectou (%s)", type(exc).__name__)
        return {"ok": False, "erro": f"conexão: {type(exc).__name__}"}

    # O que JÁ está no destino. Comparar por (nome, tamanho) é o suficiente
    # aqui: os objetos são imutáveis — cada upload gera um id novo. Comparar
    # hash exigiria baixar tudo de volta toda hora, e o custo de egresso do
    # backup passaria a ser maior que o do produto.
    try:
        ja_tem = {o.object_name: o.size for o in
                  destino.list_objects(cfg["bucket"], recursive=True)}
    except Exception as exc:  # noqa: BLE001
        logger.error("[Backup] destino ilegível (%s)", type(exc).__name__)
        return {"ok": False, "erro": f"destino: {type(exc).__name__}"}

    copiados = pulados = falhas = 0
    bytes_copiados = 0
    truncou = False

    try:
        objetos = list(origem.list_objects(bucket_origem, recursive=True))
    except Exception as exc:  # noqa: BLE001
        logger.error("[Backup] origem ilegível (%s)", type(exc).__name__)
        return {"ok": False, "erro": f"origem: {type(exc).__name__}"}

    if len(objetos) > limite:
        truncou = True
        objetos = objetos[:limite]

    for obj in objetos:
        alvo = f"{PREFIXO_DESTINO}{obj.object_name}"
        if ja_tem.get(alvo) == obj.size:
            pulados += 1
            continue
        try:
            def _copiar(o=obj, a=alvo):
                r = origem.get_object(bucket_origem, o.object_name)
                try:
                    dado = r.read()
                finally:
                    r.close()
                    r.release_conn()
                destino.put_object(cfg["bucket"], a, BytesIO(dado), len(dado))
                return len(dado)

            bytes_copiados += _com_retentativa(_copiar, oque=obj.object_name[:40]) or 0
            copiados += 1
        except Exception as exc:  # noqa: BLE001
            falhas += 1
            # O NOME do objeto, nunca o conteúdo.
            logger.error("[Backup] objeto não copiado: %s (%s)",
                         obj.object_name[:60], type(exc).__name__)

    duracao = round(time.time() - inicio, 2)
    resultado = {
        "ok": falhas == 0,
        "objetos_na_origem": len(objetos),
        "copiados": copiados,
        "ja_estavam": pulados,
        "falhas": falhas,
        "bytes": bytes_copiados,
        "mb": round(bytes_copiados / 1024 / 1024, 3),
        "duracao_s": duracao,
        "truncado": truncou,
    }
    logger.info("[Backup] %s", resultado)
    return resultado


def conferir() -> dict:
    """Origem e destino batem em contagem e tamanho?

    Backup que ninguém confere é backup que ninguém tem. Esta é a diferença
    entre "a rotina rodou" e "a cópia existe".
    """
    cfg = _config()
    if not cfg:
        return {"ok": False, "erro": "configuração incompleta"}
    try:
        origem, bucket_origem = _origem()
        destino = _destino(cfg)
        o = list(origem.list_objects(bucket_origem, recursive=True))
        d = {x.object_name: x.size for x in
             destino.list_objects(cfg["bucket"], recursive=True)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "erro": type(exc).__name__}

    # Só conta o que veio deste backup. O destino pode legitimamente ter mais
    # coisa (objeto apagado na origem CONTINUA aqui — é o ponto do backup).
    meus = {k: v for k, v in d.items() if k.startswith(PREFIXO_DESTINO)}
    faltando = [x.object_name for x in o
                if meus.get(f"{PREFIXO_DESTINO}{x.object_name}") != x.size]

    return {
        "ok": not faltando,
        "origem_objetos": len(o),
        "origem_bytes": sum(x.size or 0 for x in o),
        "backup_objetos": len(meus),
        "backup_bytes": sum(meus.values()),
        "faltando": len(faltando),
        "exemplos_faltando": faltando[:5],
        "preservados_alem_da_origem": max(0, len(meus) - len(o)),
        "frase": ("Backup completo: tudo que está na origem está na cópia."
                  if not faltando else
                  f"{len(faltando)} objeto(s) ainda não copiados."),
    }


def provar_restauracao(objeto: Optional[str] = None) -> dict:
    """Baixa um objeto do backup e compara com o original, byte a byte.

    Um backup que nunca foi restaurado é uma suposição. Esta função transforma
    a suposição em fato — e é barata o bastante para rodar sempre que se
    quiser duvidar.
    """
    import hashlib

    cfg = _config()
    if not cfg:
        return {"ok": False, "erro": "configuração incompleta"}
    try:
        origem, bucket_origem = _origem()
        destino = _destino(cfg)
        if not objeto:
            todos = list(origem.list_objects(bucket_origem, recursive=True))
            if not todos:
                return {"ok": False, "erro": "não há objeto para provar"}
            objeto = todos[0].object_name

        def _ler(cli, bkt, nome) -> bytes:
            r = cli.get_object(bkt, nome)
            try:
                return r.read()
            finally:
                r.close()
                r.release_conn()

        a = _ler(origem, bucket_origem, objeto)
        b = _ler(destino, cfg["bucket"], f"{PREFIXO_DESTINO}{objeto}")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "objeto": objeto, "erro": type(exc).__name__}

    igual = a == b
    return {
        "ok": igual,
        "objeto": objeto,
        "bytes": len(a),
        "sha256_origem": hashlib.sha256(a).hexdigest()[:32],
        "sha256_backup": hashlib.sha256(b).hexdigest()[:32],
        "frase": ("Restauração provada: o arquivo do backup é idêntico ao "
                  "original." if igual else
                  "DIVERGENTE — o backup não reproduz o original."),
    }


# ---------------------------------------------------------------------------
# Agendamento
# ---------------------------------------------------------------------------
async def rodar_periodicamente() -> None:
    """Chamado de hora em hora pelo scheduler. Nunca levanta."""
    if not ligado():
        return
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        # `nx=True`: só pega o lock quem chegou primeiro. Sem isto, duas
        # instâncias da API copiariam os mesmos objetos e dobrariam o egresso.
        if r is not None and not await r.set(LOCK, "1", ex=LOCK_TTL_S, nx=True):
            logger.info("[Backup] outra execução em andamento — pulando")
            return
    except Exception:  # noqa: BLE001
        # Sem Redis, seguir mesmo assim: perder uma hora de backup por causa de
        # cache indisponível é pior que o risco de uma cópia duplicada.
        pass

    import asyncio

    resultado = await asyncio.to_thread(executar)

    if not resultado.get("ok"):
        await _alertar(resultado)


async def _alertar(resultado: dict) -> None:
    """Backup que falha em silêncio é backup que não existe."""
    try:
        from app.services.whatsapp.alerts import alerta_de_plataforma

        await alerta_de_plataforma(
            "Backup do storage falhou",
            f"A cópia dos documentos não completou: "
            f"{resultado.get('falhas', '?')} falha(s), "
            f"{resultado.get('copiados', 0)} copiado(s). "
            f"Motivo: {resultado.get('erro', 'ver logs')}.")
    except Exception as exc:  # noqa: BLE001
        logger.error("[Backup] alerta não enviado: %s", type(exc).__name__)
