# -*- coding: utf-8 -*-
"""A configuração COMERCIAL do multicálculo — SPEC-130-A U2 (D-MC-62…72, D-130A-04/05) · SPEC-130-A.1 (D-130A1-*).

🔴 Este é o ÚNICO lugar com os números comerciais (comissão, alvo, validade, lembretes, pesos da nota, quantas
opções). O Founder (06/10): *"ajustes futuros virão dos comerciais: deixe tudo como CONFIGURAÇÃO, nunca constante
espalhada"*. O guarda `tests/test_spec130a_a_config.py::test_g8_nenhum_numero_comercial_fora_da_config` procura
estes números nos outros arquivos da 130-A e fica VERMELHO se um deles aparecer lá.

`PADRAO_DO_PRODUTO` vale para toda corretora que não configurou o seu; `carregar(company_id, db=)` devolve o padrão
⊕ a linha da corretora em `multicalculo_config` (migration 20261006_01). Só as chaves que o padrão conhece entram;
um valor de tipo errado ou uma régua incoerente (piso acima do autônomo, pesos que não somam 100) é IGNORADO com
log — vale o padrão daquela seção, nunca um número quebrado.
"""
from __future__ import annotations

import copy
import logging
import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping, Optional

logger = logging.getLogger(__name__)

TABELA = "multicalculo_config"

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class ConfigIndisponivel(RuntimeError):
    """O banco não respondeu: a config da corretora pode ter um piso MAIOR que o padrão — nunca se adivinha."""


