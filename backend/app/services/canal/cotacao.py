# -*- coding: utf-8 -*-
"""A COTAÇÃO do canal — SPEC-133-A U6 (D-133A-03 · D-133A-11 · D-130A1-06).

    disparar(db, company_id, telefone_e164, perfil, estado) → run_id do Work Run `canal.cotacao`

O perfil da conversa vira `PedidoDeCalculo` e vai à PORTA REAL (`MulticalculoProvider.calcular`) com
`origem='canal'`, as corretoras = as adesões ATIVAS do canal (lidas aqui, com o filtro do canal) e
`opcoes = OPCOES_DO_CANAL`. A porta enfileira; o motor do portal-worker calcula as corretoras em PARALELO (D-133A-11).
Quem acompanha, publica, manda a mensagem e os lembretes é o Work Run `canal.cotacao` (`canal/workflows.py`) — Work OS
(`runs.criar` · `registrar_workflow` · `dormir`), nunca um scheduler novo.

🔴 O `input_payload` do run vai EM CLARO para `work_runs`: ele leva só o `pedido_id` e um `contato` CIFRADO
(`portal_vault`, o mesmo cofre do `pedido_cifrado`) com telefone, primeiro nome e o prêmio declarado.
🔴 Depois do disparo o estado da conversa PERDE as respostas (CPF, nome, nascimento…): a cotação seguinte pergunta de
novo (P-E0017-14: estado por cotação, não memória herdada).

Também moram aqui os efeitos que a conversa pede: `cancelar_lembretes` (G8), `passar_para_corretora` (a passagem) e
`pedir_ajuda_humana` (fora do escopo).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Mapping, Optional

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "canal.cotacao"
OUTCOME_TYPE = "canal.cotacao"
SITUACAO = "novo_sem_apolice"     # o canal não leu apólice (a leitura é da 130-B)

FRASE_SEM_COMECAR = ("Não consegui começar a cotação agora — o problema é do nosso lado, não dos seus dados. "
                     "Já anotei aqui; se quiser tentar de novo mais tarde, é só escrever *nova cotação*.")


def _cliente(db: Any) -> Any:
    return getattr(db, "client", db)


def _dados(resp: Any) -> List[Dict[str, Any]]:
    return list(getattr(resp, "data", None) or [])


# ---------------------------------------------------------------------------------------------------------------------
# a leitura das adesões e o cofre
# ---------------------------------------------------------------------------------------------------------------------
def adesoes_ativas_do_canal(db: Any, canal_company_id: str) -> List[str]:
    """As corretoras com adesão ATIVA a ESTE canal (🔴 filtro `canal_company_id` aqui — CLAUDE.md §7). A porta
    reconfere a adesão antes de gravar (D-129B-05); esta lista só diz QUAIS pedir."""
    linhas = _dados(_cliente(db).table("multicalculo_adesoes").select("corretora_company_id, ativa, criada_em")
                    .eq("canal_company_id", str(canal_company_id)).eq("ativa", True).execute())
    vistos: List[str] = []
    for l in sorted(linhas, key=lambda x: str(x.get("criada_em") or "")):
        c = str(l.get("corretora_company_id") or "")
        if c and l.get("ativa") is True and c not in vistos:
            vistos.append(c)
    return vistos


def cifrar_contato(contato: Mapping[str, Any]) -> str:
    from app.services import portal_vault

    return portal_vault.encrypt(json.dumps(dict(contato), ensure_ascii=False))


def decifrar_contato(token: str) -> Dict[str, Any]:
    from app.services import portal_vault

    return json.loads(portal_vault.decrypt(token))


def nome_do_canal(db: Any, company_id: str) -> str:
    """O nome do canal DA CONFIG (`canal.nome`, D-MC-55) — o mesmo que a conversa usa. Config ilegível → o padrão do
    produto (`conversa.NOME_PADRAO_DO_CANAL`): um aviso nunca deixa de sair por causa do nome."""
    from app.services.canal.conversa import _nome_do_canal
    from app.services.multicalculo import config as CFG

    try:
        return _nome_do_canal(CFG.carregar(company_id, db=_cliente(db)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] config ilegível para o nome do canal (%s) — fica o padrão", type(exc).__name__)
        return _nome_do_canal(None)


def _porta(db: Any) -> Any:
    from app.services.multicalculo.porta import MulticalculoProvider
    from app.services.multicalculo.repositorio import RepositorioMulticalculo

    return MulticalculoProvider(RepositorioMulticalculo(_cliente(db)))


# ---------------------------------------------------------------------------------------------------------------------
# disparar
# ---------------------------------------------------------------------------------------------------------------------
async def disparar(db: Any, company_id: str, telefone_e164: str, perfil: dict, estado: dict) -> str:
    """O pedido à porta + o Work Run. Devolve o `run_id` ("" quando não conseguiu começar — a pessoa é avisada)."""
    from app.services.canal import envio, repositorio
    from app.services.multicalculo.pedido import PedidoDeCalculo
    from app.services.multicalculo.porta import OPCOES_DO_CANAL
    from app.services.work.runs import WorkRunService

    estado = dict(estado or {})
    try:
        corretoras = await asyncio.to_thread(adesoes_ativas_do_canal, db, company_id)
        if not corretoras:
            raise LookupError("o canal não tem adesão ativa com nenhuma corretora")
        pedido = PedidoDeCalculo.de_dict(perfil["pedido"], assumidos=perfil.get("assumidos") or ())
        aberto = await _porta(db).calcular(company_id=company_id, pedido=pedido, corretoras=corretoras,
                                           opcoes=OPCOES_DO_CANAL, origem="canal")
    except Exception as exc:  # noqa: BLE001 — nomes de campo e o tipo; nunca valores
        campos = ", ".join(getattr(exc, "campos", []) or [])
        logger.error("[CANAL] a cotação não começou: %s %s", type(exc).__name__, campos)
        estado.update({"etapa": "falhou", "falha": type(exc).__name__})
        estado.pop("respostas", None)
        await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone_e164, estado)
        saiu = await envio.enviar(db, company_id, telefone_e164, [FRASE_SEM_COMECAR])
        if saiu:   # conserto 8: o aviso de falha é mensagem nossa — conta no teto do dia
            await asyncio.to_thread(repositorio.contar_enviadas, db, company_id, telefone_e164, saiu)
        return ""

    contato = cifrar_contato({"telefone": telefone_e164, "primeiro_nome": perfil.get("primeiro_nome"),
                              "premio_atual_declarado": perfil.get("premio_atual_declarado")})
    linha = await asyncio.to_thread(
        WorkRunService(_cliente(db)).criar, company_id=company_id, source_type="chat", outcome_type=OUTCOME_TYPE,
        outcome_title=f"Cotação do {await asyncio.to_thread(nome_do_canal, db, company_id)} pelo WhatsApp",
        workflow_key=WORKFLOW_KEY,
        idempotency_key=f"{WORKFLOW_KEY}:{aberto.pedido_id}",
        input_payload={"pedido_id": aberto.pedido_id, "contato": contato},
        source_id=aberto.pedido_id, priority=10, risk_level="high")
    run_id = str((linha or {}).get("run_id") or "")
    await asyncio.to_thread(repositorio.registrar_lead, db, company_id, telefone_e164,
                            primeiro_nome=perfil.get("primeiro_nome"), pedido_id=aberto.pedido_id)
    estado.pop("respostas", None)                      # 🔴 o CPF e o resto não ficam depois do disparo
    estado.pop("tentativas", None)
    estado.update({"etapa": "calculando", "pedido_id": aberto.pedido_id, "run_id": run_id,
                   "resultado": None, "respondeu_em": None})
    await asyncio.to_thread(repositorio.salvar_estado, db, company_id, telefone_e164, estado)
    logger.info("[CANAL] cotação disparada: %s corretora(s), run %s", len(corretoras), run_id[:8])
    return run_id


# ---------------------------------------------------------------------------------------------------------------------
# G8 — a resposta da pessoa cancela os lembretes
# ---------------------------------------------------------------------------------------------------------------------
def cancelar_lembretes(db: Any, company_id: str, estado: Mapping[str, Any]) -> bool:
    """Pede o cancelamento do run que dorme até o próximo lembrete. Best-effort: o run TAMBÉM relê o estado antes de
    cada lembrete (`respondeu_em`), então um cancelamento perdido não deixa lembrete sair."""
    run_id = str((estado or {}).get("run_id") or "")
    if not run_id:
        return False
    try:
        from app.services.work.runs import WorkRunService

        return WorkRunService(_cliente(db)).solicitar_cancelamento(run_id, company_id) in ("cancelled", "cancelling")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] cancelar os lembretes falhou (%s) — o estado segura", type(exc).__name__)
        return False


# ---------------------------------------------------------------------------------------------------------------------
# a passagem à corretora vencedora · a ajuda humana
# ---------------------------------------------------------------------------------------------------------------------
async def _avisar(db: Any, company_id: str, texto: str, rotulo: str) -> bool:
    """O caminho de aviso humano que JÁ existe (`billing_collection.avisar_suporte_humano` → o grupo de suporte da
    corretora pelo resolvedor único). Nunca levanta."""
    try:
        from app.services.billing_collection import avisar_suporte_humano

        return bool(await avisar_suporte_humano(_cliente(db), company_id, texto, rotulo))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] aviso humano falhou (%s)", type(exc).__name__)
        return False


#: o evento durável da passagem (Work OS): a caixa do operador (`control_plane.inbox`) o lê — ver `registrar_passagem`
EVENTO_QUER_FECHAR = "canal.quer_fechar"


def registrar_passagem(db: Any, company_id: str, estado: Mapping[str, Any], *, telefone_e164: str, avisou: bool
                       ) -> bool:
    """SPEC-133-A costura (item 6) — a passagem fica ESCRITA no Work Run do canal, SEMPRE (avisando ou não o grupo).

    📊 07/10 (SELECT no banco do produto): as 3 integrações ativas são `observer`; das 2 corretoras aderidas ao canal,
    NENHUMA tem destino ativo em `human_support_destinations` e só 1 autorizou o observador para trabalho de Auxiliar
    — o `avisar_suporte_humano` (o caminho do grupo) hoje não entrega a nenhuma das duas, e nenhuma tem `contact.whatsapp`
    na marca publicada. Sem este registro, o "quero fechar" morreria num log. O evento é do CANAL (quem consentiu levar
    o contato foi a pessoa ao canal; nada é escrito na corretora) e aparece na caixa do operador da plataforma
    (`control_plane.inbox._canal_quer_fechar`), que passa o lead (`canal_leads`) à vencedora.
    ⛔ Sem o telefone inteiro no evento (só os 4 últimos): o número mora cifrado no estado e em `canal_leads`."""
    run_id = str((estado or {}).get("run_id") or "")
    if not run_id:
        return False
    from app.services.canal import repositorio
    from app.services.work.runs import WorkRunService

    res = dict((estado or {}).get("resultado") or {})
    quem = str(res.get("anfitria_nome") or "a corretora vencedora")
    nome = (estado or {}).get("primeiro_nome") or "Uma pessoa"
    try:
        WorkRunService(_cliente(db)).evento(
            company_id, run_id, EVENTO_QUER_FECHAR,
            (f"{nome} quer fechar com {quem}. "
             + ("O grupo da corretora foi avisado." if avisou else
                "A corretora NÃO foi avisada automaticamente (sem grupo de suporte): passe o contato a ela.")),
            severity="info" if avisou else "warning",
            payload={"anfitria_company_id": str(res.get("anfitria_id") or ""),
                     "pedido_id": str((estado or {}).get("pedido_id") or ""),
                     "telefone_final": repositorio.mascarar(telefone_e164), "avisou_o_grupo": bool(avisou),
                     "proposta_url": res.get("url")})
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CANAL] passagem não registrada no run (%s)", type(exc).__name__)
        return False


async def passar_para_corretora(db: Any, company_id: str, telefone_e164: str, estado: Mapping[str, Any]
                                ) -> List[str]:
    """"Quero fechar" → avisa a VENCEDORA (resumo + link + o telefone, que a pessoa consentiu levar às corretoras) e
    diz à pessoa quem vai falar com ela. Sem aviso possível, dá o WhatsApp da corretora — nunca promete o que não fez."""
    from app.services.canal import repositorio

    res = dict((estado or {}).get("resultado") or {})
    anfitria = str(res.get("anfitria_id") or "")
    quem = str(res.get("anfitria_nome") or "a corretora")
    nome = (estado or {}).get("primeiro_nome") or "Um cliente"
    canal = await asyncio.to_thread(nome_do_canal, db, company_id)
    texto = (f"🟢 {canal} — {nome} quer FECHAR o seguro do carro com vocês.\n"
             f"WhatsApp: {telefone_e164}\nProposta: {res.get('url') or '(sem link)'}\n"
             "Fale com a pessoa por esse número — ela já viu o preço e respondeu que quer fechar.")
    avisou = await _avisar(db, anfitria, texto, "canal: quer fechar") if anfitria else False
    await asyncio.to_thread(repositorio.registrar_lead, db, company_id, telefone_e164,
                            primeiro_nome=(estado or {}).get("primeiro_nome"), pedido_id=(estado or {}).get("pedido_id"))
    await asyncio.to_thread(registrar_passagem, db, company_id, estado, telefone_e164=telefone_e164, avisou=avisou)
    if avisou:
        return [f"Ótimo! Avisei a {quem}. Alguém de lá vai falar com você por aqui no WhatsApp."]
    whats = str(res.get("whatsapp") or "")
    if whats:
        return [f"Ótimo! Pra fechar, fale com a {quem} por aqui: https://wa.me/{whats}"]
    logger.warning("[CANAL] passagem sem aviso e sem WhatsApp da corretora — fica o lead")
    return [f"Ótimo! Anotei que você quer fechar com a {quem}. Ainda não consegui avisar a corretora "
            "automaticamente — assim que alguém de lá estiver disponível, fala com você por aqui."]


async def pedir_ajuda_humana(db: Any, company_id: str, telefone_e164: str, estado: Mapping[str, Any], *,
                             motivo: str) -> bool:
    """Fora do escopo antes do resultado: avisa o suporte do PRÓPRIO canal (sem CPF — só o motivo e o contato)."""
    nome = (estado or {}).get("primeiro_nome") or "Uma pessoa"
    canal = await asyncio.to_thread(nome_do_canal, db, company_id)
    texto = f"{canal} — {nome} pediu para falar com alguém ({motivo}).\nWhatsApp: {telefone_e164}"
    return await _avisar(db, company_id, texto, f"canal: {motivo}"[:60])
