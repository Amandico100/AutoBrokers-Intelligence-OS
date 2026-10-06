# -*- coding: utf-8 -*-
"""O COMANDO da proposta — SPEC-130-A U7: o Founder publica a proposta de um pedido de dentro do contêiner.

    python -m app.services.multicalculo.comando_proposta --pedido <uuid do pedido>                 (ENSAIO: não grava)
    python -m app.services.multicalculo.comando_proposta --pedido <uuid do pedido> --confirmar     (publica o link)
        [--situacao novo_sem_apolice|novo_com_apolice|renovacao] [--nome <primeiro nome do cliente>]
        [--solicitante <uuid de quem pediu>]

Sem `--confirmar` o comando MONTA a proposta e imprime o que a página e a mensagem diriam, sem gravar uma linha
(decisão F3, nota 85 × publicar direto 65: o link é público e fica no banco do solicitante — ensaiar não custa nada,
desfazer custa revogar). Com `--confirmar` cria/versiona o artefato, publica e imprime a URL e os 2 balões.
⛔ Nenhuma mensagem é ENVIADA (o envio é da 133-A). ⛔ Nada de segredo na saída: nem chave, nem env, nem comissão.

O solicitante: o dono do pedido (lido de `multicalculo_pedidos` pelo id); `--solicitante` só confere. Saída 0 = ok ·
2 = recusado (pedido de outro solicitante, nada a propor, sem endereço público) · 1 = falha inesperada.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from typing import Any, List, Optional

from app.services.multicalculo.comparacao import SITUACOES

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _argumentos(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="comando_proposta", description="Publica a proposta de um pedido do multicálculo.")
    p.add_argument("--pedido", required=True, help="o uuid do pedido (multicalculo_pedidos.id)")
    p.add_argument("--situacao", default="novo_sem_apolice", choices=SITUACOES)
    p.add_argument("--nome", default=None, help="o primeiro nome do cliente (opcional)")
    p.add_argument("--solicitante", default=None, help="confere o dono do pedido (opcional)")
    p.add_argument("--confirmar", action="store_true", help="publica de verdade (sem isto: só o ensaio)")
    return p.parse_args(argv)


def dono_do_pedido(db: Any, pedido_id: str) -> Optional[str]:
    """O solicitante do pedido. Leitura de operador (service role) que devolve SÓ o company_id — a porta refaz o
    filtro de tenant em tudo o que vem depois."""
    r = db.table("multicalculo_pedidos").select("id, company_id").eq("id", pedido_id).limit(1).execute()
    linhas = list(getattr(r, "data", None) or [])
    return str(linhas[0]["company_id"]) if linhas else None


def _imprimir_modelo(modelo: dict, saida) -> None:
    r = modelo.get("resumo") or {}
    anf = modelo.get("anfitria") or {}
    print(f"anfitriã: {anf.get('nome')} · marca publicada: {'sim' if anf.get('marca_cadastrada') else 'não'} · "
          f"WhatsApp do 'Quero fechar': {'sim' if anf.get('whatsapp') else 'NÃO (o botão não aparece)'}", file=saida)
    print(f"seguradoras: {r.get('seguradoras_cotadas')} cotadas · {r.get('com_preco_comparavel')} completas · "
          f"{r.get('com_produto_diferente')} só com produto diferente · {r.get('nao_responderam')} sem resposta"
          + (f" · {r['corretoras_comparadas']} corretoras comparadas" if r.get("corretoras_comparadas") else ""),
          file=saida)
    for o in modelo.get("opcoes") or []:
        print(f"  {o['rotulo']}: {o['seguradora']} · R$ {o['premio_anual']:,.2f} por ano · nota {o['nota']}"
              .replace(",", "§").replace(".", ",").replace("§", "."), file=saida)
    print(f"válida até {modelo.get('validade_ate')}", file=saida)


async def executar(argv: Optional[List[str]] = None, *, db: Any = None, saida=None) -> int:
    from app.services.multicalculo.mensagem import mensagem_whatsapp
    from app.services.multicalculo.porta import NaoEncontrado
    from app.services.multicalculo.proposta import (LinkSemEndereco, PropostaImpossivel, montar_proposta,
                                                    publicar_proposta)

    saida = saida or sys.stdout
    a = _argumentos(argv)
    pedido = str(a.pedido).strip().lower()
    if not _UUID.match(pedido):
        print("recusado: --pedido precisa ser o uuid inteiro do pedido", file=saida)
        return 2
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    dono = dono_do_pedido(db, pedido)
    if not dono:
        print("recusado: pedido não encontrado", file=saida)
        return 2
    if a.solicitante and str(a.solicitante).strip().lower() != dono:
        print("recusado: o pedido não é deste solicitante", file=saida)
        return 2
    try:
        if not a.confirmar:
            modelo = await montar_proposta(dono, pedido, a.situacao, primeiro_nome=a.nome, db=db)
            print("ENSAIO (nada foi gravado). Para publicar, repita com --confirmar.", file=saida)
            _imprimir_modelo(modelo, saida)
            print("\n--- a mensagem (o link real sai ao publicar) ---", file=saida)
            print("\n\n[balão 2]\n".join(mensagem_whatsapp(modelo, "<o link sai ao publicar>")), file=saida)
            return 0
        r = await publicar_proposta(dono, pedido, a.situacao, primeiro_nome=a.nome, db=db)
    except (NaoEncontrado, PropostaImpossivel, LinkSemEndereco, ValueError) as exc:
        print(f"recusado: {exc}", file=saida)
        return 2
    print("PUBLICADA", file=saida)
    print(f"link: {r['url']}", file=saida)
    print(f"versão: {r['versao']} · válida até {r['validade_ate']} · artefato {r['artifact_id']}", file=saida)
    print("\n--- a mensagem (NÃO foi enviada; o envio é da 133-A) ---", file=saida)
    print("\n\n[balão 2]\n".join(r["mensagem"]), file=saida)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    try:
        return asyncio.run(executar(argv))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — o tipo, nunca a mensagem crua (pode carregar URL com chave)
        print(f"falhou: {type(exc).__name__}", file=sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())