#: 📊 = declarado pelas comerciais (n = 4, ESTRATEGIA §1) ou decidido pelo Founder · 💭 = valor inicial a calibrar
PADRAO_DO_PRODUTO: Dict[str, Any] = {
    # D-MC-66/67/68/64 — a margem. % de comissão da corretora.
    # 🔴 D-MC-68 CORRIGIDA (Founder 06/10, 23h: "EU NÃO FALEI ISSO"): o agente desce até o PISO SOZINHO, sem aprovação
    # humana, mas PASSO A PASSO (`passo_pp`), nunca direto. De `entrada` até `autonomo_minimo` ele negocia; o trecho
    # `autonomo_minimo` → `piso` (≈ 2 pp) é a ALAVANCA DE FECHAMENTO: guardada para o fim, oferecida em R$ (nunca em %)
    # como a condição que a seguradora devolveu no recálculo, e só com o cliente fechando.
    "comissao": {
        "entrada": 15.0,          # 📊 cliente novo: 15 % (as 4 comerciais, §1.2/§1.3)
        "autonomo_minimo": 12.0,  # 📊 D-MC-68: até 12 % é a negociação normal, passo a passo
        "piso": 10.0,             # 📊 D-MC-64/68: o piso de todas; o agente chega aqui SOZINHO, só como fechamento
        "passo_pp": 1.0,          # 💭 de quanto em quanto a comissão desce (o Founder: "aos poucos, não direto")
    },
    # D-MC-66 — novo COM apólice: mirar 💭 ~10–15 % abaixo do preço atual quando der, guardando margem
    "alvo_abaixo_da_atual_pct": {"minimo": 10.0, "maximo": 15.0},
    # D-MC-66 — renovação: proposta ~15 dias antes; tenta +1–2 pp de comissão sobre a do ano anterior
    "renovacao": {"antecedencia_dias": 15, "comissao_a_mais_pp": {"minimo": 1.0, "maximo": 2.0}},
    # D-MC-71 / D-130A-05 — validade = hoje + a MENOR validade das seguradoras do quadro. 📊 padrão 5 = o menor
    # medido (n = 4). `por_seguradora`: nome da seguradora (como o Agger devolve) → dias. Vazio até medir.
    "validade": {"padrao_dias": 5, "por_seguradora": {}},
    # U7 — o link da página vive a validade da proposta + esta folga 💭
    "link": {"folga_dias": 2},
    # D-MC-71 — 1 lembrete ~24 h depois, em horário comercial, + 1 antes de vencer a validade
    "lembretes": {"primeiro_apos_h": 24, "antes_de_vencer_h": 24, "horario_comercial": {"inicio_h": 9, "fim_h": 18}},
    # U1 — a NOTA 0–100 da opção: pesos 💭 (somam 100)
    "nota": {"pesos": {"preco": 60, "franquia": 25, "coberturas": 15}},
    # D-MC-74 / D-MC-69 / D-130A-09 — quantas opções: 2 no WhatsApp, 3 no carrossel da página
    "opcoes": {"no_whatsapp": 2, "na_pagina": 3},
    # qual CÁLCULO (a opção da porta) alimenta cada papel da proposta. `completa_mais` entra numa fatia própria
    # (o preset e a constraint): sem cálculo dela, a 3ª opção é "Outra completa" (D-130A-09)
    "calculo_por_papel": {"completa": "padrao", "economica": "economica", "completa_mais": "completa_mais",
                          # SPEC-130-A.1 — o "mínimo do mínimo" (D-130A1-05): só o canal pede; mostra a MAIOR economia
                          # possível, sempre com o que deixa de cobrir. Nunca é a recomendada.
                          "minima": "minima"},
    # D-130A-04 — vencedora entre corretoras = a menor completa; empate: estes critérios, nesta ordem
    "desempate_entre_corretoras": ["nota_google", "ordem_de_adesao"],
    # D-MC-63/67 — 📊 128 E5: estas seguradoras OBEDECEM o desconto e IGNORAM a comissão (o botão da margem nelas é
    # o desconto). Casamento pelo nome normalizado (sem acento, minúsculo), começo da palavra.
    "seguradoras_que_obedecem_desconto": ["porto", "azul", "itau"],
    # D-MC-67 ① — o desconto que cada seguradora LIBERA no Agger (`percDesconto`), por nome → %. 📊 não medido:
    # vazio = o passo ① não roda nas que obedecem comissão (a corretora configura quando souber)
    "desconto_permitido_pct": {},
    # D-MC-67 — a ordem do "mais barato" (margem ANTES de cobertura) e o nível de cada corte (rótulos MEDIDOS de
    # `presets.VALORES_DO_AJUSTE`)
    "ordem_do_mais_barato": ["desconto", "comissao", "franquia", "carro_reserva", "vidros", "assistencia"],
    "cortes_de_cobertura": {"franquia": "normal", "carro_reserva": "7 dias", "vidros": "basico",
                            "assistencia": "basica"},
    # D-MC-72 — a cotação-alvo: quantas seguradoras e tentativas por etapa (cada tentativa = 1 recálculo da
    # corretora inteira, ~30–50 s 📊 E7); quais cortes o motor ainda RECOMENDA (com 1 corte só) 💭
    "negociacao": {"max_seguradoras": 3, "max_tentativas_por_etapa": 6,
                   "cortes_recomendaveis": ["franquia", "carro_reserva"]},
    # P-129B-06 / D-130A-03 — produtos de ASSINATURA: o `premio_total` não é prêmio anual e o `premio_mensal` é
    # derivado (premio_total/12) → classe DIFERENTE, preço nunca exibido. Casa por seguradora (igual) ou produto
    # (contém), nomes normalizados.
    "produtos_de_assinatura": [{"seguradora": "Azul Assinatura"}, {"seguradora": "Azul por Assinatura"},
                               {"produto": "assinatura"}],
    # textos da página que a corretora pode trocar (None = o padrão de `manual_de_negociacao`)
    "faq": None,
    "sinistro": None,
    # U4 — prova social: a ficha do Google SÓ quando a corretora a CONFIRMOU (📊 06/10 a busca por nome achou
    # outra empresa para uma das corretoras). {"nota", "avaliacoes", "data", "fonte"} ou None
    "google_confirmado": None,
    # D-MC-55 — o nome do CANAL comparador (marca do PRODUTO, não de corretora). É configuração, não constante da
    # página: a proposta do canal leva `canal.nome` no modelo (laudo do red team, 06/10: RT-10)
    # SPEC-130-A.1 — o canal comparador ao consumidor (marca própria, D-130A1-01): a mensagem pós-cálculo e o follow-up.
    "canal": {
        "nome": "Quem Cobra Menos",
        # 🔴 "Corretora Nível 5" é o selo do PROGRAMA (D-130A1-04): toda corretora que entra no canal cumpre a lista dele;
        # não é medida de porte. A corretora pode desligar o selo na própria config (ex.: enquanto não cumpre a lista).
        "selo": {"nome": "Corretora Nível 5", "ligado": True},
        # quantas seguradoras a mensagem lista em "Melhor preço por seguradora" (o resto está no link)
        "lista_por_seguradora": 6,
        # D-130A1-14 — o tempo da mensagem só aparece até este teto 💭 (acima, some; nunca um tempo menor que o medido).
        # 📊 canário 07/10: último preço aos 495 s (fila do robô + corretoras em série, portal-worker com concorrência 1).
        # SPEC-133-A F0 (Founder 07/10): o teto padrão sobe para 180 s ("em 1,5 minutos" cabe; "8 min" não)
        "tempo_exibido_ate_s": 180,
        # SPEC-133-A F0 (ordem do Founder 07/10 — TESTE CONTROLADO e temporário com o círculo social dele, para medir
        # conversão): "Fiz N Cotações" = `base` + os preços que voltaram nas opções + as tentativas sem preço (erro,
        # recusa, sem resposta) das opções. A base vem SÓ daqui 💭; desligar = `base: 0` (só o real). O real é contado
        # à parte no modelo (`resumo.volume_do_canal`), para a base nunca se confundir com o que aconteceu.
        "volume": {"base": 100},
        # D-130A1-06 — termina com UMA pergunta; sem resposta, até 2 lembretes, nunca mais que isso 💭
        "follow_up": {"primeiro_apos_min": 15, "segundo_apos_h": 24, "max_sem_resposta": 2,
                      "horario_comercial": {"inicio_h": 9, "fim_h": 20}},
        # SPEC-133-A (F1, costura) — o piloto fechado: quantas cotações um número convidado faz por dia 💭 (o convidado
        # pode ter `limite_dia` próprio, que vence) e o teto anti-laço de mensagens NOSSAS por conversa por dia 💭 (a
        # conversa inteira cabe em ~15: consentimento + ~12 perguntas + resultado + pergunta final + 2 lembretes;
        # resultado e lembretes contam).
        "limite_cotacoes_por_dia": 3,
        "teto_mensagens_por_dia": 60,
        # SPEC-133-A (conserto B2) — quanto tempo a pessoa pode ficar em "calculando" com o run vivo 💭: passou disso
        # sem resultado, a conversa SAI (etapa `falhou`, as respostas somem, UMA frase honesta). O run do canal tem
        # teto de acompanhamento de 11 min (`canal/workflows.TETO_DO_ACOMPANHAMENTO_S`) + publicar e mandar.
        "tempo_max_calculando_min": 20,
        # SPEC-133-A (conserto 7) — a conversa parada há mais que isto 💭 tem as respostas apagadas no próximo acesso
        # (o registro do consentimento, append-only em `canal_consentimentos`, fica).
        "retencao_conversa_dias": 30,
        # SPEC-133-A (costura) — a RESERVA do número da conversa do canal (o "Quero fechar" da página volta para ele).
        # O primeiro é SEMPRE o da integração ativa do canal (`canal.envio.numero_do_canal`); vazio = sem reserva.
        "whatsapp": "",
    },
}


