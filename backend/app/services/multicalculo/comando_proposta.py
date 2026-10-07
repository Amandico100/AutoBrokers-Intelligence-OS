# -*- coding: utf-8 -*-
"""O COMANDO da proposta — SPEC-130-A U7: o Founder publica a proposta de um pedido de dentro do contêiner.

    python -m app.services.multicalculo.comando_proposta --pedido <uuid do pedido>                 (ENSAIO: não grava)
    python -m app.services.multicalculo.comando_proposta --pedido <uuid do pedido> --confirmar     (publica o link)
        [--situacao novo_sem_apolice|novo_com_apolice|renovacao] [--apolice <arquivo.json>]
        [--nome <primeiro nome do cliente>] [--solicitante <uuid de quem pediu>] [--sem-whatsapp]

`--apolice` (obrigatório com `novo_com_apolice`/`renovacao` — J-B2): um JSON com a apólice atual do cliente,
`{"seguradora": "Porto", "premio_anual": 8200, "coberturas": {...}}` (a seguradora é obrigatória; o resto, quando
houver). Sem ele, essas situações são RECUSADAS: a página chamaria de "igual à sua atual" uma seguradora qualquer.
`--sem-whatsapp` (J-B1): publica mesmo sem o WhatsApp de atendimento da anfitriã — a página sai SEM "Quero fechar" e
sem nenhuma frase que prometa WhatsApp. Sem a bandeira, a publicação é recusada e o comando diz por quê.

Sem `--confirmar` o comando MONTA a proposta e imprime o que a página e a mensagem diriam, sem gravar uma linha
(decisão F3, nota 85 × publicar direto 65: o link é público e fica no banco do solicitante — ensaiar não custa nada,
desfazer custa revogar). Com `--confirmar` cria/versiona o artefato, publica e imprime a URL e os balões: a mensagem
do CANAL (≤ 3 balões) ou a da CARTEIRA (2), pela origem do pedido (SPEC-130-A.1 D-130A1-01).
⛔ Nenhuma mensagem é ENVIADA (o envio é da 133-A). ⛔ Nada de segredo na saída: nem chave, nem env, nem comissão.

O solicitante: o dono do pedido (lido de `multicalculo_pedidos` pelo id); `--solicitante` só confere. Saída 0 = ok ·
2 = recusado (pedido de outro solicitante, nada a propor, sem endereço público) · 1 = falha inesperada.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.multicalculo.comparacao import SITUACOES, precisa_de_apolice

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _argumentos(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="comando_proposta", description="Publica a proposta de um pedido do multicálculo.")
    p.add_argument("--pedido", required=True, help="o uuid do pedido (multicalculo_pedidos.id)")
    p.add_argument("--situacao", default="novo_sem_apolice", choices=SITUACOES)
    p.add_argument("--apolice", default=None,
                   help="arquivo JSON com a apólice atual (obrigatório com novo_com_apolice/renovacao)")
    p.add_argument("--nome", default=None, help="o primeiro nome do cliente (opcional)")
    p.add_argument("--solicitante", default=None, help="confere o dono do pedido (opcional)")
    p.add_argument("--sem-whatsapp", dest="sem_whatsapp", action="store_true",
                   help="publica mesmo sem o WhatsApp de atendimento da corretora (a página sai sem 'Quero fechar')")
    p.add_argument("--confirmar", action="store_true", help="publica de verdade (sem isto: só o ensaio)")
    return p.parse_args(argv)


def ler_apolice(caminho: Optional[str], situacao: str) -> Optional[Dict[str, Any]]:
    """A apólice atual do arquivo JSON (J-B2). `ValueError` com a frase do problema — o comando a imprime."""
    if not caminho:
        if precisa_de_apolice(situacao):
            raise ValueError(f"a situação {situacao} precisa da apólice atual: passe --apolice <arquivo.json> com "
                             '{"seguradora": "...", "premio_anual": ...}. Sem ela a página chamaria de "igual à sua '
                             'atual" uma seguradora que não é a do cliente')
        return None
    if not precisa_de_apolice(situacao):
        raise ValueError("--apolice só vale com --situacao novo_com_apolice ou renovacao")
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"não consegui ler a apólice em {caminho!r} ({type(exc).__name__})") from None
    if not isinstance(dados, dict) or not str(dados.get("seguradora") or "").strip():
        raise ValueError("a apólice precisa ser um objeto JSON com ao menos a \"seguradora\"")
    apolice: Dict[str, Any] = {"seguradora": str(dados["seguradora"]).strip()}
    if dados.get("premio_anual") is not None:
        try:
            premio = float(dados["premio_anual"])
        except (TypeError, ValueError):
            raise ValueError("o \"premio_anual\" da apólice precisa ser um número (ex.: 8200.50)") from None
        if premio <= 0:
            raise ValueError("o \"premio_anual\" da apólice precisa ser maior que zero")
        apolice["premio_anual"] = premio
    if isinstance(dados.get("coberturas"), dict):
        apolice["coberturas"] = dict(dados["coberturas"])
    return apolice


def dono_do_pedido(db: Any, pedido_id: str) -> Optional[str]:
    """O solicitante do pedido. Leitura de operador (service role) que devolve SÓ o company_id — a porta refaz o
    filtro de tenant em tudo o que vem depois."""
    r = db.table("multicalculo_pedidos").select("id, company_id").eq("id", pedido_id).limit(1).execute()
    linhas = list(getattr(r, "data", None) or [])
    return str(linhas[0]["company_id"]) if linhas else None


def _imprimir_modelo(modelo: dict, saida, *, sem_whatsapp: bool = False) -> None:
    r = modelo.get("resumo") or {}
    anf = modelo.get("anfitria") or {}
    print(f"anfitriã: {anf.get('nome')} · marca publicada: {'sim' if anf.get('marca_cadastrada') else 'não'} · "
          f"WhatsApp do 'Quero fechar': {'sim' if anf.get('whatsapp') else 'NÃO (o botão não aparece)'}", file=saida)
    if not anf.get("whatsapp"):
        print("  ⚠ com --confirmar a publicação é RECUSADA (o cliente não teria como fechar)"
              + (" — mas --sem-whatsapp foi passado: publica sem o botão" if sem_whatsapp else
                 ": cadastre o WhatsApp de atendimento da corretora, ou repita com --sem-whatsapp"), file=saida)
    if precisa_de_apolice(str(modelo.get("situacao") or "")) and not any(
            o.get("id") in ("igual_a_atual", "sua_renovacao") for o in modelo.get("opcoes") or []):
        print("  ⚠ a seguradora da apólice não está entre as que deram preço completo: a página sai SEM a opção "
              "\"igual à sua atual\"", file=saida)
    print(f"seguradoras: {r.get('seguradoras_cotadas')} cotadas · {r.get('com_preco_comparavel')} completas · "
          f"{r.get('com_produto_diferente')} só com produto diferente · {r.get('nao_responderam')} sem resposta"
          + (f" · {r['corretoras_comparadas']} corretoras comparadas" if r.get("corretoras_comparadas") else ""),
          file=saida)
    for o in modelo.get("opcoes") or []:
        print(f"  {o['rotulo']}: {o['seguradora']} · R$ {o['premio_anual']:,.2f} por ano · nota {o['nota']}"
              .replace(",", "§").replace(".", ",").replace("§", "."), file=saida)
    print(f"válida até {modelo.get('validade_ate')}", file=saida)


def _qual(modelo: dict) -> str:
    """SPEC-130-A.1 D-130A1-01: a mensagem sai pela ORIGEM do pedido — o comando diz qual."""
    return "do CANAL" if str(modelo.get("origem") or "") == "canal" else "da CARTEIRA"


def _baloes(baloes: List[str]) -> str:
    return "\n\n".join(f"[balão {i}]\n{b}" for i, b in enumerate(baloes, 1))


async def executar(argv: Optional[List[str]] = None, *, db: Any = None, saida=None) -> int:
    from app.services.multicalculo.mensagem import mensagem_para
    from app.services.multicalculo.porta import NaoEncontrado
    from app.services.multicalculo.proposta import (LinkSemEndereco, PropostaImpossivel, SemCanalDeFechamento,
                                                    montar_proposta, publicar_proposta)

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
        apolice = ler_apolice(a.apolice, a.situacao)
        if not a.confirmar:
            ctx: Dict[str, Any] = {}
            modelo = await montar_proposta(dono, pedido, a.situacao, apolice, primeiro_nome=a.nome, db=db,
                                           _contexto=ctx)
            print("ENSAIO (nada foi gravado). Para publicar, repita com --confirmar.", file=saida)
            _imprimir_modelo(modelo, saida, sem_whatsapp=a.sem_whatsapp)
            print(f"\n--- a mensagem {_qual(modelo)} (o link real sai ao publicar) ---", file=saida)
            print(_baloes(mensagem_para(modelo, "<o link sai ao publicar>", config=ctx.get("cfg_sol"))), file=saida)
            return 0
        r = await publicar_proposta(dono, pedido, a.situacao, apolice, primeiro_nome=a.nome, db=db,
                                    permitir_sem_whatsapp=a.sem_whatsapp)
    except (NaoEncontrado, PropostaImpossivel, LinkSemEndereco, SemCanalDeFechamento, ValueError) as exc:
        print(f"recusado: {exc}", file=saida)
        return 2
    print("PUBLICADA", file=saida)
    print(f"link: {r['url']}", file=saida)
    print(f"versão: {r['versao']} · válida até {r['validade_ate']} · artefato {r['artifact_id']}", file=saida)
    print("\n--- a mensagem (NÃO foi enviada; o envio é da 133-A) ---", file=saida)
    print(_baloes(r["mensagem"]), file=saida)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    try:                                   # P5 (juiz): no console do Windows o "ç" virava 'charmap' codec e exit 2
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        return asyncio.run(executar(argv))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — o tipo, nunca a mensagem crua (pode carregar URL com chave)
        print(f"falhou: {type(exc).__name__}", file=sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(main())
