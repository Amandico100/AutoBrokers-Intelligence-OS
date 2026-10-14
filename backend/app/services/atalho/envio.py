# -*- coding: utf-8 -*-
"""SPEC-132-C C2 — a SAÍDA do atalho: o texto do chat em formato WhatsApp, pelo número do AutoBrokers.

    para_whatsapp(markdown)                                 o markdown do CORE → o texto que o WhatsApp mostra bem
    em_mensagens(texto, teto=3500)                          cortado em mensagens inteiras (parágrafo → linha → força)
    integracao_do_assistente(db)                            a integração ATIVA `purpose='assistente'` da plataforma
    async enviar(integracao, telefone, mensagens)           manda pela integração DADA; para no 1º que falhar
    async enviar_ao_membro(db, *, company_id, user_id, texto)   a C3 chama (o resultado da cotação pelo WhatsApp)
    async avisar_pelo_atalho_se_for_o_caso(db, *, company_id, conversation_id, texto_markdown)   C3: a conversa é do
                                                            atalho? → `enviar_ao_membro` ao dono dela
    avisar_pelo_atalho_sem_esperar(...)                     a ponte síncrona (o `gravar_mensagem` da cotação)
    async digitando(integracao, telefone, estado)           "digitando…" (a mesma flag do atendimento)

Um motor só (CLAUDE.md §5): o envio é `whatsapp_service.send_message` (o seam multi-provedor, a digital da própria
voz) com `bloco_unico=True` — a resposta do chat é um DOCUMENTO para o corretor, não uma conversa picotada em balões
de 300 caracteres. O corte em ≤ 💭 3.500 é feito AQUI, por parágrafo, para nada sair partido no meio de uma linha.

🔴 A integração de saída é SEMPRE a do assistente (a que recebeu, ou a achada por `integracao_do_assistente`) —
nunca "qualquer integração ativa da empresa da plataforma": a mesma empresa tem o número do QCM, e responder ao
corretor pelo número do QCM (ou vice-versa) é a mutação 4 ao contrário.
⛔ Nenhum telefone em log (só `mascarar`); nenhum conteúdo em log.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)

#: 💭 o teto de UMA mensagem (o mesmo `_TETO_DE_UMA_MENSAGEM` do `whatsapp_service`: com ele, `bloco_unico` não re-corta)
TETO_DE_UMA_MENSAGEM = 3500
#: a cadência entre mensagens (a mesma de `whatsapp_service.send_message` e do canal)
PAUSA_ENTRE_MENSAGENS_S = 0.7
_PROVEDORES = ("evolution-go", "evolution", "evolution-api")


# =====================================================================================================================
# o formato WhatsApp
# =====================================================================================================================
_LINK_MD = re.compile(r"(?<!!)\[([^\]\n]{1,200})\]\(([^)\s]{1,2000})\)")
_IMAGEM_MD = re.compile(r"!\[([^\]\n]{0,200})\]\(([^)\s]{1,2000})\)")
_TITULO = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
_REGUA = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_ITEM = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_SEPARADOR_DE_TABELA = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_CERCA = re.compile(r"^\s*```")


def _absoluto(url: str) -> str:
    """Link relativo do painel (`/dashboard/entregas/<id>`) → absoluto pelo endereço público do app (um lugar só)."""
    u = str(url or "").strip()
    if u.startswith("/") and not u.startswith("//"):
        try:
            from app.services.artifacts.service import base_publica_do_app

            base = base_publica_do_app()
        except Exception:  # noqa: BLE001
            base = ""
        return f"{base}{u}" if base else u
    return u


def _negrito_e_italico(linha: str) -> str:
    """`**x**`/`__x__` → `*x*` · `*x*`/`_x_` (itálico do markdown) → `_x_` · `~~x~~` → `~x~`."""
    marca = "\x00"
    s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", lambda m: f"{marca}{m.group(1)}{marca}", linha)
    s = re.sub(r"__(?=\S)(.+?)(?<=\S)__", lambda m: f"{marca}{m.group(1)}{marca}", s)
    s = re.sub(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])", r"_\1_", s)
    s = re.sub(r"~~(?=\S)(.+?)(?<=\S)~~", r"~\1~", s)
    return s.replace(marca, "*")


def _limpar_celula(celula: str) -> str:
    c = re.sub(r"\*\*|__|`", "", str(celula or "")).strip()
    return re.sub(r"\s+", " ", c)


def _celulas(linha: str) -> List[str]:
    s = linha.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [_limpar_celula(c) for c in s.split("|")]


def _tabela_em_linhas(cabecalho: List[str], linhas: List[List[str]]) -> List[str]:
    """Uma linha por registro: "• Seguradora — 12x R$ 99,90 · à vista R$ 1.100".

    Duas colunas → "• A — B". Três ou mais → cada valor depois do 1º leva o rótulo da coluna (em minúscula), salvo
    quando o valor já o diz. Célula vazia some. O cabeçalho em si não vira linha."""
    saida = []
    for linha in linhas:
        valores = [c for c in linha]
        if not any(valores):
            continue
        primeiro = valores[0] if valores else ""
        resto = []
        for j, valor in enumerate(valores[1:], start=1):
            if not valor:
                continue
            rotulo = cabecalho[j] if j < len(cabecalho) else ""
            if len(cabecalho) > 2 and rotulo and rotulo.lower() not in valor.lower():
                resto.append(f"{rotulo[:1].lower()}{rotulo[1:]} {valor}")
            else:
                resto.append(valor)
        if primeiro and resto:
            saida.append(f"• {primeiro} — {' · '.join(resto)}")
        elif primeiro or resto:
            saida.append("• " + (primeiro or " · ".join(resto)))
    return saida


def para_whatsapp(markdown: Any) -> str:
    """O markdown do CORE no formato do WhatsApp: títulos e negrito → *negrito*, itálico → _itálico_, listas → "•",
    tabelas → uma linha legível por registro, régua → nada, e os LINKS no fim ("Rótulo: https://…").
    Código entre cercas (```) passa como está. Nunca levanta."""
    texto = str(markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    links: List[Tuple[str, str]] = []

    def _guardar_link(m: "re.Match") -> str:
        rotulo, url = m.group(1).strip(), _absoluto(m.group(2))
        if url and (rotulo, url) not in links:
            links.append((rotulo, url))
        return rotulo if rotulo and rotulo != m.group(2) else ""

    linhas_in = texto.split("\n")
    saida: List[str] = []
    i, em_codigo = 0, False
    while i < len(linhas_in):
        linha = linhas_in[i]
        if _CERCA.match(linha):
            em_codigo = not em_codigo
            saida.append(linha.strip())
            i += 1
            continue
        if em_codigo:
            saida.append(linha)
            i += 1
            continue
        # a tabela: cabeçalho + separador + registros
        if "|" in linha and i + 1 < len(linhas_in) and _SEPARADOR_DE_TABELA.match(linhas_in[i + 1]) \
                and "-" in linhas_in[i + 1]:
            cabecalho = _celulas(_LINK_MD.sub(_guardar_link, linha))
            j, registros = i + 2, []
            while j < len(linhas_in) and "|" in linhas_in[j] and linhas_in[j].strip():
                registros.append(_celulas(_LINK_MD.sub(_guardar_link, linhas_in[j])))
                j += 1
            saida.extend(_negrito_e_italico(x) for x in _tabela_em_linhas(cabecalho, registros))
            i = j
            continue
        if _REGUA.match(linha):
            saida.append("")
            i += 1
            continue
        linha = _IMAGEM_MD.sub(lambda m: (links.append((m.group(1).strip() or "Imagem", _absoluto(m.group(2))))
                                          or ""), linha)
        linha = _LINK_MD.sub(_guardar_link, linha)
        titulo = _TITULO.match(linha)
        if titulo:
            conteudo = re.sub(r"\*\*|__", "", titulo.group(1)).strip()
            saida.append(f"*{conteudo}*" if conteudo else "")
            i += 1
            continue
        item = _ITEM.match(linha)
        if item:
            recuo = "  " if len(item.group(1)) >= 2 else ""
            saida.append(f"{recuo}• {_negrito_e_italico(item.group(2).strip())}")
            i += 1
            continue
        saida.append(_negrito_e_italico(linha.rstrip()))
        i += 1

    corpo = "\n".join(saida)
    corpo = re.sub(r"\n{3,}", "\n\n", corpo).strip()
    if links:
        partes = []
        for rotulo, url in links:
            if url in corpo:   # o link já está solto no texto: não repete
                continue
            partes.append(f"{rotulo}: {url}" if rotulo and rotulo != url else url)
        if partes:
            corpo = (corpo + "\n\n" if corpo else "") + "\n".join(partes)
    return corpo


def em_mensagens(texto: Any, teto: int = TETO_DE_UMA_MENSAGEM) -> List[str]:
    """Corta em mensagens de até `teto` caracteres: junta parágrafos inteiros; parágrafo maior que o teto, por linha;
    linha maior que o teto, na força (senão ela nunca sai). Vazio → []."""
    bruto = str(texto or "").strip()
    if not bruto:
        return []
    teto = max(50, int(teto or TETO_DE_UMA_MENSAGEM))
    if len(bruto) <= teto:
        return [bruto]
    pedacos: List[str] = []
    atual = ""

    def _empurrar(bloco: str, sep: str) -> None:
        nonlocal atual
        candidato = f"{atual}{sep}{bloco}" if atual else bloco
        if len(candidato) <= teto:
            atual = candidato
            return
        if atual:
            pedacos.append(atual)
            atual = ""
        if len(bloco) <= teto:
            atual = bloco
            return
        if sep == "\n\n":
            for linha in bloco.split("\n"):
                _empurrar(linha, "\n")
            return
        while len(bloco) > teto:
            pedacos.append(bloco[:teto])
            bloco = bloco[teto:]
        atual = bloco

    for paragrafo in re.split(r"\n{2,}", bruto):
        if paragrafo.strip():
            _empurrar(paragrafo.strip("\n"), "\n\n")
    if atual:
        pedacos.append(atual)
    return [p.strip() for p in pedacos if p.strip()]


# =====================================================================================================================
# a integração do assistente e o envio
# =====================================================================================================================
def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def integracao_do_assistente(db: Any) -> Optional[Dict[str, Any]]:
    """A integração ATIVA `purpose='assistente'` da empresa da PLATAFORMA (`company_kind='platform_canal'`, pelo
    banco — §13.9), conectada primeiro, com os segredos prontos para o envio. Nenhuma → None. Nunca levanta."""
    try:
        from app.services.atalho.verificacao import PURPOSE_DO_ASSISTENTE
        from app.services.canal.repositorio import KIND_DO_CANAL

        empresas = _dados(db.table("companies").select("id, company_kind").eq("company_kind", KIND_DO_CANAL).execute())
        ids = sorted({str(x.get("id") or "").lower() for x in empresas if x.get("company_kind") == KIND_DO_CANAL}
                     - {""})
        if not ids:
            return None
        linhas = _dados(db.table("integrations").select("*").eq("purpose", PURPOSE_DO_ASSISTENTE)
                        .eq("is_active", True).in_("company_id", ids).execute())
        linhas = [x for x in linhas if str(x.get("company_id") or "").lower() in ids
                  and x.get("purpose") == PURPOSE_DO_ASSISTENTE and x.get("is_active") is True
                  and str(x.get("provider") or "").strip().lower() in _PROVEDORES]
        if not linhas:
            return None
        linhas.sort(key=lambda x: 0 if str(x.get("channel_status") or "").lower() == "connected" else 1)
        from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

        return prepare_integration_for_runtime(linhas[0])
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] integração do assistente ilegível (%s)", type(erro).__name__)
        return None


def _mascarar(telefone: Any) -> str:
    from app.services.canal.repositorio import mascarar

    return mascarar(telefone)


async def enviar(integracao: Dict[str, Any], telefone: Any, mensagens: Union[str, Sequence[str]]) -> int:
    """Manda as mensagens ao telefone pela integração DADA (a do assistente). Devolve quantas saíram; para na 1ª
    que falhar (uma resposta pela metade é melhor que uma fora de ordem). Nunca levanta."""
    from app.services.atalho.verificacao import PURPOSE_DO_ASSISTENTE
    from app.services.canal.repositorio import canonico

    lista = [mensagens] if isinstance(mensagens, str) else list(mensagens or [])
    textos = [str(t).strip() for t in lista if str(t or "").strip()]
    tel = canonico(telefone)
    if not textos or not tel or not integracao:
        return 0
    if str(integracao.get("purpose") or "") != PURPOSE_DO_ASSISTENTE:
        # o cinto: o atalho nunca fala por outro número (atendimento, observer, QCM)
        logger.error("[ATALHO] envio recusado: a integração não é a do assistente")
        return 0
    from app.services.whatsapp_service import get_whatsapp_service

    servico = get_whatsapp_service()
    saiu = 0
    for i, texto in enumerate(textos):
        if i:
            await asyncio.sleep(PAUSA_ENTRE_MENSAGENS_S)
        try:
            ok = await asyncio.to_thread(servico.send_message, tel, texto, integracao, bloco_unico=True)
        except Exception as erro:  # noqa: BLE001 — o contrato legado levanta na falha
            logger.error("[ATALHO] mensagem %d/%d não saiu para %s (%s)", i + 1, len(textos), _mascarar(tel),
                         type(erro).__name__)
            break
        if ok is False:
            logger.error("[ATALHO] mensagem %d/%d recusada para %s", i + 1, len(textos), _mascarar(tel))
            break
        saiu += 1
    return saiu


async def enviar_texto(integracao: Dict[str, Any], telefone: Any, markdown: Any) -> int:
    """`para_whatsapp` → `em_mensagens` → `enviar`. O caminho único da resposta do chat."""
    return await enviar(integracao, telefone, em_mensagens(para_whatsapp(markdown)))


def _telefone_verificado(db: Any, company_id: str, user_id: str) -> Optional[str]:
    cid, uid = str(company_id or "").strip().lower(), str(user_id or "").strip().lower()
    if not cid or not uid:
        return None
    linhas = _dados(db.table("company_members")
                    .select("company_id, user_id, status, whatsapp_trabalho_e164, whatsapp_trabalho_verificado_em")
                    .eq("company_id", cid).eq("user_id", uid).limit(1).execute())
    linha = next((x for x in linhas if str(x.get("company_id") or "").lower() == cid
                  and str(x.get("user_id") or "").lower() == uid), None)
    if not linha or linha.get("status") != "active" or not linha.get("whatsapp_trabalho_verificado_em"):
        return None
    return str(linha.get("whatsapp_trabalho_e164") or "") or None


async def enviar_ao_membro(db: Any, *, company_id: Any, user_id: Any, texto: Any) -> int:
    """Para a C3 (o resultado da cotação pelo WhatsApp): manda `texto` (markdown) ao número VERIFICADO do membro
    (company_id, user_id), pela integração do assistente. Membro inativo, sem número verificado ou sem assistente
    ligado → 0 (nada sai). Respeita `ATALHO_WHATSAPP_LIGADO`. Nunca levanta."""
    try:
        from app.services.atalho.entrada import ligado

        if not ligado():
            return 0
        telefone = await asyncio.to_thread(_telefone_verificado, db, str(company_id or ""), str(user_id or ""))
        if not telefone:
            return 0
        integracao = await asyncio.to_thread(integracao_do_assistente, db)
        if not integracao:
            return 0
        return await enviar_texto(integracao, telefone, texto)
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] envio ao membro falhou (%s)", type(erro).__name__)
        return 0


# =====================================================================================================================
# SPEC-132-C C3 — a volta do Work Run pelo WhatsApp (a Cotação Rápida que terminou depois do turno)
# =====================================================================================================================
#: 💭 quanto a volta pode segurar quem a chamou (o envio tem o próprio timeout; isto é o cinto)
TEMPO_DA_VOLTA_S = 60.0
_VOLTAS_EM_CURSO: set = set()


def _conversa_do_atalho(db: Any, company_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
    """A conversa SE for desta corretora E do canal do atalho (filtro no banco E reconferido aqui). Senão None."""
    from app.services.atalho.turno import CANAL_DO_ATALHO

    cid, conv = str(company_id or "").strip().lower(), str(conversation_id or "").strip().lower()
    if not cid or not conv:
        return None
    cli = getattr(db, "client", db)
    linhas = _dados(cli.table("conversations").select("id, company_id, user_id, channel")
                    .eq("id", conv).eq("company_id", cid).limit(1).execute())
    linha = next((x for x in linhas if str(x.get("id") or "").lower() == conv
                  and str(x.get("company_id") or "").lower() == cid), None)
    if not linha or linha.get("channel") != CANAL_DO_ATALHO or not linha.get("user_id"):
        return None
    return linha


async def avisar_pelo_atalho_se_for_o_caso(db: Any, *, company_id: Any, conversation_id: Any,
                                           texto_markdown: Any) -> bool:
    """A mensagem que um Work Run gravou na conversa (ex.: o resultado da Cotação Rápida) volta TAMBÉM pelo WhatsApp
    quando a conversa nasceu nele (`channel == turno.CANAL_DO_ATALHO`): ao DONO da conversa (`user_id`), no número
    VERIFICADO dele, pela instância do assistente (`enviar_ao_membro` — que respeita `ATALHO_WHATSAPP_LIGADO`).
    Conversa do painel, de outra corretora, sem dono ou ilegível → False, nada sai. True = saiu ao menos 1 mensagem.
    Nunca levanta (quem chama já gravou a mensagem; o WhatsApp é cortesia)."""
    try:
        if not str(texto_markdown or "").strip():
            return False
        cid = str(company_id or "")
        linha = await asyncio.to_thread(_conversa_do_atalho, db, cid, str(conversation_id or ""))
        if not linha:
            return False
        cli = getattr(db, "client", db)
        n = await enviar_ao_membro(cli, company_id=cid.strip().lower(), user_id=str(linha["user_id"]),
                                   texto=texto_markdown)
        return n > 0
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] a volta pelo WhatsApp falhou (%s)", type(erro).__name__)
        return False


def avisar_pelo_atalho_sem_esperar(db: Any, *, company_id: Any, conversation_id: Any, texto_markdown: Any) -> None:
    """A ponte SÍNCRONA para quem grava a mensagem fora de um laço async (`cotacao.workflow.gravar_mensagem`, que roda
    em `asyncio.to_thread`): sem laço nesta thread → roda a volta aqui mesmo (com teto); dentro de um laço (o gancho
    de desistência do Work OS) → agenda no laço e segue. Nunca levanta."""
    async def _com_teto() -> None:
        try:
            await asyncio.wait_for(avisar_pelo_atalho_se_for_o_caso(
                db, company_id=company_id, conversation_id=conversation_id, texto_markdown=texto_markdown),
                timeout=TEMPO_DA_VOLTA_S)
        except Exception as erro:  # noqa: BLE001
            logger.error("[ATALHO] a volta pelo WhatsApp não terminou (%s)", type(erro).__name__)

    try:
        try:
            laco = asyncio.get_running_loop()
        except RuntimeError:
            laco = None
        if laco is None:
            asyncio.run(_com_teto())
        else:
            tarefa = laco.create_task(_com_teto())
            _VOLTAS_EM_CURSO.add(tarefa)          # sem a referência o laço pode recolher a tarefa no meio
            tarefa.add_done_callback(_VOLTAS_EM_CURSO.discard)
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] a volta pelo WhatsApp não foi agendada (%s)", type(erro).__name__)


async def digitando(integracao: Dict[str, Any], telefone: Any, estado: str = "composing") -> None:
    """"digitando…" — a MESMA flag e o MESMO seam do atendimento (`PRESENCA_DIGITANDO_LIGADA`,
    `whatsapp_service.send_presence`). Enfeite: nunca levanta, nunca custa a resposta."""
    try:
        from app.core.config import settings

        if not getattr(settings, "PRESENCA_DIGITANDO_LIGADA", False):
            return
        from app.services.canal.repositorio import canonico
        from app.services.whatsapp_service import get_whatsapp_service

        tel = canonico(telefone)
        if tel and integracao:
            await asyncio.to_thread(get_whatsapp_service().send_presence, tel, estado, integracao, 0)
    except Exception as erro:  # noqa: BLE001
        logger.debug("[ATALHO] presença não enviada (%s)", type(erro).__name__)


__all__ = ("TETO_DE_UMA_MENSAGEM", "para_whatsapp", "em_mensagens", "integracao_do_assistente", "enviar",
           "enviar_texto", "enviar_ao_membro", "digitando", "avisar_pelo_atalho_se_for_o_caso",
           "avisar_pelo_atalho_sem_esperar")