# ---------------------------------------------------------------------------------------------------------------------
def normalizar(texto: Any) -> str:
    """Sem acento, minúsculo, espaços simples — a chave de casamento de nomes de seguradora/produto."""
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t).strip()


def casa_seguradora(nome: Any, lista: Iterable[str]) -> bool:
    """`nome` casa um item da lista quando o nome normalizado COMEÇA pela palavra do item ("Porto Seguro" ↔ "porto",
    "Itaú" ↔ "itau"). Começo de palavra, nunca substring solta ("Liberty" não casa "bert")."""
    alvo = normalizar(nome)
    for item in lista or ():
        chave = normalizar(item)
        if chave and (alvo == chave or alvo.startswith(chave + " ")):
            return True
    return False


def _mesclar(base: Any, extra: Any, caminho: str) -> Any:
    if isinstance(base, dict):
        if not isinstance(extra, Mapping):
            logger.warning("[MC-CONFIG] %s: esperado objeto — fica o padrão", caminho or "raiz")
            return base
        saida = dict(base)
        for k, v in extra.items():
            if k not in base:
                logger.info("[MC-CONFIG] chave desconhecida ignorada: %s.%s", caminho, k)
                continue
            # dicionários-tabela (vazios no padrão, ou de chaves livres) entram inteiros
            if isinstance(base[k], dict) and (not base[k] or k in _TABELAS_LIVRES):
                saida[k] = dict(v) if isinstance(v, Mapping) else base[k]
            else:
                saida[k] = _mesclar(base[k], v, f"{caminho}.{k}" if caminho else k)
        return saida
    if base is None:
        return copy.deepcopy(extra)
    if isinstance(base, bool):
        return extra if isinstance(extra, bool) else base
    if isinstance(base, (int, float)):
        if isinstance(extra, bool) or not isinstance(extra, (int, float)) or extra < 0:
            logger.warning("[MC-CONFIG] %s: número inválido — fica o padrão", caminho)
            return base
        return extra
    if isinstance(base, list):
        return list(extra) if isinstance(extra, list) else base
    if isinstance(base, str):
        return extra if isinstance(extra, str) else base
    return base


_TABELAS_LIVRES = frozenset({"por_seguradora", "desconto_permitido_pct"})

#: a TRAVA DE PRODUTO da régua da margem (conserto 130-A.1, red P2 / juiz 4): sem humano no laço (D-MC-68 corrigida),
#: um erro de config chegaria ao consumidor sem ninguém ver. O passo mínimo 💭 0,5 pp (abaixo disso o plano vira
#: centenas de recálculos — 📊 juiz 07/10: passo 0,01 → 504 passos). O piso mínimo é o do PRODUTO (`comissao.piso`).
PASSO_PP_MINIMO = 0.5


