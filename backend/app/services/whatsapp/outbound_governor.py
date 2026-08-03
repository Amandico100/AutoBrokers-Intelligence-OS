"""O governador de vazão do WhatsApp, no caminho em que ele foi procurado.

Este arquivo **não tem lógica**. Ele existe porque `delivery_executor.py` já
tinha declarado, meses antes de o governador existir, o nome pelo qual ia
procurá-lo::

    try:
        from app.services.whatsapp import outbound_governor
    except Exception:
        return ResultadoDeCanal("whatsapp", False,
            "governador de envio ainda não existe — o briefing não sai por "
            "WhatsApp até a SPEC-063 Bloco C")

Era uma guarda por IMPORT, e não por flag, de propósito: flag alguém liga por
engano; módulo ausente, não. Honrar esse contrato era obrigação do Bloco C —
mudar o nome do lado de lá seria trocar a guarda de lugar em vez de satisfazê-la.

Por que a lógica mora em `platform_outbound.py`
-----------------------------------------------
Metade do governador já estava lá: a fila persistente em Redis, a janela de
ocupado, o backoff, o teto de tentativas e o drenador periódico. Escrever a
outra metade aqui criaria **duas filas de saída** para o mesmo canal — CLAUDE.md
§5, motor paralelo. O governador estendeu o que existia; este arquivo só aponta
para lá.

Quem importa daqui está pedindo a decisão de VAZÃO. Quem precisa enviar de fato
continua chamando `send_to_client_guarded`, que consulta esta mesma decisão.
"""

from __future__ import annotations

from app.services.platform_outbound import (  # noqa: F401
    FRIA,
    QUENTE,
    Veredito,
    avaliar_vazao,
    dentro_da_janela,
    envios_parados,
    fuso_da_corretora,
    governar_envio,
    governar_envio_sync,
    historico_de_envios,
    intervalo_entre_frias,
    maturidade_do_canal,
    parar_envios,
    proxima_abertura,
    retomar_envios,
    send_to_client_guarded,
    teto_do_dia,
)

__all__ = [
    "FRIA",
    "QUENTE",
    "Veredito",
    "avaliar_vazao",
    "dentro_da_janela",
    "envios_parados",
    "fuso_da_corretora",
    "governar_envio",
    "governar_envio_sync",
    "historico_de_envios",
    "intervalo_entre_frias",
    "maturidade_do_canal",
    "parar_envios",
    "proxima_abertura",
    "retomar_envios",
    "send_to_client_guarded",
    "teto_do_dia",
]
