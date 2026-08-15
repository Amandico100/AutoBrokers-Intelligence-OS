"""MAPA DE URA (SPEC-034 Onda 2) — o território completo dos fluxos por seguradora.

╔══════════════════════════════════════════════════════════════════════════╗
║  O MAPA É UM SÓ E É DE TODAS AS CORRETORAS — ele não tem `company_id`,  ║
║  e a ausência é DE PROPÓSITO.                                            ║
╚══════════════════════════════════════════════════════════════════════════╝

Decisão do Founder, 15/08/2026 —
`docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`.

Se você veio até aqui procurando o filtro por corretora que "está faltando":
ele não está faltando. Todas as corretoras alimentam **o mesmo** mapa, e todas
leem o mesmo. A URA de uma seguradora é a mesma para todas — quem percorre uma
rota nova, descobre para todo mundo. É assim que o mapa se completa.

O propósito é o agente **saber a pergunta antes de ela chegar**: sabendo o que a
URA vai perguntar e qual tecla é qual, ele não adivinha e não trava.

🔴 Mas o mapa é NEUTRO. Nome de corretora e de atendente não moram aqui — vêm da
configuração do dashboard, em tempo de execução. Quem escrever leitura nova
sobre `map` deve tratar qualquer nome próprio encontrado como **defeito a
reportar**, não como dado a usar (PENDENCIAS.md#P-165).


Formato do mapa (JSONB em ura_maps.map):
{
  "root": "<node_id>",
  "nodes": {
    "<node_id>": {
      "text": "<texto normalizado da tela>",
      "kind": "menu" | "pergunta" | "informativo" | "finalize" | "terminal",
      "options": [{"label": "...", "reply": "...", "leads_to": "<node_id>|null"}],
      "hash": "<sha1 curto do texto normalizado>"
    }
  }
}

O playbook continua sendo o CAMINHO FELIZ compilado; o mapa é o que o Cérebro v2
consulta nos DESVIOS e o que o Alfaiate diffa para detectar mudanças (Onda 4).
Funções de diff/normalização são PURAS (testáveis offline); IO Supabase é
best-effort e nunca derruba quem chama.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_screen_text(text: str) -> str:
    """Normaliza a tela p/ hash estável: sem acentos, minúsculo, sem números
    voláteis (protocolos/telefones/nomes ficam como placeholder)."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r"\d[\d\.\-/() ]{5,}", "<num>", s)  # protocolos, cpfs, telefones
    s = re.sub(r"\s+", " ", s).strip()
    return s


def node_hash(text: str) -> str:
    return hashlib.sha1(normalize_screen_text(text).encode("utf-8")).hexdigest()[:12]