def _coerente(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """As réguas que não podem quebrar: piso ≤ autônomo ≤ entrada (todos > 0) · piso ≥ o piso do PRODUTO ·
    `PASSO_PP_MINIMO` ≤ passo ≤ entrada − autônomo · pesos somam 100 · opções ≥ 1. Fora disso: o padrão da seção."""
    pad = PADRAO_DO_PRODUTO
    c = cfg["comissao"]
    piso_do_produto = float(pad["comissao"]["piso"])
    if not (0 < c["piso"] <= c["autonomo_minimo"] <= c["entrada"]) or not (0 < c["passo_pp"] <= c["entrada"]):
        logger.warning("[MC-CONFIG] comissão incoerente (piso ≤ autônomo ≤ entrada) — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    elif c["piso"] < piso_do_produto:
        # o Founder: "até 10 %" — a corretora pode SUBIR o piso dela, nunca descer abaixo do do produto
        logger.warning("[MC-CONFIG] piso da comissão abaixo do piso do produto — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    elif not (PASSO_PP_MINIMO <= c["passo_pp"] <= c["entrada"] - c["autonomo_minimo"]):
        # o passo desce "aos poucos, não direto": nunca menor que o mínimo, nunca maior que o trecho normal inteiro
        logger.warning("[MC-CONFIG] passo da comissão fora de [mínimo, entrada − autônomo] — fica o padrão")
        cfg["comissao"] = copy.deepcopy(pad["comissao"])
    pesos = cfg["nota"]["pesos"]
    if set(pesos) != set(pad["nota"]["pesos"]) or abs(sum(float(v) for v in pesos.values()) - 100.0) > 1e-6:
        logger.warning("[MC-CONFIG] pesos da nota não somam 100 — fica o padrão")
        cfg["nota"] = copy.deepcopy(pad["nota"])
    a = cfg["alvo_abaixo_da_atual_pct"]
    if not (0 <= a["minimo"] <= a["maximo"] < 100):
        cfg["alvo_abaixo_da_atual_pct"] = copy.deepcopy(pad["alvo_abaixo_da_atual_pct"])
    for k in ("no_whatsapp", "na_pagina"):
        if int(cfg["opcoes"][k]) < 1:
            cfg["opcoes"][k] = pad["opcoes"][k]
    if int(cfg["validade"]["padrao_dias"]) < 1:
        cfg["validade"]["padrao_dias"] = pad["validade"]["padrao_dias"]
    return cfg


def mesclar(linha: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """O padrão ⊕ a config de uma corretora (puro — o que `carregar` usa depois de ler o banco)."""
    base = copy.deepcopy(PADRAO_DO_PRODUTO)
    if not linha:
        return base
    return _coerente(_mesclar(base, linha, ""))


def carregar(company_id: str, *, db: Any) -> Dict[str, Any]:
    """A config EFETIVA da corretora: `PADRAO_DO_PRODUTO` ⊕ a linha dela em `multicalculo_config`.

    🔴 Filtro `company_id` AQUI (o backend usa service role; a RLS sem policy não protege erro de filtro — §7).
    Sem linha → o padrão. Banco fora → `ConfigIndisponivel` (nunca o padrão às cegas: o piso dela pode ser maior)."""
    cid = str(company_id or "").strip()
    if not _UUID.match(cid):
        raise ValueError("company_id precisa ser um uuid")
    cid = cid.lower()
    try:
        resp = db.table(TABELA).select("company_id, config").eq("company_id", cid).limit(1).execute()
    except Exception as exc:  # noqa: BLE001
        raise ConfigIndisponivel(f"multicalculo_config ilegível ({type(exc).__name__})") from None
    linhas = list(getattr(resp, "data", None) or [])
    linha = next((l for l in linhas if str(l.get("company_id", "")).lower() == cid), None)
    return mesclar((linha or {}).get("config") if linha else None)


def validade_dias(config: Mapping[str, Any], seguradoras: Iterable[str]) -> int:
    """D-MC-71: a MENOR validade entre as seguradoras do quadro (dias por seguradora na config; senão o padrão)."""
    val = config["validade"]
    tabela = {normalizar(k): v for k, v in (val.get("por_seguradora") or {}).items()}
    dias = [int(tabela.get(normalizar(s), val["padrao_dias"])) for s in seguradoras]
    return min(dias) if dias else int(val["padrao_dias"])


def e_produto_de_assinatura(seguradora: Any, produto: Any, config: Mapping[str, Any]) -> bool:
    seg, prod = normalizar(seguradora), normalizar(produto)
    for regra in config.get("produtos_de_assinatura") or ():
        if not isinstance(regra, Mapping):
            continue
        s, p = normalizar(regra.get("seguradora")), normalizar(regra.get("produto"))
        if (s and seg == s) or (p and p in prod):
            return True
    return False
