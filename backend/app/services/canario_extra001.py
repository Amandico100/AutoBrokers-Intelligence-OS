# -*- coding: utf-8 -*-
"""O canário vivo da SPEC-EXTRA-001 — a cobrança chega a quem deve, medido no ar.

Por que isto é um MÓDULO do serviço, e não só um script
=======================================================
📊 07/09/2026: toda mensagem FRIA passa pelo governador (`platform_outbound.
governar_envio`), e sem Redis ele recusa — falha fechada, e é assim que tem de
ser. Nesta máquina não há Redis; no contêiner implantado há. Então o canário
vivo roda ONDE o produto roda: `backend/scripts/canario_extra001.py` imprime o
plano localmente (`--dry-run`), e a rota admin `POST /api/admin/canario/extra001`
(chave interna) executa `rodar(...)` dentro do smith-api implantado.

⛔ Nunca relaxa um controle para testar: o governador, a porta única, a
allowlist, a reserva — tudo o que vale para a corretora vale aqui.

O que ele mede
==============
```
Q1  EQUIPE    rotina canário (config.canario=True, send_mode='equipe',
              team_number=TESTE-B) · item SINTÉTICO · PDF sintético sem
              validade financeira → 3 mensagens chegam em TESTE-B (nota
              interna, texto limpo, PDF); ledger `entregue_equipe`, canario=true.
              O aviso ao grupo real da corretora é SUPRIMIDO.
Q2  CLIENTE   a mesma parcela em `cliente` (whatsapp=TESTE-B) → 0 envios
              (G11: entregue à equipe, sem "encaminhado"); depois `liberado`
              com motivo → texto + PDF chegam.
Q3  REEXECUÇÃO a mesma parcela de novo → 0 envios, "já cobrado".
Q4  RETORNO   `registrar_retorno(TESTE-B, "já paguei")` pelo caminho de U2 →
              ledger `contestado` + linha em agent_activities. (A resposta
              REAL de TESTE-B pelo webhook só é medível depois do Implantar:
              `--esperar-retorno` olha o ledger por N segundos.)
Q5  ALLOWLIST rotina com team_number FORA da allowlist → a porta recusa
              (`fora_da_allowlist`), 0 envios, incidente.
Q6  LIMPEZA   ledger (por id + company + canario), platform_sends do canário,
              atividades do canário, o PDF do cofre. VERIFY 0/0/0.

SPEC-EXTRA-001.6 (proposta §10.2) — acrescentados em 14/09/2026:
Q7  GRUPO     2 itens sintéticos com o MESMO documento e o mesmo portal →
              1 nota + 1 texto + 2 PDFs em TESTE-B (platform_sends: billing 1 ·
              billing_nota 1 · billing_doc 2); nada picotado (bloco único).
Q8  REPETE    a mesma execução de novo no mesmo dia → 0 envios.
Q9  JANELA    3º item, mesmo documento, OUTRA seguradora → retido pela regra de
              N dias, com motivo, data e a origem da identidade.
Q10 LOGIN     `portais=True`: o canário de login (`_canario_de_login`) roda nos 4
              portais com senha válida (Tokio, HDI, Yelum, Zurich) e o motivo de
              quem não entrou sai em português. Allianz/Mapfre esperam a senha
              de 15/09 (D-PILOTO-19).
```

⛔ Nunca imprime telefone, nome ou id inteiro: só aliases, últimos 4 e
prefixos de 8 caracteres. ⛔ Só roda com `BILLING_CANARIO_ALLOWLIST` com ≥ 2
entradas e o destino (`CANARIO_TESTE_B`) dentro dela — os valores reais vivem
no ambiente, nunca aqui.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: 📊 `select id from companies where company_name='Resulta Seguros'` (07/09/2026)
RESULTA = "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"
MARCA = "CANARIO-EXTRA001"
#: ⛔ Um número que não é de ninguém — o "fora da allowlist" do Q5.
FORA_DA_ALLOWLIST = "5500900000001"

PDF_SINTETICO = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 400 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 120>>stream\nBT /F1 18 Tf 20 120 Td (DOCUMENTO DE TESTE - SEM VALIDADE) Tj "
    b"0 -30 Td (AutoBrokers - canario EXTRA-001) Tj 0 -30 Td (nao pagar, nao e boleto) Tj ET\nendstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
)


def _mask(v: Any, n: int = 4) -> str:
    s = str(v or "")
    return f"...{s[-n:]}" if s else "?"


def _pref(v: Any) -> str:
    return str(v or "")[:8]


def _digits(v: Any) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


class Relato:
    """Linhas do canário, sem PII, e o veredito por pergunta."""

    def __init__(self) -> None:
        self.linhas: List[str] = []
        self.perguntas: Dict[str, str] = {}

    def p(self, texto: str) -> None:
        self.linhas.append(texto)
        logger.info("[CANARIO EXTRA-001] %s", texto)

    def veredito(self, q: str, ok: bool, detalhe: str = "") -> None:
        self.perguntas[q] = ("OK" if ok else "FALHOU") + (f" — {detalhe}" if detalhe else "")
        self.p(f"{q}: {'✅' if ok else '❌'} {detalhe}")

    def como_dict(self) -> Dict[str, Any]:
        return {"perguntas": self.perguntas, "linhas": self.linhas}


def _allowlist() -> set:
    from app.services.platform_outbound import _allowlist_do_canario

    return set(_allowlist_do_canario())


def plano(company_id: str = RESULTA) -> Dict[str, Any]:
    """`--dry-run`: o que o canário FARIA, com o censo — sem tocar em nada."""
    from app.core.database import get_supabase_client
    from app.services.billing_collection import _find_whatsapp_integration

    r = Relato()
    allow = _allowlist()
    destino = _digits(os.getenv("CANARIO_TESTE_B", ""))
    r.p(f"allowlist do canário: {len(allow)} entrada(s) (BILLING_CANARIO_ALLOWLIST)")
    r.p(f"destino TESTE-B configurado: {'sim' if destino else 'NÃO'} ({_mask(destino)})")
    db = get_supabase_client().client
    integ = _find_whatsapp_integration(db, company_id)
    if integ:
        r.p(f"conexão autorizada como Auxiliar: {_pref(integ.get('id'))}… purpose={integ.get('purpose')} "
            f"status={integ.get('channel_status')} remetente={_mask(integ.get('paired_phone_e164'))}")
    else:
        r.p("conexão autorizada como Auxiliar: NENHUMA — o canário não sairia")
    from app.services.platform_outbound import _autorizado_no_canario

    r.p(f"remetente na allowlist: {bool(integ) and _autorizado_no_canario(integ.get('paired_phone_e164'), allow)}")
    r.p(f"destino na allowlist: {bool(destino) and _autorizado_no_canario(destino, allow)}")
    r.p("plano: Q1 equipe → Q2 cliente (0, depois liberado) → Q3 reexecução (0) → Q4 retorno (U2) → "
        "Q5 fora da allowlist (recusa) → Q6 limpeza 0/0/0")
    return r.como_dict()


def _rotina(company_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": str(uuid.uuid4()), "company_id": company_id, "name": f"{MARCA} (rotina sintética, não persistida)",
            "config": cfg, "delivery": {}}


def _cfg(modalidade: str, *, destino: str, team_number: Optional[str] = None) -> Dict[str, Any]:
    from app.services.billing_collection import normalize_billing_config

    return normalize_billing_config({
        "kind": "billing_collection", "send_mode": modalidade,
        "team_number": team_number or "", "confirmacao_cliente": True, "canario": True,
        "portal_keys": ["allianz_corretor"], "brokerage_name": "Resulta Seguros (teste)",
        "attendant_name": "equipe de teste", "insurer_name": "ALLIANZ",
    })


def _item(recibo: str, destino: str, nome: str = "Cliente Canário") -> Dict[str, Any]:
    """Uma parcela sintética. 🔴 O `nome` é a IDENTIDADE, e cada Q tem a sua.

    ⚠️ 14/09/2026 (B2) — sem documento, `segurado_chave` cai no NOME. Todos os Q
    usavam "Cliente Canário" e `cpf_cnpj=""`, ou seja: **um único segurado**. A
    JANELA DE 7 DIAS, que roda ANTES da allowlist, retinha o Q5 por causa do Q1 —
    e o Q5 (que existe para provar que a PORTA recusa um número fora da
    allowlist) passava verde pelo motivo errado, sem a porta ter sido chamada. O
    mesmo valia para Q2a e Q3: eles afirmam medir a RESERVA por recibo, e quem os
    segurava era a janela por segurado.

    🔴 A regra: **cada Q afirma UMA coisa, e o que o segura tem de ser a coisa
    que ele afirma.** Q2a/Q2b/Q3 mantêm o recibo do Q1 de propósito (é a reserva
    que eles medem) e ganham nome próprio para a janela não entrar na frente;
    Q5 e Q7/Q9 têm identidade inteiramente própria.
    """
    return {
        "portal": "allianz_corretor", "recibo": recibo, "cliente_nome": nome,
        "cpf_cnpj": "", "whatsapp": destino, "contact_status": "found",
        "apolice_susep": f"{MARCA}-APOLICE", "vencimento": "2026-08-01", "valor": 0.0,
        "parcela": "1/1", "item_segurado": "veículo de teste (sem validade)",
    }


async def rodar(company_id: str = RESULTA, *, limpar: bool = True,
                esperar_retorno_s: int = 0, portais: bool = False) -> Dict[str, Any]:
    """O canário VIVO. Só roda onde há Redis e com a allowlist configurada."""
    from app.core.database import get_supabase_client
    from app.services import billing_collection as BC
    from app.services.platform_outbound import _autorizado_no_canario

    r = Relato()
    allow = _allowlist()
    destino = _digits(os.getenv("CANARIO_TESTE_B", ""))
    if len(allow) < 2 or not destino or not _autorizado_no_canario(destino, allow):
        r.veredito("Q0", False, "allowlist com menos de 2 entradas ou destino fora dela — nada roda")
        return r.como_dict()
    # 🔴 `AUTOBROKERS_CANARIO` marca toda peça publicada como canário (artifacts/
    #    service.py::e_canario lê o env EM TEMPO DE CHAMADA). Esta função roda
    #    dentro do smith-api, que não morre ao fim — deixar a variável ligada
    #    marcaria as peças de TODAS as corretoras até o próximo restart (painel
    #    07/09, lente verdade B1). Liga só durante a corrida, e restaura sempre.
    _tinha = os.environ.get("AUTOBROKERS_CANARIO")
    os.environ["AUTOBROKERS_CANARIO"] = "1"
    try:
        return await _rodar_marcado(company_id, limpar=limpar, esperar_retorno_s=esperar_retorno_s,
                                    r=r, allow=allow, destino=destino, portais=portais)
    finally:
        if _tinha is None:
            os.environ.pop("AUTOBROKERS_CANARIO", None)
        else:
            os.environ["AUTOBROKERS_CANARIO"] = _tinha


async def _rodar_marcado(company_id: str, *, limpar: bool, esperar_retorno_s: int,
                         r: Relato, allow: set, destino: str, portais: bool = False) -> Dict[str, Any]:
    from app.core.database import get_supabase_client
    from app.services import billing_collection as BC

    db = get_supabase_client().client
    inicio = datetime.now(timezone.utc)
    recibo = f"{MARCA}-{int(time.time())}"
    caminho = f"canario/extra001/{recibo}.pdf"
    ledger_ids: List[str] = []

    try:
        # O documento sintético entra no cofre da corretora, marcado pelo caminho.
        await asyncio.to_thread(
            lambda: db.storage.from_(BC.PORTAL_EVIDENCE_BUCKET).upload(
                caminho, PDF_SINTETICO, {"content-type": "application/pdf"}))
        r.p(f"PDF sintético no cofre: {caminho}")
        boleto = {"recibo": recibo, "ok": True, "storage_path": caminho}
        # 🔴 B2 — IDENTIDADES SEPARADAS. Sem documento, quem identifica o segurado
        # é o NOME, e a janela de 7 dias roda ANTES de tudo. Ver `_item`.
        item = _item(recibo, destino, nome="Cliente Canário Q1")
        # ⚠️ MESMO recibo do Q1, de propósito: o que tem de segurar Q2a e Q3 é a
        # RESERVA por recibo — que é o que eles afirmam medir.
        item_q2 = _item(recibo, destino, nome="Cliente Canário Q2")

        async def executar(modalidade: str, team_number: Optional[str] = None,
                           itens: Optional[List[Dict[str, Any]]] = None,
                           boletos: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
            cfg = _cfg(modalidade, destino=destino, team_number=team_number)
            blockers: List[str] = []
            entregas = await BC._entregar_cobranca_real(
                db, _rotina(company_id, cfg), list(itens or [item]), list(boletos or [boleto]),
                cfg, blockers, work_run_id=None)
            for e in entregas:
                if e.get("ledger_id") and e["ledger_id"] not in ledger_ids:
                    ledger_ids.append(str(e["ledger_id"]))
            return {"entregas": entregas, "blockers": blockers}

        def ledger() -> Optional[Dict[str, Any]]:
            res = (db.table("billing_sent_log").select("*").eq("company_id", company_id)
                   .eq("send_mode", "real").eq("recibo", recibo).limit(1).execute())
            return (res.data or [None])[0]

        # Q1 — EQUIPE
        q1 = await executar("equipe", team_number=destino)
        l1 = ledger() or {}
        r.p(f"Q1 entregas={[(e.get('status'), e.get('ok'), e.get('doc_ok')) for e in q1['entregas']]} "
            f"blockers={q1['blockers'][:4]}")
        r.veredito("Q1", l1.get("status") == "entregue_equipe" and l1.get("canario") is True
                   and l1.get("text_ok") is True and l1.get("doc_ok") is True,
                   f"ledger status={l1.get('status')} to={_mask(l1.get('to_last4'))} modalidade={l1.get('modalidade')}")

        # Q2 — CLIENTE sem liberar: 0 envios
        q2a = await executar("cliente", itens=[item_q2])
        l2a = ledger() or {}
        r.veredito("Q2a", not any(e.get("ok") for e in q2a["entregas"]) and l2a.get("status") == "entregue_equipe",
                   f"0 envios; ledger continua {l2a.get('status')}; motivo={[e.get('motivo') for e in q2a['entregas']]}")
        # ... e depois de LIBERAR com motivo: texto + PDF
        if l2a.get("id"):
            await asyncio.to_thread(BC._marcar_estado, db, company_id, str(l2a["id"]),
                                    status="liberado", motivo="canário EXTRA-001: liberação de teste")
        q2b = await executar("cliente", itens=[item_q2])
        l2b = ledger() or {}
        r.veredito("Q2b", any(e.get("ok") for e in q2b["entregas"]) and l2b.get("doc_ok") is True
                   and l2b.get("modalidade") == "cliente",
                   f"ledger status={l2b.get('status')} modalidade={l2b.get('modalidade')} attempts={l2b.get('attempts')}")

        # Q3 — REEXECUÇÃO: 0 envios
        q3 = await executar("cliente", itens=[item_q2])
        l3 = ledger() or {}
        r.veredito("Q3", not any(e.get("ok") for e in q3["entregas"]) and l3.get("attempts") == l2b.get("attempts"),
                   f"0 envios; attempts={l3.get('attempts')}; blockers={q3['blockers'][:2]}")

        # Q4 — RETORNO pelo caminho de U2 (simulado) e, se pedido, o real pelo webhook
        try:
            from app.services.billing_replies import registrar_retorno

            ret = await registrar_retorno(company_id, destino, "já paguei ontem, pode conferir")
            l4 = ledger() or {}
            r.veredito("Q4", bool(ret) and l4.get("retorno_do_cliente") == "ja_paguei"
                       and l4.get("status") == "contestado",
                       f"retorno={l4.get('retorno_do_cliente')} status={l4.get('status')}")
        except Exception as exc:  # noqa: BLE001
            r.veredito("Q4", False, f"billing_replies indisponível ({type(exc).__name__})")
        if esperar_retorno_s > 0:
            r.p(f"Q4-vivo: esperando até {esperar_retorno_s}s por uma resposta REAL de TESTE-B pelo webhook…")
            fim = time.time() + esperar_retorno_s
            visto = None
            while time.time() < fim:
                l = ledger() or {}
                if l.get("retorno_em") and str(l.get("retorno_em")) > (l4.get("retorno_em") or ""):
                    visto = l
                    break
                await asyncio.sleep(5)
            r.veredito("Q4-vivo", bool(visto), f"retorno={(visto or {}).get('retorno_do_cliente')}" if visto else "sem resposta no prazo")

        # Q5 — FORA DA ALLOWLIST: a porta recusa
        # 🔴 B2 — identidade PRÓPRIA: o que tem de recusar o Q5 é a ALLOWLIST da
        # porta, não a janela de 7 dias aberta pelo Q1.
        item_q5 = _item(f"{recibo}-Q5", destino, nome="Cliente Canário Q5")
        boleto_q5 = {"recibo": item_q5["recibo"], "ok": True, "storage_path": caminho}
        cfg5 = _cfg("equipe", destino=destino, team_number=FORA_DA_ALLOWLIST)
        blockers5: List[str] = []
        e5 = await BC._entregar_cobranca_real(db, _rotina(company_id, cfg5), [item_q5], [boleto_q5], cfg5,
                                              blockers5, work_run_id=None)
        for e in e5:
            if e.get("ledger_id"):
                ledger_ids.append(str(e["ledger_id"]))
        r.veredito("Q5", not any(e.get("ok") for e in e5) and any("fora_da_allowlist" in str(e.get("motivo")) for e in e5),
                   f"motivos={[e.get('motivo') for e in e5]}")

        # ------------------------------------------------------------------
        # SPEC-EXTRA-001.6 — Q7..Q10 (proposta §10.2). Documentos SINTÉTICOS.
        # ------------------------------------------------------------------
        # Q7 — UM SEGURADO, N BOLETOS: 1 nota + 1 texto + 2 PDFs, nada picotado.
        doc_q7 = "00000000000191"   # ⛔ sintético: 14 dígitos, CNPJ inválido de propósito
        i7a = {**_item(f"{recibo}-Q7A", destino, nome="Cliente Canário Q7"),
               "cpf_cnpj": doc_q7, "parcela": "1/2", "numero_parcela": "1/2"}
        i7b = {**_item(f"{recibo}-Q7B", destino, nome="Cliente Canário Q7"),
               "cpf_cnpj": doc_q7, "parcela": "2/2", "numero_parcela": "2/2"}
        b7 = [{"recibo": i["recibo"], "ok": True, "storage_path": caminho} for i in (i7a, i7b)]
        antes_q7 = datetime.now(timezone.utc)
        q7 = await executar("equipe", team_number=destino, itens=[i7a, i7b], boletos=b7)

        def _kinds_desde(marco: datetime) -> List[str]:
            res = (db.table("platform_sends").select("kind").eq("company_id", company_id)
                   .eq("phone", destino).gte("sent_at", marco.isoformat()).execute())
            return [str((x or {}).get("kind") or "") for x in (res.data or [])]

        kinds7 = await asyncio.to_thread(_kinds_desde, antes_q7)
        oks7 = [e for e in q7["entregas"] if e.get("ok")]
        r.p(f"Q7 entregas={[(e.get('status'), e.get('ok'), e.get('doc_ok')) for e in q7['entregas']]} "
            f"platform_sends={sorted(kinds7)} blockers={q7['blockers'][:3]}")
        r.veredito("Q7", len(oks7) == 2 and kinds7.count("billing") == 1
                   and kinds7.count("billing_nota") == 1 and kinds7.count("billing_doc") == 2,
                   f"2 parcelas do mesmo documento → {kinds7.count('billing')} texto · "
                   f"{kinds7.count('billing_nota')} nota · {kinds7.count('billing_doc')} PDF(s)")

        # Q8 — SEGUNDA EXECUÇÃO no mesmo dia: ZERO envios (janela por segurado + reserva por parcela).
        antes_q8 = datetime.now(timezone.utc)
        q8 = await executar("equipe", team_number=destino, itens=[i7a, i7b], boletos=b7)
        kinds8 = await asyncio.to_thread(_kinds_desde, antes_q8)
        r.veredito("Q8", not any(e.get("ok") for e in q8["entregas"]) and not kinds8,
                   f"0 envios; estados={[e.get('status') for e in q8['entregas']]}; "
                   f"motivo={str((q8['entregas'] or [{}])[0].get('motivo'))[:120]}")

        # Q9 — O MESMO SEGURADO NA OUTRA SEGURADORA: retido pela janela de N dias, com motivo e data.
        i9 = {**_item(f"{recibo}-Q9", destino, nome="Cliente Canário Q7"),
              "cpf_cnpj": doc_q7, "portal": "hdi_corretor"}
        b9 = [{"recibo": i9["recibo"], "ok": True, "storage_path": caminho}]
        antes_q9 = datetime.now(timezone.utc)
        q9 = await executar("equipe", team_number=destino, itens=[i9], boletos=b9)
        kinds9 = await asyncio.to_thread(_kinds_desde, antes_q9)
        e9 = (q9["entregas"] or [{}])[0]
        r.veredito("Q9", e9.get("status") == "retido" and not kinds9
                   and "identificado por" in str(e9.get("motivo") or ""),
                   f"status={e9.get('status')} motivo={str(e9.get('motivo'))[:160]}")

        # Q10 — O CANÁRIO DE LOGIN roda ANTES da varredura, nos 4 portais com senha válida
        # (Tokio, HDI, Yelum, Zurich — D-PILOTO-19: Allianz e Mapfre esperam a senha de 15/09).
        # ⚠️ Abre portais de verdade (só `login_check`, leitura) e leva ≈100 s por portal em
        #    paralelo: só com `portais=True`.
        if portais:
            cfg10 = _cfg("equipe", destino=destino, team_number=destino)
            cfg10["portal_keys"] = ["tokiomarine_corretor", "hdi_corretor", "yelum_corretor", "zurich_corretor"]
            blockers10: List[str] = []
            rotina10 = _rotina(company_id, cfg10)
            try:
                aprovados = await BC._canario_de_login(db, rotina10, cfg10, blockers10)
                r.p(f"Q10 aprovados={sorted(aprovados.keys())} blockers={blockers10}")
                # 🔴 P3 — UM VEREDITO QUE ACEITA ZERO PORTAIS NÃO É VEREDITO.
                # A forma anterior (`len(aprovados) + len(blockers10) >= 4`) ficava
                # VERDE com 0 aprovados e 4 blockers — que é exatamente o dia em
                # que nenhuma seguradora foi varrida. A pergunta do Q10 é "o
                # canário ENTRA?", e a resposta certa exige pelo menos um ENTROU,
                # a soma EXATA dos 4 portais (nem um a mais, nem um a menos) e
                # cada recusa dizendo QUAL portal, em português.
                ok10 = (len(aprovados) >= 1
                        and len(aprovados) + len(blockers10) == len(cfg10["portal_keys"])
                        and all(b.startswith("portal ") for b in blockers10))
                r.veredito("Q10", ok10,
                           f"{len(aprovados)} de {len(cfg10['portal_keys'])} portais entraram "
                           f"(mínimo 1); {len(blockers10)} recusa(s), cada uma nomeando o portal")
            except Exception as exc:  # noqa: BLE001
                r.veredito("Q10", False, f"o canário de login levantou ({type(exc).__name__})")
            # 🔴 P9 — A LIMPEZA DO Q10. Ele ENFILEIRA `login_check` de verdade, e
            # sem isto o canário deixava lixo em `portal_jobs` a cada execução —
            # a mesma regra do Q6: quem cria, apaga. Só os TERMINAIS: um job que
            # ainda está rodando é trabalho do worker, não sujeira.
            await _limpar_jobs_do_q10(db, company_id, str(rotina10.get("id") or ""), r)
        else:
            r.p("Q10 pulado (portais=False): chame com ?portais=1 para abrir os 4 portais com senha válida")
    finally:
        if limpar:
            await _limpar(db, company_id, recibo, caminho, ledger_ids, inicio, destino, r)
        else:
            r.p("limpeza PULADA (--sem-limpeza): apague por id + company_id + canario")
    return r.como_dict()


async def _limpar_jobs_do_q10(db, company_id: str, routine_id: str, r: Relato) -> None:
    """Apaga os `portal_jobs` que o Q10 criou. Só os dele, só os terminais.

    🔴 P9 — A marca é o `params->>routine_id` da rotina SINTÉTICA do Q10, que é um
    uuid novo a cada execução (`_rotina`): nenhum job de produção pode casar com
    ele. `.filter("params->>routine_id", "eq", ...)` é como o supabase-py escreve
    um caminho de JSON no PostgREST — `.eq("params->>routine_id", ...)` não vale,
    porque `eq` escapa o nome da coluna.

    ⛔ `company_id` na cláusula, sempre (CLAUDE.md §7). ⛔ E só `done`/`failed`/
    `needs_human`: apagar um job `queued`/`running` seria tirar da mesa trabalho
    que o worker já pegou.
    """
    def _q():
        apagados = (db.table("portal_jobs").delete()
                    .eq("company_id", company_id)
                    .eq("journey", "login_check")
                    .filter("params->>routine_id", "eq", routine_id)
                    .in_("status", ["done", "failed", "needs_human"])
                    .execute().data or [])
        sobra = (db.table("portal_jobs").select("id")
                 .eq("company_id", company_id)
                 .filter("params->>routine_id", "eq", routine_id)
                 .execute().data or [])
        return len(apagados), len(sobra)

    try:
        apagados, sobra = await asyncio.to_thread(_q)
        r.p(f"limpeza Q10: portal_jobs {apagados} apagado(s); restam {sobra} "
            f"(os que ainda não terminaram ficam com o worker)")
    except Exception as exc:  # noqa: BLE001
        r.p(f"limpeza Q10: NÃO consegui apagar os portal_jobs ({type(exc).__name__}) "
            f"— apague por company_id + journey=login_check + params->>routine_id")


async def _limpar(db, company_id: str, recibo: str, caminho: str, ledger_ids: List[str],
                  inicio: datetime, destino: str, r: Relato) -> None:
    """Só o que o canário criou, por id e marca. Nunca `delete` sem `company_id`."""
    def _q():
        led = (db.table("billing_sent_log").delete().eq("company_id", company_id).eq("canario", True)
               .like("recibo", f"{recibo}%").execute().data or [])
        ps = (db.table("platform_sends").delete().eq("company_id", company_id).eq("phone", destino)
              .gte("sent_at", inicio.isoformat()).like("kind", "billing%").execute().data or [])
        act = (db.table("agent_activities").delete().eq("company_id", company_id).eq("category", "cobranca")
               .gte("created_at", inicio.isoformat()).execute().data or [])
        try:
            db.storage.from_("portal-evidence").remove([caminho])
            pdf = "removido"
        except Exception as exc:  # noqa: BLE001
            pdf = f"não removido ({type(exc).__name__})"
        sobra = (db.table("billing_sent_log").select("id").eq("company_id", company_id)
                 .eq("canario", True).like("recibo", f"{recibo}%").execute().data or [])
        return len(led), len(ps), len(act), pdf, len(sobra)

    led, ps, act, pdf, sobra = await asyncio.to_thread(_q)
    r.p(f"limpeza: ledger {led} · platform_sends {ps} · atividades {act} · pdf {pdf}")
    r.veredito("Q6", sobra == 0, f"VERIFY: restam {sobra} linha(s) do canário no ledger")