def diff_maps(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Diff legível entre dois mapas: nós adicionados/removidos e opções que
    mudaram em nós persistentes. Base do Alfaiate (Onda 4) e do aviso no admin."""
    old_nodes = (old or {}).get("nodes") or {}
    new_nodes = (new or {}).get("nodes") or {}
    old_by_hash = {n.get("hash"): (nid, n) for nid, n in old_nodes.items()}
    new_by_hash = {n.get("hash"): (nid, n) for nid, n in new_nodes.items()}
    added = [n["text"][:120] for h, (_, n) in new_by_hash.items() if h not in old_by_hash]
    removed = [n["text"][:120] for h, (_, n) in old_by_hash.items() if h not in new_by_hash]
    changed_options = []
    for h, (_, n_new) in new_by_hash.items():
        if h in old_by_hash:
            n_old = old_by_hash[h][1]
            old_labels = [o.get("label") for o in n_old.get("options") or []]
            new_labels = [o.get("label") for o in n_new.get("options") or []]
            if old_labels != new_labels:
                changed_options.append({"tela": n_new["text"][:80], "de": old_labels, "para": new_labels})
    return {
        "added": added, "removed": removed, "changed_options": changed_options,
        "safe_auto_apply": bool(added) and not removed and not changed_options,
    }


def render_map_for_llm(map_obj: Dict[str, Any], max_nodes: int = 30) -> str:
    """Resumo do mapa em texto p/ o Cérebro v2 ('onde estou e o que cada opção faz').

    ESTE CORTE ESCOLHIA PELO DIGEST, E O PROMPT CHAMAVA ISSO DE 'COMPLETO'.
    ---------------------------------------------------------------------
    📊 Medido em 05/08/2026. A versão anterior fazia `list(nodes.items())[:30]`.
    A chave de cada nó é `sha1(...)[:12]` e o mapa mora em JSONB, que **não
    preserva ordem de inserção** — normaliza por (comprimento, bytes). Todas as
    chaves têm 12 caracteres, então a ordem era **lexicográfica sobre o digest**:
    uma amostra pseudo-aleatória estável, sem relação nenhuma com o fluxo.

        allianz   1.323 nós  →  o modelo veria 30   (2,3%)
        porto       840 nós  →  3,6%

    E `insurer_dispatch_service` anunciava o resultado como *"MAPA COMPLETO DA
    URA DESTA SEGURADORA"*. **Injetar 2% rotulado como 100% é pior do que não
    injetar nada:** o modelo confia no que o prompt afirma, e a tela que ele
    precisa provavelmente não está entre as trinta.

    O material para escolher direito já estava gravado e era ignorado: cada nó
    tem `samples` (quantas vezes a tela apareceu de verdade), `order`,
    `nao_rota` e `status`; e o mapa tem `root`. Nada disso era lido.

    Agora: começa pela RAIZ, exclui o que não é rota, e ordena o resto por
    quantas vezes a tela foi realmente vista. Quem fica de fora é a cauda rara,
    não um sorteio.

    Isto foi consertado enquanto o caminho está DORMENTE — 📊 `ura_maps` não tem
    nenhum mapa `active`, então `get_active_map` devolve `None` e esta função
    não é chamada em produção. Consertar código morto é barato; consertá-lo
    depois de ligado é uma mudança de comportamento ao vivo.
    """
    nodes = (map_obj or {}).get("nodes") or {}
    if not isinstance(nodes, dict) or not nodes:
        return ""

    raiz_id = str((map_obj or {}).get("root") or "")

    def _vale_como_rota(n: Dict[str, Any]) -> bool:
        # `nao_rota` marca tela que não leva a lugar nenhum (aviso, despedida).
        # Renderizá-la como rota ensina o modelo a escolher uma saída morta.
        return not bool(n.get("nao_rota")) and str(n.get("status") or "") != "nao_rota"

    candidatos = [(nid, n) for nid, n in nodes.items()
                  if isinstance(n, dict) and _vale_como_rota(n)]

    def _peso(par) -> tuple:
        _nid, n = par
        try:
            vistas = int(n.get("samples") or 0)
        except (TypeError, ValueError):
            vistas = 0
        try:
            ordem = int(n.get("order") or 10_000)
        except (TypeError, ValueError):
            ordem = 10_000
        # mais vistas primeiro; empate desfeito por quem aparece antes no fluxo
        return (-vistas, ordem)

    candidatos.sort(key=_peso)

    # A raiz nunca fica de fora: sem ela o modelo não sabe onde o fluxo começa.
    if raiz_id and raiz_id in nodes:
        candidatos = ([(raiz_id, nodes[raiz_id])]
                      + [c for c in candidatos if c[0] != raiz_id])

    escolhidos = candidatos[:max(1, int(max_nodes or 30))]
    lines: List[str] = []
    for nid, n in escolhidos:
        opts = " | ".join(
            f"'{o.get('label')}'→responder '{o.get('reply')}'" for o in (n.get("options") or [])[:8]
        )
        marca = " [TELA INICIAL]" if nid == raiz_id else ""
        lines.append(f"- [{n.get('kind')}]{marca} \"{n.get('text', '')[:110]}\""
                     + (f" → opções: {opts}" if opts else ""))
    return "\n".join(lines)


def resumo_honesto_do_mapa(map_obj: Dict[str, Any], max_nodes: int = 30) -> str:
    """Quantas telas o modelo está vendo, de quantas existem.

    Existe para que o prompt possa dizer a verdade. O rótulo antigo — "MAPA
    COMPLETO DA URA DESTA SEGURADORA" — era uma afirmação falsa em 2,3% dos
    casos da Allianz, e o modelo não tem como desconfiar do próprio prompt.
    """
    nodes = (map_obj or {}).get("nodes") or {}
    total = len(nodes) if isinstance(nodes, dict) else 0
    mostradas = min(total, max(1, int(max_nodes or 30))) if total else 0
    cobertura = ((map_obj or {}).get("coverage") or {}).get("pct")
    extra = f", cobertura observada {cobertura}%" if cobertura not in (None, "") else ""
    return f"{mostradas} de {total} telas observadas{extra}"


# ── IO Supabase (best-effort) ─────────────────────────────────────────────────
# Uma seguradora tem UM WhatsApp para toda a assistencia. A URA pergunta qual
# seguro e ramifica dali — o mapa observado contem a arvore INTEIRA, com auto,
# residencial, condominio e empresarial dentro dela.
#
# `todos` e o ramo desse mapa unico. Rotula-lo como "auto" era mentira com
# consequencia: a Resulta conversa sobre residencial e condominio, a AutoFleet
# so sobre auto e frota, e as duas falam com o MESMO numero.
RAMO_COMPLETO = "todos"


async def save_proposed_map(insurer_key: str, ramo: str, map_obj: Dict[str, Any],
                            source: str = "cartographer") -> Optional[str]:
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        active = await get_active_map(insurer_key, ramo)
        diff = diff_maps((active or {}).get("map") or {}, map_obj)
        version = int((active or {}).get("version") or 0) + 1
        row = {
            "insurer_key": insurer_key, "ramo": ramo, "version": version,
            "status": "proposed", "map": map_obj, "source": source,
            "diff_summary": (
                f"+{len(diff['added'])} telas novas, -{len(diff['removed'])} removidas, "
                f"{len(diff['changed_options'])} menus alterados"
            ),
        }
        res = await asyncio.to_thread(lambda: db.client.table("ura_maps").insert(row).execute())
        return res.data[0]["id"] if res.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] save_proposed falhou: {type(e).__name__}")
        return None


async def get_active_map(insurer_key: str, ramo: str = "auto") -> Optional[Dict[str, Any]]:
    """O mapa ativo da seguradora. Cai para o mapa COMPLETO quando não há um
    específico do ramo pedido.

    Quem chama pergunta por um ramo concreto — o acionamento pede "auto",
    porque é o que o playbook dele diz. Mas o mapa observado é **um só**, com a
    árvore inteira, e vive sob `todos`.

    Sem esta reserva, mudar o rótulo para a verdade faria o acionamento parar de
    achar o mapa: uma correção de nome viraria um defeito de funcionamento.
    """
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _buscar(r: str):
            return (db.client.table("ura_maps").select("*")
                    .eq("insurer_key", insurer_key).eq("ramo", r)
                    .eq("status", "active")
                    .order("version", desc=True).limit(1).execute())

        res = await asyncio.to_thread(lambda: _buscar(ramo))
        if not res.data and ramo != RAMO_COMPLETO:
            res = await asyncio.to_thread(lambda: _buscar(RAMO_COMPLETO))
        return res.data[0] if res.data else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] get_active falhou: {type(e).__name__}")
        return None


async def activate_map(map_id: str) -> bool:
    """Promove um mapa proposed→active e aposenta o active anterior."""
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        res = await asyncio.to_thread(
            lambda: db.client.table("ura_maps").select("insurer_key, ramo").eq("id", map_id).limit(1).execute()
        )
        if not res.data:
            return False
        ik, ramo = res.data[0]["insurer_key"], res.data[0]["ramo"]
        await asyncio.to_thread(
            lambda: db.client.table("ura_maps").update({"status": "retired"})
            .eq("insurer_key", ik).eq("ramo", ramo).eq("status", "active").execute()
        )
        await asyncio.to_thread(
            lambda: db.client.table("ura_maps").update({"status": "active"}).eq("id", map_id).execute()
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[URA_MAP] activate falhou: {type(e).__name__}")
        return False


# ===========================================================================
# HIGIENE E PROMOÇÃO — SPEC-063, 07/08/2026
# ===========================================================================
# 📊 Zero mapas `active` em produção. Consequência medida, em cadeia:
# `route_sentinel.check_insurer` sai na terceira linha (`if not active: return
# None`), `route_drift` = 0 registros, `playbook_overlays` = 0, e o alerta
# "a seguradora mudou o menu" nunca chega ao Founder. Três subsistemas
# construídos, testados e inalcançáveis por causa de um `status`.
#
# Promover à mão resolveria — e foi o que quase fizemos. O que impediu: 📊 115
# nós carregam nome próprio de segurado e 24 carregam marca de corretora. O
# mapa é GLOBAL: promovê-lo assim publicaria o nome de um cliente e a marca de
# uma corretora dentro do conhecimento que as outras leem (CLAUDE.md §7).
#
# Por isso as duas coisas moram juntas: **limpar é pré-condição de promover**,
# e a ordem está no código em vez de estar na cabeça de quem clica.
_MAX_MARCA_PARA_PROMOVER = 0


def _renomear_nos_sync(mapa: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Reaplica o mascarador de produção sobre os nós JÁ gravados.

    Usa `templatize`, o mesmo do caminho de captura — não uma segunda regra.
    Uma cópia aqui divergiria da original no dia em que uma das duas fosse
    corrigida, e a divergência apareceria como PII vazando de um lado só.
    """
    from app.services.atlas.templater import templatize

    nos = (mapa or {}).get("nodes") or {}
    if not isinstance(nos, dict):
        return mapa, 0

    tocados = 0
    novos: Dict[str, Any] = {}
    for chave, no in nos.items():
        if not isinstance(no, dict):
            novos[chave] = no
            continue
        texto = no.get("text")
        if isinstance(texto, str) and texto:
            limpo = templatize(texto)
            if limpo != texto:
                no = {**no, "text": limpo}
                tocados += 1

        # 🔴 O RÓTULO DA OPÇÃO TAMBÉM — 15/08/2026.
        #
        # Esta função prometia "reaplica o mascarador sobre os nós JÁ gravados"
        # e limpava SÓ `no["text"]`. 📊 O rótulo da opção e o da aresta ficavam
        # como estavam — e era exatamente ali que estavam os 141 CPF (P-162).
        # A higiene tinha o mesmo ponto cego do Tecelão.
        #
        # ⚠️ `rotulo_de_campo=False` aqui pelo mesmo motivo do Tecelão: rótulo
        # de opção chega sozinho, e com a rede ligada "Assistência 24h" viraria
        # "{VALOR}" e a opção sumiria na limpeza (P-164). Limpar não pode
        # apagar o guincho.
        opcoes = no.get("options")
        if isinstance(opcoes, list) and opcoes:
            novas_opcoes = []
            mudou_opcao = False
            for opt in opcoes:
                if not isinstance(opt, dict):
                    novas_opcoes.append(opt)
                    continue
                nova = dict(opt)
                for campo in ("label", "reply"):
                    valor = nova.get(campo)
                    if isinstance(valor, str) and valor:
                        limpo_o = templatize(valor, rotulo_de_campo=False)
                        if limpo_o != valor:
                            nova[campo] = limpo_o
                            mudou_opcao = True
                novas_opcoes.append(nova)
            if mudou_opcao:
                no = {**no, "options": novas_opcoes}
                tocados += 1
        novos[chave] = no

    saida: Dict[str, Any] = {**(mapa or {}), "nodes": novos}

    # 🔴 A ARESTA — onde estavam os 141 CPF, 34 CNPJ e 105 placas.
    #
    # ⚠️ A CHAVE da aresta é `"{no_origem}|{rótulo}"`, então limpar o rótulo
    # obriga a REESCREVER a chave. Duas arestas que só diferiam pelo CPF
    # colapsam numa só — e isso é o certo: era uma aresta por SEGURADO onde
    # deveria haver uma por ROTA.
    arestas = (mapa or {}).get("edges")
    if isinstance(arestas, dict) and arestas:
        novas_arestas: Dict[str, Any] = {}
        for chave, aresta in arestas.items():
            if not isinstance(aresta, dict):
                novas_arestas[chave] = aresta
                continue
            rotulo = aresta.get("label")
            if isinstance(rotulo, str) and rotulo:
                limpo_a = templatize(rotulo, rotulo_de_campo=False)
                if limpo_a != rotulo:
                    aresta = {**aresta, "label": limpo_a}
                    src = str(chave).split("|", 1)[0]
                    chave = f"{src}|{limpo_a}"
                    tocados += 1
            # Colisão depois da limpeza = a MESMA rota vista duas vezes.
            # Somar o que for contável preserva o peso; o resto fica com o
            # primeiro, que é o mais antigo (as arestas vêm em ordem).
            if chave in novas_arestas:
                antiga = novas_arestas[chave]
                if isinstance(antiga, dict):
                    for campo in ("count", "samples", "observations"):
                        if isinstance(antiga.get(campo), int) and isinstance(aresta.get(campo), int):
                            antiga[campo] = antiga[campo] + aresta[campo]
                continue
            novas_arestas[chave] = aresta
        saida["edges"] = novas_arestas

    # E a trilha escrita (`paths[*].steps[*].c`), que carrega a mesma escolha.
    trilhas = (mapa or {}).get("paths")
    if isinstance(trilhas, list) and trilhas:
        novas_trilhas = []
        for trilha in trilhas:
            if not isinstance(trilha, dict):
                novas_trilhas.append(trilha)
                continue
            passos = trilha.get("steps")
            if isinstance(passos, list):
                novos_passos = []
                for passo in passos:
                    if isinstance(passo, dict) and isinstance(passo.get("c"), str) and passo["c"]:
                        limpo_p = templatize(passo["c"], rotulo_de_campo=False)
                        if limpo_p != passo["c"]:
                            passo = {**passo, "c": limpo_p}
                            tocados += 1
                    novos_passos.append(passo)
                trilha = {**trilha, "steps": novos_passos}
            novas_trilhas.append(trilha)
        saida["paths"] = novas_trilhas

    return saida, tocados


def _tem_marca_de_corretora(mapa: Dict[str, Any]) -> int:
    """Quantos nós ainda nomeiam uma corretora. Promover com isto é vazamento.

    🔴 ESTE PORTÃO PROMETIA "nunca promove mapa com marca de corretora" E
    DEIXOU PASSAR — 15/08/2026.

    📊 Ele era uma lista de três literais: `autofleet|resulta seguros|amandus`.
    Medido contra os quatro vazamentos reais encontrados nos mapas ativos:

        "*Saionara - Resulta*, por ser um item essencial…"     -> False
        "Olá RESULTA CORRETORA DE SEGUROS LTDA…"               -> False
        "Olá INDYANA COMERCIO DE VEICULOS LTDA…"               -> False
        "Olá CONDOMINIO DO CONJUNTO RESIDENCIAL…"              -> False

    **Quatro `False`.** O portão não falhou por bug — falhou por não conhecer os
    nomes. Uma lista escrita à mão envelhece no dia em que entra a quarta
    corretora, e ninguém é avisado.

    Agora ele lê `marcas_de_corretora()`, a mesma fonte que o mascarador usa —
    `companies`. E olha os quatro lugares, não só o texto do nó: 📊 o rótulo da
    ARESTA era onde estavam os 141 CPF, e ele nunca foi conferido aqui.
    """
    import re as _re

    from app.services.atlas.templater import marcas_de_corretora

    marcas = [m for m in marcas_de_corretora() if len(m) >= 4]
    if not marcas:
        # Sem configuração legível, o portão vira o antigo — nunca vira "passa
        # tudo". Errar para o lado de NÃO promover é o lado barato.
        marcas = ["autofleet", "resulta", "amandus"]
    padrao = _re.compile(
        r"\b(" + "|".join(_re.escape(m) for m in marcas) + r")\b", _re.IGNORECASE)

    mapa = mapa or {}
    sujos = 0

    nos = mapa.get("nodes") or {}
    if isinstance(nos, dict):
        for no in nos.values():
            if not isinstance(no, dict):
                continue
            alvo = [str(no.get("text") or "")]
            for opt in (no.get("options") or []):
                if isinstance(opt, dict):
                    alvo.append(str(opt.get("label") or ""))
                    alvo.append(str(opt.get("reply") or ""))
            if any(padrao.search(t) for t in alvo if t):
                sujos += 1

    # A aresta — o ponto cego que guardava os CPF e as razões sociais.
    arestas = mapa.get("edges") or {}
    if isinstance(arestas, dict):
        for chave, aresta in arestas.items():
            rotulo = str((aresta or {}).get("label") or "") if isinstance(aresta, dict) else ""
            if padrao.search(str(chave)) or (rotulo and padrao.search(rotulo)):
                sujos += 1

    return sujos


async def higienizar_e_promover(*, aplicar: bool = True) -> Dict[str, Any]:
    """Remascara os mapas observados e promove os que ficarem limpos.

    Idempotente: rodar de novo não muda nada num mapa já limpo, e não repromove
    o que já está ativo. Pode viver no agendador sem custo — não chama modelo
    nenhum, é só regex e escrita.

    ⚠️ **Nunca promove mapa com marca de corretora.** Se sobrar uma, o mapa
    continua `observed` e o relatório diz quantas — é melhor uma seguradora
    ficar de fora da Sentinela do que a marca de um cliente entrar no acervo
    que os outros leem.
    """
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    resumo: Dict[str, Any] = {"lidos": 0, "limpos": 0, "nos_mascarados": 0,
                              "promovidos": 0, "barrados_por_marca": [],
                              "aplicado": aplicar}
    try:
        linhas = await asyncio.to_thread(
            lambda: db.client.table("ura_maps")
            .select("id, insurer_key, ramo, map, status")
            .eq("status", "observed").limit(200).execute().data or [])
    except Exception as erro:  # noqa: BLE001
        logger.warning("[URA_MAP] higiene não leu os mapas (%s)", type(erro).__name__)
        return {**resumo, "ok": False, "motivo": type(erro).__name__}

    for linha in linhas:
        resumo["lidos"] += 1
        mapa, tocados = _renomear_nos_sync(linha.get("map") or {})
        marcas = _tem_marca_de_corretora(mapa)

        if tocados and aplicar:
            try:
                await asyncio.to_thread(
                    lambda m=mapa, i=linha["id"]: db.client.table("ura_maps")
                    .update({"map": m}).eq("id", i).execute())
            except Exception as erro:  # noqa: BLE001
                logger.warning("[URA_MAP] não gravei a higiene de %s (%s)",
                               linha.get("insurer_key"), type(erro).__name__)
                continue
        resumo["nos_mascarados"] += tocados

        if marcas > _MAX_MARCA_PARA_PROMOVER:
            resumo["barrados_por_marca"].append(
                {"seguradora": linha.get("insurer_key"), "nos_com_marca": marcas})
            continue

        resumo["limpos"] += 1
        if aplicar and await activate_map(str(linha["id"])):
            resumo["promovidos"] += 1

    logger.info("[URA_MAP] higiene: %s lidos, %s nós mascarados, %s promovidos, "
                "%s barrados por marca de corretora",
                resumo["lidos"], resumo["nos_mascarados"], resumo["promovidos"],
                len(resumo["barrados_por_marca"]))
    return {**resumo, "ok": True}
