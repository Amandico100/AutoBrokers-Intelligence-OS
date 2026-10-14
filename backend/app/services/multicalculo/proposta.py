# -*- coding: utf-8 -*-
"""A PROPOSTA — SPEC-130-A U4 + U7 (a costura F3): do pedido do motor ao link `/r/` que o segurado abre.

    montar_proposta(...)    → dict   o MODELO da página (CONTRATO §5, `tests/fixtures/proposta/modelo_contrato.json`)
    publicar_proposta(...)  → dict   {url, token, artifact_id, versao, mensagem} — o artefato `proposal.quote`
                                     criado → renderizado → publicado → compartilhado, e a mensagem do WhatsApp

O fio, elo a elo:
    porta.consultar (company_id do SOLICITANTE: a porta corta a comissão de quem não é dono e esconde a corretora sem
    adesão ativa) → comparacao.comparar (o quadro inteiro: quem VENCE entre as corretoras) → comparacao.comparar só da
    ANFITRIÃ (ranking, produto diferente, não responderam, o resumo que fecha a conta) → comparacao.opcoes → o modelo
    (bem, anfitriã com a marca PUBLICADA, FAQ do caso, sinistro, validade, nível por cobertura, juros com nome,
    arredondamento único) → ArtifactService (no SOLICITANTE, D-130A-10) → mensagem.mensagem_para(link) (a do canal ou
    a da carteira, pela ORIGEM — SPEC-130-A.1 D-130A1-01).

🔴 Regras que moram aqui:
  · a ANFITRIÃ é a vencedora no pedido do canal e a própria corretora no pedido dela. A página mostra o quadro DELA
    (ela fecha o que mostra); a perdedora só aparece em `entre_corretoras`, SEM nome (D-MC-55).
  · a marca da anfitriã vai no MODELO, lida de `brand_profiles` PUBLICADO; o artefato mora no solicitante e a anfitriã
    nunca recebe linha (D-130A-10). Sem marca publicada → `marca_cadastrada=False`, sem cores nem logo.
  · prova social só confirmada: o Google vem da config da anfitriã (`google_confirmado`), nunca de busca por nome.
  · a comissão nunca chega ao modelo (G3): o modelo é conferido por chave antes de sair (`_sem_comissao`).
  · todo número COMERCIAL vem da config (G8): validade, folga do link, quantas opções.

`db` é o cliente PostgREST (`get_supabase_client().client`). A porta é assíncrona; estas duas também.
"""
from __future__ import annotations

import base64
import binascii
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from app.services.multicalculo import comparacao as CMP
from app.services.multicalculo import config as CFG
from app.services.multicalculo import manual_de_negociacao as MANUAL
from app.services.multicalculo.porta import KIND_CANAL, OPCOES as OPCOES_DO_PEDIDO, MulticalculoProvider, NaoEncontrado
from app.services.multicalculo.repositorio import RepositorioMulticalculo

logger = logging.getLogger(__name__)

VERSAO_DO_CONTRATO = 1
TEMPLATE_DA_PROPOSTA = "proposal.quote"
#: o logo embutido na página: só imagem, e no máximo isto (📊 06/10 o logo publicado em produção é um PNG de ~6 KB)
TETO_DO_LOGO_BYTES = 256 * 1024
_MIMES_DE_LOGO = ("image/png", "image/jpeg", "image/webp", "image/gif")
#: a nota do Google vai de 1 a 5 estrelas (escrita assim para o G8: o 5 dos números comerciais é outro)
ESCALA_DO_GOOGLE = float(len("★★★★★"))

AVISO_LEGAL_CORRETORA = ("Comparação feita com os preços que as seguradoras devolveram no cálculo. O preço final "
                         "depende da aceitação da seguradora e da vistoria, se houver. A contratação é feita pela "
                         "corretora, registrada na SUSEP.")
AVISO_LEGAL_CANAL = ("Comparação independente feita com os preços que as seguradoras devolveram no cálculo, nas "
                     "corretoras parceiras. O preço final depende da aceitação da seguradora e da vistoria, se houver. "
                     "A contratação é feita pela corretora parceira que teve o menor preço, registrada na SUSEP.")


class PropostaImpossivel(LookupError):
    """O pedido não tem o que propor (nenhuma oferta completa da anfitriã). Nada é gravado."""


class LinkSemEndereco(RuntimeError):
    """Sem o endereço público do painel o link nasceria sem host — recusado ANTES de gravar."""


class SemCanalDeFechamento(RuntimeError):
    """J-B1 (juiz, 06/10): a anfitriã não tem WhatsApp de atendimento — a página sairia sem "Quero fechar" e o
    segurado sem como fechar. Recusado ANTES de gravar, salvo `permitir_sem_whatsapp=True` explícito."""


# =====================================================================================================================
# o relógio e o dinheiro
# =====================================================================================================================
def _fuso_do_brasil():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo("America/Sao_Paulo")
    except Exception:  # noqa: BLE001 — sem tzdata: o Brasil não tem horário de verão desde 2019
        return datetime.strptime("-0300", "%z").tzinfo


_FUSO = _fuso_do_brasil()


def _agora(agora: Optional[datetime]) -> datetime:
    a = agora or datetime.now(timezone.utc)
    return (a if a.tzinfo else a.replace(tzinfo=timezone.utc)).astimezone(_FUSO)


def reais_inteiros(v: Any) -> str:
    """R$ em reais INTEIROS, meio para cima (a regra ÚNICA dos textos derivados: `int(v + 0,5)`)."""
    f = float(v)
    n = int(abs(f) + 0.5)
    return ("-" if f < 0 and n else "") + "R$ " + f"{n:,}".replace(",", ".")


_RE_REAIS_COM_CENTAVOS = re.compile(r"(?<!x de )R\$ (\d{1,3}(?:\.\d{3})*),(\d{2})\b")


def arredondar_texto(texto: str) -> str:
    """Troca todo "R$ 1.234,56" de um texto DERIVADO por "R$ 1.235" — menos o valor da PARCELA ("10x de R$ 555,83"),
    que é um fato da seguradora, não uma conta nossa."""
    def troca(m: "re.Match[str]") -> str:
        inteiro = int(m.group(1).replace(".", ""))
        return reais_inteiros(inteiro + int(m.group(2)) / 100)

    return _RE_REAIS_COM_CENTAVOS.sub(troca, str(texto))


# =====================================================================================================================
# as peças do modelo
# =====================================================================================================================
def _so_leitura(_texto: str) -> str:
    raise RuntimeError("a proposta só LÊ a porta — nunca cifra nem grava pedido")


def _uuid(valor: Any, nome: str) -> str:
    texto = str(valor or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", texto):
        raise ValueError(f"{nome} precisa ser um uuid")
    return texto


def _dados(resp: Any) -> List[Dict[str, Any]]:
    d = getattr(resp, "data", None) if resp is not None else None
    if isinstance(d, dict):
        return [d]
    return list(d or [])


def _primeiro_nome(nome: Any) -> Optional[str]:
    partes = re.findall(r"[^\W\d_][^\W\d_'’-]*(?:['’-][^\W\d_]+)*", str(nome or ""))
    return partes[0][:40].capitalize() if partes else None


def _digitos_de_whatsapp(valor: Any) -> Optional[str]:
    """Um número de WhatsApp a partir de "+55 48 9…", "5548…" ou "https://wa.me/5548…". Sem DDI → +55."""
    texto = str(valor or "").strip()
    if not texto:
        return None
    m = re.search(r"wa\.me/(\+?\d+)", texto) or re.search(r"[?&]phone=(\+?\d+)", texto)
    dig = re.sub(r"\D", "", m.group(1) if m else texto)
    if re.fullmatch(r"\d{10,11}", dig):            # DDD + número, sem o país
        dig = "55" + dig
    return dig if re.fullmatch(r"\d{12,15}", dig) else None


#: o que a seguradora escreve no modelo e o segurado não precisa ler: tração (4X2), válvulas (16V), portas (4P)
_RE_FICHA_TECNICA = re.compile(r"^(?:\d+x\d+|\d{1,2}v|\d\s?p)$", re.I)
#: as palavras de motor/câmbio, por extenso e em minúscula (a chave é o texto sem acento e sem pontuação)
_PALAVRAS_DO_MOTOR = {"flex": "flex", "aut": "automático", "automatico": "automático", "automatica": "automático",
                      "mec": "manual", "manual": "manual", "turbo": "turbo", "tb": "turbo", "diesel": "diesel",
                      "gasolina": "gasolina", "hibrido": "híbrido", "eletrico": "elétrico"}


def descricao_do_veiculo(bruto: Any) -> str:
    """O modelo como o segurado o chama, a partir do texto CRU da seguradora (crítico final, 06/10):
    "COMPASS LIMITED 2.0 4X2 FLEX 16V AUT." → "Compass Limited 2.0 flex automático". Regras simples: tira a ficha
    técnica (tração, válvulas, portas), escreve motor/câmbio por extenso em minúscula, nome com inicial maiúscula
    (sigla sem vogal fica em maiúscula: LTZ), mantém a cilindrada. Nunca acrescenta o que não veio (marca, ano)."""
    saida: List[str] = []
    for bruto_p in str(bruto or "").split():
        t = bruto_p.strip(".,;:")
        if not t or _RE_FICHA_TECNICA.match(t):
            continue
        chave = CFG.normalizar(t)
        if chave in _PALAVRAS_DO_MOTOR:
            if _PALAVRAS_DO_MOTOR[chave] not in saida:
                saida.append(_PALAVRAS_DO_MOTOR[chave])
        elif re.fullmatch(r"\d+(?:[.,]\d+)?", t):
            saida.append(t.replace(",", "."))
        elif t.isalpha():
            saida.append(t.upper() if not re.search(r"[aeiouáéíóúâêôãõ]", t, re.I) else t.capitalize())
        else:
            saida.append(t.upper())
    return " ".join(saida)


def _bem(ofertas: Sequence[Mapping[str, Any]], ramo: int) -> Optional[Dict[str, Any]]:
    """O que foi cotado, da OFERTA (`coberturas.modeloSelecionado`) — o pedido é cifrado e a proposta não o decifra."""
    modelos = Counter(str((o.get("coberturas") or {}).get("modeloSelecionado") or "").strip()
                      for o in ofertas if isinstance(o.get("coberturas"), Mapping))
    modelos.pop("", None)
    if not modelos:
        return None
    descricao = descricao_do_veiculo(modelos.most_common(1)[0][0])
    if not descricao:
        return None
    apelido = next((p for p in descricao.split() if p.isalpha() and len(p) > 2 and p[:1].isupper()), None)
    return {"rotulo": "carro" if int(ramo) == CMP.RAMO_AUTO else None, "descricao": descricao, "apelido": apelido}


def _parcelas_sem_juros(oferta: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """A MAIOR quantidade de parcelas cujo total bate com o prêmio (diferença < R$ 1) — senão None (tem juros)."""
    try:
        premio = float(oferta.get("premio_total"))
    except (TypeError, ValueError):
        return None
    melhor = None
    for p in oferta.get("parcelamentos") or ():
        if not isinstance(p, Mapping):
            continue
        try:
            vezes = int(p.get("parcelas"))
            valor = float(p.get("demais_parcelas") or p.get("primeira_parcela"))
            primeira = float(p.get("primeira_parcela") or valor)
        except (TypeError, ValueError):
            continue
        if vezes < 2 or valor <= 0:
            continue
        total = primeira + valor * (vezes - 1)
        if abs(total - premio) < 1.0 and (melhor is None or vezes > melhor["vezes"]):
            melhor = {"vezes": vezes, "valor": round(valor, 2)}
    return melhor


#: SPEC-133-A.1 F1 — quanto o total de um parcelamento pode passar do prêmio e ainda ser SEM juros (arredondamento de
#: centavos). 📊 10/10/2026, os 2.862 parcelamentos (≥ 2x) das 104 ofertas reais da fixture do canário: a diferença
#: total − prêmio fica em [−0,049 %, +0,024 %] (centavos: Tokio 12x −R$ 1,58, Zurich 12x +R$ 1,10) ou é ≥ +0,99 % (juros:
#: Liberty 2x +R$ 71,81) — nada entre os dois. 0,25 % fica no vão. O `_parcelas_sem_juros` da carteira (|dif| < R$ 1)
#: NÃO muda (D-133A1-01) — e por isso chama de "com juros" o 12x da Tokio que é mais barato que o prêmio.
TOLERANCIA_SEM_JUROS = 0.0025


def _e_sem_juros(total: float, premio: Optional[float]) -> Optional[bool]:
    if premio is None or premio <= 0:
        return None
    return total - premio <= max(1.0, premio * TOLERANCIA_SEM_JUROS)


def _parcelamentos_do_canal(oferta: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Os parcelamentos de 2x ou mais da oferta, em QUALQUER forma de pagamento: vezes, valor (as demais), total
    (1ª + demais × (vezes − 1)) e se é sem juros (`_e_sem_juros`)."""
    try:
        premio: Optional[float] = float(oferta.get("premio_total"))
    except (TypeError, ValueError):
        premio = None
    saida = []
    for p in oferta.get("parcelamentos") or ():
        if not isinstance(p, Mapping):
            continue
        try:
            vezes = int(p.get("parcelas"))
            valor = round(float(p.get("demais_parcelas") or p.get("primeira_parcela")), 2)
            primeira = float(p.get("primeira_parcela") or valor)
        except (TypeError, ValueError):
            continue
        if vezes < 2 or valor <= 0:
            continue
        total = round(primeira + valor * (vezes - 1), 2)
        saida.append({"vezes": vezes, "valor": valor, "total": total, "sem_juros": _e_sem_juros(total, premio)})
    return saida


def _parcela_menor(oferta: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """SPEC-133-A.1 F1 (Founder 10/10, só o CANAL — D-133A1-01): a MENOR parcela que a oferta trouxe, em qualquer forma
    de pagamento, com ou sem juros (o menor valor; empate → mais vezes, e sem juros antes de com juros). As vezes são as
    da seguradora — 📊 10/10: a Youse do pedido d0bb15ba só devolve 1x..4x, então ali a menor é 4x; nunca um 12
    inventado. Sem parcelamento de 2x ou mais → None (a página mostra o à vista no topo)."""
    todas = _parcelamentos_do_canal(oferta)
    return dict(min(todas, key=lambda p: (p["valor"], -p["vezes"], p["sem_juros"] is not True))) if todas else None


def _parcela_sem_juros_maior(oferta: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """SPEC-133-A.1 F1 (só o CANAL): o MAIOR número de parcelas SEM juros que a seguradora mandou (empate → a menor
    parcela). Sem nenhum sem juros de 2x ou mais → None (a linha some)."""
    sj = [p for p in _parcelamentos_do_canal(oferta) if p["sem_juros"] is True]
    if not sj:
        return None
    p = max(sj, key=lambda p: (p["vezes"], -p["valor"]))
    return {"vezes": p["vezes"], "valor": p["valor"]}


def _total_do_parcelamento(oferta: Mapping[str, Any], parcelas: Any) -> Optional[float]:
    """O TOTAL do parcelamento que a opção mostra, como a SEGURADORA o devolveu: 1ª parcela + demais × (vezes − 1),
    do mesmo parcelamento (mesmas vezes e mesmo valor). Sem esse parcelamento na oferta → None (a mensagem usa
    vezes × valor). Conserto 130-A.1: a 1ª parcela diferente não some do total (juiz, pendência 9)."""
    if not isinstance(parcelas, Mapping):
        return None
    try:
        vezes, valor = int(parcelas.get("vezes")), round(float(parcelas.get("valor")), 2)
    except (TypeError, ValueError):
        return None
    for p in oferta.get("parcelamentos") or ():
        if not isinstance(p, Mapping):
            continue
        try:
            v = int(p.get("parcelas"))
            demais = float(p.get("demais_parcelas") or p.get("primeira_parcela"))
            primeira = float(p.get("primeira_parcela") or demais)
        except (TypeError, ValueError):
            continue
        if v == vezes and round(demais, 2) == valor and v >= 1:
            return round(primeira + demais * (v - 1), 2)
    return None


def _quantidades(cob: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    """O que dá para ORDENAR em cada cobertura (maior = melhor). None = a seguradora não informou."""
    def num(v: Any) -> Optional[float]:
        if v is None or isinstance(v, bool):
            return None
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if f >= 0 else None

    km, ilimitado = CMP.guincho(cob)
    dm, dc = num(cob.get("isDanosMateriais")), num(cob.get("isDanosCorporais"))
    reserva = CMP.dias_de_carro_reserva(cob)
    return {
        "casco": num(cob.get("casco")),
        "terceiros": (dm + dc) if dm is not None and dc is not None else None,
        "vidros": None if CMP.nivel_de_vidros(cob) is None else float(CMP.nivel_de_vidros(cob)),
        "reserva": None if reserva is None else float(reserva),
        "assistencia": float("inf") if ilimitado else km,
        "app": num(cob.get("isAppMorte")),
        "morais": num(cob.get("isDanosMorais")),
    }


def _niveis(opcoes: List[Dict[str, Any]], brutas: List[Mapping[str, Any]]) -> None:
    """`coberturas[].nivel` = posição DENSA (1 = a menor) entre as opções da página; None = desconhecido."""
    qs = [_quantidades(b) for b in brutas]
    for chave in {c["chave"] for o in opcoes for c in o["coberturas"]}:
        valores = sorted({q.get(chave) for q in qs if q.get(chave) is not None})
        for o, q in zip(opcoes, qs):
            for c in o["coberturas"]:
                if c["chave"] == chave:
                    v = q.get(chave)
                    c["nivel"] = (valores.index(v) + 1) if v is not None else None


def _sem_carro_reserva(qa: Mapping[str, Any], qr: Mapping[str, Any], *, minima: bool) -> bool:
    """A MESMA leitura de `comparacao._o_que_muda` (a página): 0 dias contra uma referência com dias → sem carro
    reserva; a MÍNIMA (pedida sem carro reserva, D-130A1-05) que não informa os dias → sem carro reserva (a leitura que
    cobre MENOS, nunca a que promete a mais). Conserto 130-A.1 (red B1): a página e a mensagem dizem o mesmo."""
    a, r = qa.get("reserva"), qr.get("reserva")
    if a is not None and r is not None:
        return a == 0 and r > 0
    return minima and not a and r != 0


def _por_que_mais_barata(op: Mapping[str, Any], ref: Mapping[str, Any], bruta: Mapping[str, Any],
                         bruta_ref: Mapping[str, Any], *, minima: bool = False) -> Optional[str]:
    """Uma frase de FATOS: o que a opção mais em conta tem de diferente da referência (só o que pesa contra ela).
    "sem carro reserva" (zero dias, ou a mínima que não informa) vem PRIMEIRO — é o corte que define a mínima e o que
    sobra quando a mensagem encurta; "menos dias de carro reserva" só quando ainda há dias."""
    partes: List[str] = []
    qa, qr = _quantidades(bruta.get("coberturas") or {}), _quantidades(bruta_ref.get("coberturas") or {})
    sem_reserva = _sem_carro_reserva(qa, qr, minima=minima)
    if sem_reserva:
        partes.append("sem carro reserva")
    fv, fr = (op.get("franquia") or {}).get("valor"), (ref.get("franquia") or {}).get("valor")
    if fv is not None and fr is not None and fv > fr + 0.5:
        tipo = str((op.get("franquia") or {}).get("tipo") or "").strip().lower()
        dobro = " (o dobro)" if fr > 0 and abs(fv / fr - 2) < 0.05 else ""
        partes.append(f"franquia {tipo + ' ' if tipo else 'maior '}de {reais_inteiros(fv)}{dobro}".replace("  ", " "))
    for chave, texto in (("vidros", "vidros mais simples"), ("reserva", "menos dias de carro reserva"),
                         ("assistencia", "assistência mais simples"), ("terceiros", "menos cobertura para terceiros")):
        if chave == "reserva" and sem_reserva:
            continue
        if qa[chave] is not None and qr[chave] is not None and qa[chave] < qr[chave]:
            partes.append(texto)
    if not partes:
        return None
    rot = str(ref.get("rotulo") or "recomendada").lower()
    inicio = (f"Mesma {op['seguradora']} da {rot}" if op.get("seguradora") == ref.get("seguradora")
              else f"{op['seguradora']}")
    corpo = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
    return f"{inicio}, com {corpo}."


_RE_PARCELA_NO_MOTIVO = re.compile(r"^Em até (\d+)x de R\$ [\d.]+(?:,\d{2})?$")


def _texto_de_parcela(motivo: str, sem_juros: Optional[Mapping[str, Any]]) -> str:
    """A parcela nunca sai sem dizer se tem juros (o desenho aprovado: "juros com nome")."""
    m = _RE_PARCELA_NO_MOTIVO.match(motivo)
    if not m:
        return motivo
    if sem_juros and int(m.group(1)) == int(sem_juros["vezes"]):
        return f"{motivo} sem juros"
    return f"{motivo} com juros"


def _sem_comissao(obj: Any, caminho: str = "modelo") -> None:
    """🔴 G3: nenhuma chave com "comiss" sai no modelo (o comparador já não copia; isto é a cerca de saída)."""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if "comiss" in str(k).lower():
                raise AssertionError(f"comissão no modelo da proposta: {caminho}.{k}")
            _sem_comissao(v, f"{caminho}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _sem_comissao(v, f"{caminho}[{i}]")


# =====================================================================================================================
# a anfitriã — a marca PUBLICADA, o logo embutido, o WhatsApp, a prova social confirmada
# =====================================================================================================================
BaixarLogo = Callable[[str], Awaitable[Tuple[Optional[bytes], str]]]


def _tipo_da_imagem(dados: bytes) -> Optional[str]:
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if dados.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if dados.startswith(b"RIFF") and dados[8:].startswith(b"WEBP"):
        return "image/webp"
    return None


def _data_url(dados: Optional[bytes]) -> Optional[str]:
    """Só IMAGEM rasterizada (os bytes dizem o tipo, não o cabeçalho) e só até o teto. SVG fica fora: é documento."""
    if not dados or len(dados) > TETO_DO_LOGO_BYTES:
        return None
    tipo = _tipo_da_imagem(dados)
    if tipo not in _MIMES_DE_LOGO:
        return None
    return f"data:{tipo};base64," + base64.b64encode(dados).decode("ascii")


async def _baixar_logo_padrao(url: str) -> Tuple[Optional[bytes], str]:
    """O download com o guarda de egresso do produto (SPEC-054: allowlist da própria URL, redirect revalidado)."""
    from app.services.brand.web import baixar_binario

    return await baixar_binario(url)


async def logo_embutido(storage_ref: Any, *, baixar: Optional[BaixarLogo] = None) -> Optional[str]:
    """O logo como `data:` — de um `data:` já guardado ou de uma URL https (baixada pelo guarda de egresso)."""
    ref = str(storage_ref or "").strip()
    if not ref:
        return None
    if ref.startswith("data:"):
        m = re.fullmatch(r"data:[\w.+-]+/[\w.+-]+;base64,([A-Za-z0-9+/=\s]+)", ref, re.S)
        if not m:
            return None
        try:
            return _data_url(base64.b64decode(re.sub(r"\s+", "", m.group(1)), validate=True))
        except (binascii.Error, ValueError):
            return None
    if not ref.lower().startswith("https://"):
        return None
    try:
        dados, _tipo = await (baixar or _baixar_logo_padrao)(ref)
    except Exception as exc:  # noqa: BLE001 — sem logo a página sai com o monograma; nunca cai por isso
        logger.warning("[PROPOSTA] logo da anfitriã não baixou: %s", type(exc).__name__)
        return None
    return _data_url(dados)


def _whatsapp_da_anfitria(db: Any, company_id: str, marca: Optional[Mapping[str, Any]]) -> Optional[str]:
    """O número que recebe o "Quero fechar", nesta ordem:
    1. o WhatsApp DECLARADO na marca publicada (`contact.whatsapp`);
    2. a integração de ATENDIMENTO ativa e pareada (`integrations.purpose='attendance'`).
    ⛔ O número do OBSERVADOR (`purpose='observer'`) não entra: é o espelho da conversa, não o canal de venda."""
    if marca:
        dig = _digitos_de_whatsapp((marca.get("contact") or {}).get("whatsapp"))
        if dig:
            return dig
    try:
        # N1 (131-B K3): ORDEM FIXA — com 2+ integrações de atendimento ativas, a leitura sem ORDER BY podia trocar de
        # número entre duas chamadas, `quem_atende_mudou` dava True e cada envio republicava a página. A mais antiga
        # vence (`created_at`, depois `id` no empate) — a mesma em toda leitura.
        linhas = _dados(db.table("integrations").select("id, created_at, paired_phone_e164, purpose, is_active")
                        .eq("company_id", company_id).eq("purpose", "attendance").eq("is_active", True)
                        .order("created_at").order("id")
                        .limit(64).execute())   # o teto da leitura (o G8 proíbe os números da config — 50 virou o teto da comissão)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PROPOSTA] integrações ilegíveis: %s", type(exc).__name__)
        return None
    for l in linhas:
        if str(l.get("purpose")) == "attendance" and l.get("is_active") is True:
            dig = _digitos_de_whatsapp(l.get("paired_phone_e164"))
            if dig:
                return dig
    return None


def whatsapp_do_canal(db: Any, company_id: str, cfg: Mapping[str, Any]) -> Optional[str]:
    """SPEC-133-A (costura) — o número da CONVERSA do canal, para onde o "Quero fechar" da página do canal volta:
    1. o `paired_phone_e164` da integração ATIVA do próprio canal (`canal.envio.numero_do_canal` — a MESMA escolha
       por onde os balões saem; nunca uma 2ª busca);
    2. a reserva da config do canal (`canal.whatsapp`).
    Sem nenhum → None (a página sai sem o botão)."""
    try:
        from app.services.canal.envio import numero_do_canal

        dig = numero_do_canal(db, company_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PROPOSTA] número do canal ilegível: %s", type(exc).__name__)
        dig = None
    return dig or _digitos_de_whatsapp((cfg.get("canal") or {}).get("whatsapp"))


def numero_do_fechar(modelo: Mapping[str, Any]) -> Optional[str]:
    """Para onde o "Quero fechar" da página vai: no canal, a conversa do canal (D-133A-13); na carteira, a corretora."""
    if modelo.get("origem") == "canal":
        return (modelo.get("canal") or {}).get("whatsapp")
    return (modelo.get("anfitria") or {}).get("whatsapp")


def _site(url: Any) -> Optional[str]:
    m = re.match(r"^\s*(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})(?:[/:?#]|\s*$)", str(url or ""), re.I)
    return m.group(1).lower() if m else None


def _google(cfg: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    g = cfg.get("google_confirmado")
    if not isinstance(g, Mapping):
        return None
    try:
        nota, avaliacoes = float(g.get("nota")), int(g.get("avaliacoes"))
    except (TypeError, ValueError):
        return None
    if not (0 < nota <= ESCALA_DO_GOOGLE) or avaliacoes < 1:
        return None
    fonte = ", ".join(str(x).strip() for x in (g.get("fonte") or "Google", g.get("data")) if x and str(x).strip())
    return {"nota": nota, "avaliacoes": avaliacoes, "fonte": fonte}


def _marca_publicada(perfil: Optional[Mapping[str, Any]]) -> bool:
    """A marca vale na página só PUBLICADA e com os dois temas (o mesmo critério para o nome, a cor e o número)."""
    temas = ((perfil or {}).get("palette") or {}).get("themes") or {}
    return bool(perfil and perfil.get("is_published") is True and temas.get("light") and temas.get("dark"))


async def montar_anfitria(db: Any, company_id: str, cfg: Mapping[str, Any], *,
                          baixar_logo: Optional[BaixarLogo] = None) -> Dict[str, Any]:
    """A anfitriã do modelo. 🔴 Filtro `company_id` em toda leitura (service role — CLAUDE.md §7)."""
    emp = _dados(db.table("companies").select("id, company_name").eq("id", company_id).limit(1).execute())
    nome_oficial = str((emp[0] if emp else {}).get("company_name") or "").strip() or None
    perfis = _dados(db.table("brand_profiles").select("*").eq("company_id", company_id).limit(1).execute())
    perfil = next((p for p in perfis if str(p.get("company_id")) == company_id), None)
    temas = ((perfil or {}).get("palette") or {}).get("themes") or {}
    publicada = _marca_publicada(perfil)

    anf: Dict[str, Any] = {"nome": nome_oficial, "marca_cadastrada": publicada}
    if publicada:
        pal = perfil.get("palette") or {}
        anf["nome"] = str(perfil.get("display_name") or "").strip() or nome_oficial
        anf["cores"] = {"primaria": pal.get("primary"), "acento": pal.get("accent")}
        anf["tema_claro"], anf["tema_escuro"] = temas["light"], temas["dark"]
        if perfil.get("logo_asset_id"):
            ativos = _dados(db.table("brand_assets").select("id, storage_ref, mime_type")
                            .eq("id", str(perfil["logo_asset_id"])).eq("company_id", company_id).limit(1).execute())
            if ativos:
                anf["logo_data_url"] = await logo_embutido(ativos[0].get("storage_ref"), baixar=baixar_logo)
        for chave, campo in (("cidade", "service_area"), ("tagline", "tagline")):
            v = str(perfil.get(campo) or "").strip()
            if v:
                anf[chave] = v
        if isinstance(perfil.get("founded_year"), int) and not isinstance(perfil.get("founded_year"), bool):
            anf["desde"] = perfil["founded_year"]
        if str(perfil.get("susep_code") or "").strip():
            anf["susep"] = str(perfil["susep_code"]).strip()
        if _site(perfil.get("website_url")):
            anf["site"] = _site(perfil.get("website_url"))
    g = _google(cfg)
    if g:
        anf["google"] = g
    anf["whatsapp"] = _whatsapp_da_anfitria(db, company_id, perfil if publicada else None)
    return {k: v for k, v in anf.items() if v is not None}


# =====================================================================================================================
# a FAQ do caso — as objeções reais, com os números DESTE quadro, só sobre opções que existem
# =====================================================================================================================
def _faq(cfg_anf: Mapping[str, Any], *, resumo: Mapping[str, Any], opcoes: List[Dict[str, Any]],
         situacao: str, voz: str = "corretora", com_whatsapp: bool = True) -> List[Dict[str, str]]:
    base = MANUAL.faq_padrao(cfg_anf, voz=voz, com_whatsapp=com_whatsapp)
    if MANUAL.faq_da_corretora(cfg_anf):                                       # a FAQ da corretora vale inteira
        return [{"p": i["pergunta"], "r": i["resposta"]} for i in base]
    por_pergunta = {}
    for chave in ("melhorar_preco", "reduzir_franquia", "outras_seguradoras", "qual_tenho_hoje", "banco_cooperativa",
                  "endosso_concessionaria", "parcelar_mais", "sinistro_quem_ligo", "uso_aplicativo"):
        o = MANUAL.objecao(chave)
        if o:
            por_pergunta[o["pergunta"]] = chave
    ids = {o["id"]: o for o in opcoes}
    saida = []
    for item in base:
        chave = por_pergunta.get(item["pergunta"])
        resposta = item["resposta"]
        if chave == "qual_tenho_hoje" and not ({"igual_a_atual", "sua_renovacao"} & set(ids)):
            continue                                            # só sobre opções que EXISTEM
        if chave == "outras_seguradoras" and resumo.get("seguradoras_cotadas"):
            resposta += (f" Nesta cotação: {resumo['seguradoras_cotadas']} seguradoras consultadas, "
                         f"{resumo.get('com_preco_comparavel', 0)} com preço para a mesma cobertura completa.")
        if chave == "reduzir_franquia" and "menor_franquia" in ids:
            o = ids["menor_franquia"]
            fv = (o.get("franquia") or {}).get("valor")
            if fv:
                resposta += f" Compare a opção “Menor franquia”: {o['seguradora']}, franquia de {reais_inteiros(fv)}."
        if chave == "parcelar_mais" and opcoes and opcoes[0].get("parcelas"):
            resposta += f" A opção “{opcoes[0]['rotulo']}” vai até {opcoes[0]['parcelas']['vezes']}x."
        saida.append({"p": item["pergunta"], "r": arredondar_texto(resposta)})
    return saida


def cta_da_pagina(destino: Optional[str], opcoes: Sequence[Mapping[str, Any]], *, nome: Optional[str],
                  ref_curta: str, renovacao: bool = False) -> Optional[Dict[str, Any]]:
    """O "Quero fechar" / "Quero renovar" da página: o número e o texto de cada opção. Sem número → None (sem botão)."""
    if not destino:
        return None
    ola = f"Olá!{' Aqui é ' + nome + '.' if nome else ''}"
    textos = {}
    for o in opcoes:
        preco = reais_inteiros(o["premio_anual"])
        if renovacao:                           # SPEC-131-B: quem JÁ é cliente renova, não "fecha"
            textos[o["id"]] = (f"{ola} Quero renovar o meu seguro na opção {o['rotulo']} ({o['seguradora']}, "
                               f"{preco} por ano). Ref. {ref_curta}")
        else:
            textos[o["id"]] = (f"{ola} Quero fechar a opção {o['rotulo']} "
                               f"({o['seguradora']}, {preco} por ano). Ref. {ref_curta}")
    return {"whatsapp_url": f"https://wa.me/{destino}", "texto_por_opcao": textos}


def pct_br(v: Any) -> str:
    """O percentual em português: vírgula decimal, uma casa no máximo e sem ",0"."""
    f = round(float(v), 1)
    return (str(int(f)) if f.is_integer() else f"{f:.1f}".replace(".", ",")) + " %"


def _data_br(iso: Any) -> Optional[str]:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return None
    ano, mes, dia = m.groups()
    return f"{dia}/{mes}/{ano}"


def faq_da_renovacao(*, ramo: int, opcoes: Sequence[Mapping[str, Any]], vence_em: Any = None,
                     reajuste_pct: Optional[float] = None, com_whatsapp: bool = True) -> List[Dict[str, str]]:
    """SPEC-131-B (laudo I3 §2.3): as dúvidas de quem JÁ é cliente — reajuste, bônus, mudar a franquia, se não renovar,
    parcelar. Só afirma o que é verdade para qualquer corretora e o que ESTA página mostra; as objeções de cliente
    novo (banco/cooperativa, "outras seguradoras") ficam na cotação (D-131-40)."""
    auto = int(ramo) == CMP.RAMO_AUTO
    ids = {str(o.get("id")): o for o in opcoes}
    falar = "Me responda por aqui" if com_whatsapp else "Fale com a corretora"
    saida: List[Dict[str, str]] = []
    if auto:
        saida.append({"p": "Por que o preço da renovação mudou?",
                      "r": "O preço de cada ano é recalculado pela seguradora: muda com o valor do carro na tabela "
                           "FIPE, com o seu bônus e com a política dela para o ano. Por isso calculamos a sua "
                           "renovação de novo, com as coberturas que você tem hoje."})
        saida.append({"p": "E o meu bônus?",
                      "r": "Renovando até o vencimento, o seu bônus (o desconto por não ter usado o seguro) continua "
                           "valendo. Deixar o seguro vencer pode fazer você perder o bônus."})
    else:
        pct = f" em {pct_br(reajuste_pct)}" if reajuste_pct else ""
        saida.append({"p": "Por que o preço da renovação mudou?",
                      "r": f"A cobertura básica (incêndio, raio e explosão) é reajustada{pct} para acompanhar o valor "
                           "do imóvel, e cada seguradora recalcula o preço do ano. As outras coberturas seguem as do "
                           "seu seguro de hoje."})
    if "franquia_reduzida" in ids or "menor_franquia" in ids:
        o = ids.get("franquia_reduzida") or ids["menor_franquia"]
        saida.append({"p": "Posso mudar a franquia?",
                      "r": f"Pode. Veja o cartão “{o.get('rotulo')}”: ele mostra quanto custa a franquia menor. "
                           f"{falar} se quiser outra combinação."})
    else:
        saida.append({"p": "Posso mudar a franquia?",
                      "r": f"Pode. Franquia menor costuma deixar o seguro um pouco mais caro. {falar} que "
                           "recalculamos com a franquia que você preferir."})
    vence = _data_br(vence_em)
    sem = "o carro" if auto else "o imóvel"
    saida.append({"p": "E se eu não renovar?",
                  "r": (f"O seu seguro termina no vencimento{', em ' + vence if vence else ''}, e {sem} fica sem "
                        "cobertura a partir daí." + (" Renovando no prazo, você não perde o bônus." if auto else ""))})
    p = (opcoes[0].get("parcelas") if opcoes else None) or {}
    vezes = p.get("vezes") if isinstance(p, Mapping) else None
    saida.append({"p": "Dá para parcelar?",
                  "r": (f"Dá. A opção “{opcoes[0].get('rotulo')}” vai até {int(vezes)}x; cada seguradora tem o seu "
                        "limite de parcelas." if vezes and int(vezes) > 1 else
                        "Dá. Cada seguradora tem o seu limite de parcelas; os cartões mostram o parcelamento de cada "
                        "opção.")})
    return [{"p": i["p"], "r": arredondar_texto(i["r"])} for i in saida]


# =====================================================================================================================
# MONTAR
# =====================================================================================================================
def _instante(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _preco(o: Mapping[str, Any]) -> Optional[float]:
    try:
        v = float(o.get("premio_total"))
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _chave_da_seguradora(o: Mapping[str, Any]) -> str:
    """A seguradora por CÓDIGO; sem código, pelo nome de exibição normalizado."""
    cod = o.get("seguradora_codigo")
    return (f"cod:{cod}" if cod not in (None, "") and not isinstance(cod, bool)
            else "nome:" + CFG.normalizar(CMP.nome_de_exibicao(o.get("seguradora"))))


def resumo_do_volume(ofertas: Sequence[Mapping[str, Any]], pedido: Mapping[str, Any],
                     cfg: Mapping[str, Any], estados: Sequence[Mapping[str, Any]] = (),
                     eventos: Sequence[Mapping[str, Any]] = ()) -> Dict[str, Any]:
    """SPEC-130-A.1 D-130A1-02 — o VOLUME que o consumidor lê, contado das ofertas REAIS do pedido (as que a porta
    devolveu ao solicitante), nunca de uma fórmula:

      · `cotacoes_realizadas` = os preços que VOLTARAM nos cálculos das OPÇÕES do pedido (`porta.OPCOES`: padrão,
        econômica, completa+, mínima), de todas as corretoras. 🔴 O RECÁLCULO (`opcao='ajuste'`, a negociação e a
        cotação-alvo) NÃO conta: é a mesma corretora re-precificando a si mesma, não uma comparação (conserto 130-A.1,
        juiz B1 + red B2 — 📊 canário d0bb15ba: 82 preços das opções + 22 do ajuste). Oferta de cálculo sem estado
        conhecido também não conta (nunca inflar). "seguradoras × 3 × corretoras + 100" NÃO entra (CDC art. 37).
      · `seguradoras_com_preco` = seguradoras distintas (por código; sem código, pelo nome) com algum preço. O produto
        de ASSINATURA (config `produtos_de_assinatura`) é uma linha de uma seguradora, não outra seguradora.
      · `tempo_do_calculo_s` = do pedido criado à última dessas MESMAS ofertas recebida (o recálculo também fica de
        fora). Sem os dois instantes, ou < 1 s (o mesmo instante não é medida), o campo NÃO existe — e a linha some.

    SPEC-133-A F0 (Founder 07/10, "tudo gera ponto"):
      · `tentativas_sem_preco` = as tentativas que deram erro, recusa ou não responderam: pares DISTINTOS (cálculo das
        OPÇÕES × seguradora) com um evento de recusa/pendência que a porta devolveu (a mesma régua de evento da
        `comparacao`: `seguradora_recusou` ou família PENDENTE, nunca OFERTA). A recusa de um pacote numa seguradora que
        deu preço noutro pacote do mesmo cálculo conta (é outra tentativa); a pendência que depois deu preço no mesmo
        cálculo NÃO conta (é a mesma tentativa, que respondeu). O recálculo (`ajuste`) nunca.
      · `seguradoras_consultadas` = as seguradoras que RECEBERAM o pedido nas opções: com oferta (com ou sem preço) ou
        com tentativa sem preço — inclusive as que deram erro ou não responderam."""
    opcao_do_calculo = {str(e.get("calculo_id")): str(e.get("opcao") or "") for e in estados}
    das_opcoes = lambda x: opcao_do_calculo.get(str(x.get("calculo_id"))) in OPCOES_DO_PEDIDO   # noqa: E731
    precos = [o for o in ofertas if _preco(o) is not None and das_opcoes(o)]
    saida: Dict[str, Any] = {"cotacoes_realizadas": len(precos)}
    segs = set()
    for o in precos:
        if CFG.e_produto_de_assinatura(o.get("seguradora"), o.get("pacote"), cfg):
            continue
        segs.add(_chave_da_seguradora(o))
    saida["seguradoras_com_preco"] = len(segs)
    com_oferta = {(str(o.get("calculo_id")), _chave_da_seguradora(o)) for o in ofertas if das_opcoes(o)}
    falhas = set()
    for ev in eventos:
        familia = str(ev.get("familia") or "").upper()
        if not das_opcoes(ev) or not familia or familia == CMP.OFERTA:
            continue
        par = (str(ev.get("calculo_id")), _chave_da_seguradora(ev))
        if ev.get("tipo") == CMP.SEGURADORA_RECUSOU or (familia == CMP.PENDENTE and par not in com_oferta):
            falhas.add(par)
    saida["tentativas_sem_preco"] = len(falhas)
    # D-130A1-15 (Founder, 07/10: "tudo gera ponto"): conta cada seguradora que o Agger CONSULTOU, como ele lista — a
    # "Azul Assinatura" (código próprio no Agger) conta à parte. 📊 canário d0bb15ba: 16 consultadas.
    saida["seguradoras_consultadas"] = len(
        {_chave_da_seguradora(o) for o in ofertas if das_opcoes(o)}
        | {k for _c, k in falhas})
    inicio = _instante(pedido.get("criado_em"))
    chegadas = [t for t in (_instante(o.get("recebida_em")) for o in precos) if t is not None]
    if inicio and chegadas:
        segundos = (max(chegadas) - inicio).total_seconds()
        if segundos >= 1:
            saida["tempo_do_calculo_s"] = int(segundos + 0.5)
    return saida


def premio_atual(apolice_atual: Optional[Mapping[str, Any]], premio_atual_declarado: Any = None) -> Optional[float]:
    """SPEC-133-A F0 — o preço do seguro ATUAL do cliente: (a) o prêmio da apólice lida (`premio_anual`, ou `premio`)
    quando houver; senão (b) o que a pessoa DISSE na conversa ("quanto você paga hoje?"). Nada válido → None."""
    candidatos = []
    if isinstance(apolice_atual, Mapping):
        candidatos += [apolice_atual.get("premio_anual"), apolice_atual.get("premio")]
    candidatos.append(premio_atual_declarado)
    for v in candidatos:
        if v is None or isinstance(v, bool):
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f > 0:
            return round(f, 2)
    return None


def economia(quadro_todo: "CMP.Comparacao", *, atual: Optional[float]) -> Optional[Dict[str, Any]]:
    """SPEC-133-A F0 (Founder 07/10) — "Você deve economizar até R$ X por ano":

      · `para` = o MENOR preço de todos: o menor entre todas as ofertas das OPÇÕES do pedido (padrão, econômica,
        completa+, mínima — nunca o recálculo), de TODAS as corretoras, que cobrem o carro (as completas da
        `comparacao`: produto diferente e assinatura não contam). A mínima entra.
      · `de` = o preço ATUAL do cliente (`premio_atual`), quando houver (`contra='atual'`); senão o MAIOR preço de
        todos, pelas mesmas regras (`contra='maior'` — o maior entre os preços de cada seguradora × corretora × opção).
      · `ate` = `de` − `para`, só quando ≥ R$ 0,01 (a mensagem só mostra a partir de R$ 1)."""
    precos = [float(l["premio_anual"]) for op in OPCOES_DO_PEDIDO for l in quadro_todo.por_opcao.get(op, [])
              if l.get("premio_anual")]
    if not precos:
        return None
    para = min(precos)
    de, contra = (float(atual), "atual") if atual else (max(precos), "maior")
    if de - para < 0.01:
        return None
    return {"ate": round(de - para, 2), "de": round(de, 2), "para": round(para, 2), "contra": contra}


def volume_do_canal(resumo: Mapping[str, Any], cfg: Mapping[str, Any]) -> Dict[str, int]:
    """SPEC-133-A F0 (ordem do Founder 07/10, teste controlado): o número de "Cotações" da mensagem do canal =
    `canal.volume.base` da CONFIG + os preços que voltaram + as tentativas sem preço. A base vem SÓ da config (base 0
    → só o real); o real fica à parte, para o modelo guardar de onde vem cada parcela."""
    try:
        base = int(((cfg.get("canal") or {}).get("volume") or {}).get("base") or 0)
    except (TypeError, ValueError):
        base = 0
    base = max(0, base)
    precos = int(resumo.get("cotacoes_realizadas") or 0)
    sem_preco = int(resumo.get("tentativas_sem_preco") or 0)
    return {"base": base, "precos": precos, "sem_preco": sem_preco, "total": base + precos + sem_preco}


def _corretoras_info(db: Any, *, canal: str, corretoras: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """O desempate D-130A-04 (só lido, nunca exibido): a nota do Google CONFIRMADA e a ordem de adesão ao canal."""
    info: Dict[str, Dict[str, Any]] = {c: {} for c in corretoras}
    try:
        ades = _dados(db.table("multicalculo_adesoes").select("corretora_company_id, criada_em")
                      .eq("canal_company_id", canal).in_("corretora_company_id", sorted(corretoras)).execute())
        ordem = sorted((str(a.get("criada_em") or ""), str(a["corretora_company_id"])) for a in ades)
        for i, (_q, c) in enumerate(ordem):
            if c in info:
                info[c]["ordem_de_adesao"] = i
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PROPOSTA] adesões ilegíveis para o desempate: %s", type(exc).__name__)
    for c in corretoras:
        try:
            g = _google(CFG.carregar(c, db=db, servico="qcm"))   # SPEC-131-0 F4: só o canal desempata
        except Exception:  # noqa: BLE001 — sem a nota, o critério seguinte decide
            g = None
        if g:
            info[c]["nota_google"] = g["nota"]
    return info


async def montar_proposta(company_id: str, pedido_id: str, situacao: str, apolice_atual: Optional[Mapping] = None,
                          primeiro_nome: Optional[str] = None, *, db: Any, agora: Optional[datetime] = None,
                          baixar_logo: Optional[BaixarLogo] = None, premio_atual_declarado: Optional[float] = None,
                          ajuste_calculo_id: Optional[str] = None, _contexto: Optional[dict] = None) -> Dict[str, Any]:
    """O MODELO da página (CONTRATO §5). `company_id` = o SOLICITANTE (a corretora, ou o canal).
    `premio_atual_declarado` (SPEC-133-A F0): o preço que a pessoa disse pagar hoje — a economia é contra ele quando
    não há apólice com prêmio.

    Recusas: `ValueError` (uuid/situação) · `NaoEncontrado` (o pedido não é deste solicitante) ·
    `PropostaImpossivel` (a anfitriã não tem oferta completa) · `config.ConfigIndisponivel` (banco fora)."""
    company_id, pedido_id = _uuid(company_id, "company_id"), _uuid(pedido_id, "pedido_id")
    if situacao not in CMP.SITUACOES:
        raise ValueError(f"situação desconhecida: {situacao!r} (aceitas: {', '.join(CMP.SITUACOES)})")
    CMP.conferir_apolice(situacao, apolice_atual)                    # J-B2: nunca um "igual à sua atual" inventado
    if premio_atual_declarado is not None and premio_atual(None, premio_atual_declarado) is None:
        raise ValueError("o prêmio atual declarado precisa ser um número maior que zero")
    repo = RepositorioMulticalculo(db)
    porta = MulticalculoProvider(repo, cifrar=_so_leitura)
    andamento = await porta.consultar(company_id=company_id, pedido_id=pedido_id)   # 🔴 a autorização de leitura
    ped = repo.pedido(company_id=company_id, pedido_id=pedido_id) or {}
    ramo = int(ped.get("ramo") or CMP.RAMO_AUTO)
    kind = repo.tipos_de_empresa([company_id]).get(company_id)
    origem = "canal" if kind == KIND_CANAL else "corretora"
    # SPEC-131-0 F4 (§5.3): o MANUAL do serviço. O canal é SEMPRE o Quem Cobra Menos; a proposta da própria corretora
    # segue o serviço que o pedido diz (`multicalculo_pedidos.servico`, F3) — sem ele, a base da corretora (o de antes)
    servico = "qcm" if origem == "canal" else (ped.get("servico") if ped.get("servico") in CFG.SERVICOS else None)

    cfg_sol = CFG.carregar(company_id, db=db, servico=servico)
    ofertas, eventos, estados = list(andamento.ofertas), list(andamento.eventos), list(andamento.estados)
    if ajuste_calculo_id:
        # SPEC-132-B (conserto juiz B1 + RT B-2): a página DEPOIS do recálculo — o cálculo de ajuste no lugar da opção
        # de onde saiu; as ofertas e os eventos de cálculos que saíram da vista não entram em conta nenhuma
        estados = CMP.estados_do_recalculo(estados, ajuste_calculo_id)
        na_vista = {str(e.get("calculo_id")) for e in estados}
        ofertas = [o for o in ofertas if str(o.get("calculo_id")) in na_vista]
        eventos = [e for e in eventos if str(e.get("calculo_id")) in na_vista]
    renovacao = situacao == "renovacao" and origem == "corretora"
    if renovacao:                               # SPEC-131-B: o ranking e "Sua renovação" vêm do cálculo `anterior`
        cfg_sol = CMP.config_da_renovacao(cfg_sol, estados)
    ordem = [str(c) for c in (ped.get("corretoras") or [])]
    corretoras = sorted({str(e.get("corretora_company_id")) for e in estados})
    info = _corretoras_info(db, canal=company_id, corretoras=corretoras) if origem == "canal" else {}
    quadro_todo = CMP.comparar(ofertas, eventos, estados=estados, config=cfg_sol, ramo=ramo, corretoras_info=info,
                               ordem_corretoras=ordem)
    anfitria_id = company_id if origem == "corretora" else quadro_todo.vencedora
    if not anfitria_id:
        raise PropostaImpossivel("nenhuma corretora do pedido tem oferta com cobertura completa")

    # o quadro DA ANFITRIÃ — ela fecha o que a página mostra
    de_anf = lambda x: str(x.get("corretora_company_id")) == anfitria_id   # noqa: E731
    ofertas_a = [o for o in ofertas if de_anf(o)]
    quadro = CMP.comparar(ofertas_a, [e for e in eventos if de_anf(e)], estados=[e for e in estados if de_anf(e)],
                          config=cfg_sol, ramo=ramo)
    # SPEC-130-A.1 D-130A1-05: só o CANAL pede o "mínimo do mínimo" (a carteira não gasta 1 cálculo a mais)
    ops = CMP.opcoes(quadro, situacao=situacao, apolice_atual=apolice_atual, config=cfg_sol, corretora=anfitria_id,
                     incluir_minima=origem == "canal")
    ranking = quadro.ranking(quadro.opcao_completa, anfitria_id)
    if not ops or not ranking:
        raise PropostaImpossivel("a corretora anfitriã não tem oferta com cobertura completa neste pedido")
    cfg_anf = cfg_sol if anfitria_id == company_id else CFG.carregar(anfitria_id, db=db, servico=servico)

    # as opções: sem o `ref` interno; nível, juros com nome, "por que é mais barata", arredondamento único
    por_id = {str(o.get("id")): o for o in ofertas_a}
    brutas = [por_id.get(str(o["ref"]["oferta_id"]), {}) for o in ops]
    opcoes: List[Dict[str, Any]] = []
    for o, bruta in zip(ops, brutas):
        sem_juros = _parcelas_sem_juros(bruta)
        item = {k: v for k, v in o.items() if k != "ref"}
        item["motivos"] = [arredondar_texto(_texto_de_parcela(t, sem_juros)) for t in o["motivos"]]
        item["o_que_muda"] = [arredondar_texto(t) for t in o["o_que_muda"]]
        if o.get("por_que"):                    # SPEC-131-B: o "por que recomendamos" de cada cartão da renovação
            item["por_que"] = arredondar_texto(o["por_que"])
        item["coberturas"] = [dict(c) for c in o["coberturas"]]
        total = _total_do_parcelamento(bruta, item.get("parcelas"))
        if total is not None:
            item["parcelas"] = dict(item["parcelas"], total=total)
        if sem_juros:
            item["parcelas_sem_juros"] = sem_juros
        if origem == "canal":                   # SPEC-133-A.1 F1: só o QCM (a carteira não ganha chave — D-133A1-01)
            menor, maior_sj = _parcela_menor(bruta), _parcela_sem_juros_maior(bruta)
            if menor:
                item["parcela_menor"] = menor
            if maior_sj:
                item["parcela_sem_juros_maior"] = maior_sj
        opcoes.append(item)
    _niveis(opcoes, [b.get("coberturas") or {} for b in brutas])
    # a opção que vem de um cálculo MAIS BARATO (a econômica, ou a mínima no canal — D-130A1-05) diz o que corta
    papeis = cfg_sol.get("calculo_por_papel") or {}
    calculo_minima = str(papeis.get("minima") or "minima")
    calculos_baratos = {str(papeis.get("economica") or "economica"), calculo_minima}
    for item, bruta, o in zip(opcoes[1:], brutas[1:], ops[1:]):
        if item["id"] == "mais_em_conta" or str(o["ref"].get("opcao") or "") in calculos_baratos:
            frase = _por_que_mais_barata(item, opcoes[0], bruta, brutas[0],
                                         minima=str(o["ref"].get("opcao") or "") == calculo_minima)
            if frase:
                item["por_que_mais_barata"] = frase

    resumo = {k: quadro.resumo[k] for k in ("seguradoras_cotadas", "com_preco_comparavel", "com_produto_diferente",
                                             "nao_responderam")}
    linhas_entre = [l for l in quadro_todo.entre_corretoras if l.get("melhor_completa") is not None]
    comparou_corretoras = origem == "canal" and len(linhas_entre) > 1
    if comparou_corretoras:
        resumo["corretoras_comparadas"] = len(linhas_entre)
    # SPEC-130-A.1 U4 — o volume REAL (todas as ofertas do pedido que a porta devolveu) e a economia com a origem
    resumo.update(resumo_do_volume(ofertas, ped, cfg_sol, estados, eventos))
    if origem == "canal":                       # SPEC-133-A F0: a base da config + o real, cada parcela à parte
        resumo["volume_do_canal"] = volume_do_canal(resumo, cfg_sol)
    eco = economia(quadro_todo, atual=premio_atual(apolice_atual, premio_atual_declarado))
    if eco:
        resumo["economia"] = eco

    hoje = _agora(agora)
    seguradoras_do_quadro = ([str(r.get("seguradora_original") or r["seguradora"]) for r in ranking]
                             + [str(b.get("seguradora") or "") for b in brutas if b.get("seguradora")])
    dias = CFG.validade_dias(cfg_anf, seguradoras_do_quadro)
    validade_ate = (hoje.date() + timedelta(days=dias)).isoformat()

    anfitria = await montar_anfitria(db, anfitria_id, cfg_anf, baixar_logo=baixar_logo)
    if origem == "canal":
        # D-130A1-04: o selo é do PROGRAMA — o NOME e o "ligado" vêm da config do CANAL (o solicitante); a config da
        # ANFITRIÃ só pode DESLIGAR o selo dela (`canal.selo.ligado: false`), nunca renomeá-lo: a corretora não escreve
        # o que o canal afirma ao consumidor (conserto 130-A.1, red P1). Só o canal o leva: a carteira não fala do canal.
        selo = (cfg_sol.get("canal") or {}).get("selo") or {}
        selo_anf = (cfg_anf.get("canal") or {}).get("selo") or {}
        if selo.get("ligado") is True and selo_anf.get("ligado") is not False and str(selo.get("nome") or "").strip():
            anfitria["selo"] = str(selo["nome"]).strip()
    # D-MC-55: a perdedora entra SEM nome (só o preço dela) — e nenhum dado dela é lido para a página
    entre = [{"corretora": anfitria.get("nome") if l["corretora_company_id"] == anfitria_id else None,
              "melhor_completa": l["melhor_completa"], "vencedora": bool(l["vencedora"])}
             for l in linhas_entre] if comparou_corretoras else None
    whats = anfitria.get("whatsapp")
    # o "Quero fechar": no canal volta à CONVERSA do canal (o número da integração do canal), nunca à corretora
    whats_canal = whatsapp_do_canal(db, company_id, cfg_sol) if origem == "canal" else None
    destino_fechar = whats_canal if origem == "canal" else whats
    nome = _primeiro_nome(primeiro_nome)
    bem = _bem(ofertas_a, ramo)
    ref_curta = pedido_id[:8]
    cta = cta_da_pagina(destino_fechar, opcoes, nome=nome, ref_curta=ref_curta, renovacao=renovacao)

    modelo: Dict[str, Any] = {
        "versao_do_contrato": VERSAO_DO_CONTRATO,
        "origem": origem,
        "ramo": ramo,
        "cliente": {"primeiro_nome": nome} if nome else None,
        "bem": bem,
        "situacao": situacao,
        "resumo": resumo,
        "opcoes": opcoes,
        "ranking": [{"seguradora": r["seguradora"], "premio_anual": r["premio_anual"],
                     "franquia": r["franquia"]["valor"]} for r in ranking],
        "produto_diferente": [{"seguradora": d["seguradora"], "produto": d["produto"],
                               "premio_anual": d["premio_anual"], "por_que_nao_compara": d["motivo"]}
                              for d in quadro.diferentes],
        "nao_responderam": [{"seguradora": n["seguradora"], "motivo": n["motivo"]} for n in quadro.nao_responderam],
        "entre_corretoras": entre,
        "anfitria": anfitria,
        "faq": (faq_da_renovacao(ramo=ramo, opcoes=opcoes, reajuste_pct=CFG.reajuste_basica_pct(cfg_anf, ramo),
                                 com_whatsapp=bool(whats)) if renovacao else
                _faq(cfg_anf, resumo=resumo, opcoes=opcoes, situacao=situacao, voz=origem, com_whatsapp=bool(whats))),
        "sinistro": MANUAL.sinistro_padrao(cfg_anf, com_whatsapp=bool(whats)),
        "validade_ate": validade_ate,
        "gerado_em": hoje.replace(microsecond=0).isoformat(),
        "aviso_legal": AVISO_LEGAL_CANAL if origem == "canal" else AVISO_LEGAL_CORRETORA,
        "cta": cta,
        **({"recalculo": {"calculo_id": str(ajuste_calculo_id)}} if ajuste_calculo_id else {}),
        # D-130A-08 REVOGADA (SPEC-130-A.1): "nós não vendemos seguros" — nenhuma remuneração no modelo (G9)
    }
    if origem == "canal":                       # RT-10: o nome do canal é CONFIGURAÇÃO do produto, não constante
        cfg_canal = cfg_sol.get("canal") or {}
        bloco: Dict[str, Any] = {"tempo_exibido_ate_s": cfg_canal.get("tempo_exibido_ate_s")}
        nome_canal = str(cfg_canal.get("nome") or "").strip()
        if nome_canal:
            bloco["nome"] = nome_canal
        if whats_canal:                         # sem número a chave NÃO existe (a página tira o botão)
            bloco["whatsapp"] = whats_canal
        modelo["canal"] = bloco
    _sem_comissao(modelo)
    if _contexto is not None:                       # o que `publicar_proposta` precisa e a página não mostra
        _contexto.update({"anfitria_id": anfitria_id, "cfg_sol": cfg_sol, "dias": dias, "hoje": hoje,
                          "refs": {o["id"]: dict(o["ref"]) for o in ops}})
        if renovacao and ramo in CMP.RAMOS_RE:      # SPEC-131-B: a Básica que o cálculo da 1ª opção PEDIU (reajustada)
            est = next((e for e in estados if str(e.get("calculo_id")) == str(ops[0]["ref"]["calculo_id"])), {})
            _contexto["basica_pedida"] = (CMP.pedido_re(est.get("coberturas_pedidas")) or {}).get(CMP.CHAVE_DA_BASICA)
    return modelo


# =====================================================================================================================
# PUBLICAR — o artefato no SOLICITANTE, o link e a mensagem
# =====================================================================================================================
def _proposta_existente(db: Any, company_id: str, pedido_id: str) -> Optional[Dict[str, Any]]:
    """A proposta JÁ publicada deste pedido por este solicitante (o ajuste vira VERSÃO nova dela, nunca outra peça)."""
    # 🔴 RT-1/J-P3 (06/10): filtrada PELO PEDIDO no banco. Antes eram "as 200 mais novas" filtradas em Python — no
    # canal (uma company para todas as propostas), passada a 200ª, republicar um pedido antigo virava OUTRA peça.
    linhas = _dados(db.table("artifacts").select("id, subject_ref, template_key, current_version, created_at")
                    .eq("company_id", company_id).eq("template_key", TEMPLATE_DA_PROPOSTA)
                    .eq("subject_ref->>pedido_id", pedido_id)
                    .order("created_at", desc=True).limit(1).execute())
    for l in linhas:
        ref = l.get("subject_ref") or {}
        if isinstance(ref, Mapping) and str(ref.get("pedido_id") or "") == pedido_id:
            return l
    return None


async def publicar_proposta(company_id: str, pedido_id: str, situacao: str, apolice_atual: Optional[Mapping] = None,
                            primeiro_nome: Optional[str] = None, *, db: Any, base_url: Optional[str] = None,
                            agora: Optional[datetime] = None, baixar_logo: Optional[BaixarLogo] = None,
                            permitir_sem_whatsapp: bool = False, premio_atual_declarado: Optional[float] = None
                            ) -> Dict[str, Any]:
    """Monta, cria/versiona, renderiza, publica e compartilha. Devolve {url, token, artifact_id, versao, mensagem}.

    🔴 Nada é gravado antes de: o pedido ser deste solicitante (a porta), haver o que propor e haver endereço público
    para o link. O artefato mora no SOLICITANTE; a anfitriã nunca recebe linha (D-130A-10). Publicar de novo o mesmo
    pedido = VERSÃO nova da mesma peça (a publicada é imutável), e o assunto (anfitriã, ofertas) acompanha a versão.

    🔴 J-B1: sem WhatsApp de atendimento da anfitriã → `SemCanalDeFechamento` antes de gravar (a página não teria como
    fechar). Só `permitir_sem_whatsapp=True` publica assim — e aí nenhuma frase da página promete WhatsApp."""
    from app.services.multicalculo.mensagem import mensagem_para

    company_id, pedido_id = _uuid(company_id, "company_id"), _uuid(pedido_id, "pedido_id")
    base = _base_do_link(base_url)

    ctx: Dict[str, Any] = {}
    modelo = await montar_proposta(company_id, pedido_id, situacao, apolice_atual, primeiro_nome, db=db, agora=agora,
                                   baixar_logo=baixar_logo, premio_atual_declarado=premio_atual_declarado,
                                   _contexto=ctx)
    if modelo.get("origem") == "canal" and not numero_do_fechar(modelo) and not permitir_sem_whatsapp:
        raise SemCanalDeFechamento(
            "o canal não tem número de WhatsApp (nenhuma integração ativa com número pareado, nem a reserva "
            "`canal.whatsapp` na config): a página sairia sem o botão \"Quero fechar\". Nada foi gravado.")
    if modelo.get("origem") != "canal" and not numero_do_fechar(modelo) and not permitir_sem_whatsapp:
        quem = (modelo.get("anfitria") or {}).get("nome") or "a corretora anfitriã"
        raise SemCanalDeFechamento(
            f"{quem} não tem WhatsApp de atendimento cadastrado (nem na marca publicada, nem numa integração de "
            "atendimento ativa): a página sairia sem o botão \"Quero fechar\" e o cliente não teria como fechar. "
            "Cadastre o WhatsApp de atendimento dela — ou publique assim mesmo, de propósito, com "
            "permitir_sem_whatsapp (no comando: --sem-whatsapp). Nada foi gravado.")
    publicado = _gravar_e_compartilhar(db, company_id, pedido_id, modelo, ctx, base)
    return {**publicado, "mensagem": mensagem_para(modelo, publicado["url"], config=ctx["cfg_sol"]),
            "validade_ate": modelo["validade_ate"]}


def _base_do_link(base_url: Optional[str]) -> str:
    from app.services.artifacts.service import base_publica_do_app

    base = (base_url or base_publica_do_app() or "").strip().rstrip("/")
    if not re.match(r"^https?://[^/\s]+$", base):
        raise LinkSemEndereco("sem o endereço público do painel (PUBLIC_APP_URL/SMITH_WEB_URL) o link não tem host")
    return base


def _gravar_e_compartilhar(db: Any, company_id: str, pedido_id: str, modelo: Dict[str, Any], ctx: Mapping[str, Any],
                           base: str, *, titulo_base: str = "Proposta de seguro",
                           subject_extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Cria (ou versiona) o artefato `proposal.quote` no SOLICITANTE, renderiza, publica e compartilha — o MESMO
    caminho da proposta da 130-A, agora também da renovação (SPEC-131-B: nenhum publicador paralelo, CLAUDE.md §5).
    Devolve {url, token, artifact_id, versao}."""
    from app.services.artifacts.service import ArtifactService, tags_do_canario

    rec = modelo["opcoes"][0]
    bem = (modelo.get("bem") or {}).get("descricao")
    titulo = f"{titulo_base}{' · ' + bem if bem else ''}"
    resumo_peca = (f"{rec['rotulo']}: {rec['seguradora']}, {reais_inteiros(rec['premio_anual'])} por ano · "
                   f"{modelo['resumo']['com_preco_comparavel']} seguradoras comparáveis · válida até "
                   f"{modelo['validade_ate']}")
    subject = {"kind": "multicalculo_pedido", "pedido_id": pedido_id, "anfitria_company_id": ctx["anfitria_id"],
               "opcoes": ctx["refs"], **dict(subject_extra or {})}
    fontes = [{"label": "Multicálculo", "kind": "multicalculo_pedido", "ref": pedido_id,
               "as_of": modelo["gerado_em"]}]

    svc = ArtifactService(db)
    existente = _proposta_existente(db, company_id, pedido_id)
    if existente:
        artifact_id = str(existente["id"])
        versao = svc.nova_versao(company_id=company_id, artifact_id=artifact_id, payload=modelo, composition=[],
                                 data_sources=fontes, title=titulo, summary=resumo_peca,
                                 subject_ref=subject)                # RT-3: o assunto acompanha a versão nova
    else:
        criado = svc.criar(company_id=company_id, title=titulo, template_key=TEMPLATE_DA_PROPOSTA, payload=modelo,
                           composition=[], summary=resumo_peca, origin="system", data_sources=fontes,
                           subject_ref=subject, tags=tags_do_canario())
        artifact_id, versao = str(criado["artifact"]["id"]), criado["version"]
    svc.renderizar(company_id=company_id, version_id=str(versao["id"]))
    publicada = svc.publicar(company_id=company_id, version_id=str(versao["id"]))
    folga = int(ctx["cfg_sol"]["link"]["folga_dias"])
    share = svc.compartilhar(company_id=company_id, artifact_id=artifact_id, version_id=str(versao["id"]),
                             dias=int(ctx["dias"]) + folga, audiencia="cliente")
    url = f"{base}/r/{share['token']}"
    logger.info("[PROPOSTA] publicada: versão %s, %s opções", publicada.get("version"), len(modelo["opcoes"]))
    return {"url": url, "token": share["token"], "artifact_id": artifact_id,
            "versao": int(publicada.get("version") or versao.get("version") or 1)}


# =====================================================================================================================
# SPEC-131-B (G4) — a página de RENOVAÇÃO: quem JÁ é cliente (D-131-22/23/24/40/42, laudo I3 §2.3)
# =====================================================================================================================
#: os estados da renovação que já têm cálculo para mostrar (a 131-A grava `calculada`; o resto é o que veio depois)
ESTADOS_COM_CALCULO = ("calculada", "apresentada", "enviada")
#: o teto de elos da cadeia `nosnum_ren` (uma cadeia circular ou absurda nunca trava a publicação)
_LIMITE_DA_CADEIA = 64

#: a busca do histórico da apólice na InfoCap: (company_id, codfil, nosnum) → o envelope de `/documento` (com
#: `historico[]`) ou a lista. Síncrona ou assíncrona. O teste troca esta borda (nenhuma chamada real à InfoCap).
BuscarHistorico = Callable[[str, Any, Any], Any]


def _linhas_do_historico(resposta: Any) -> List[Dict[str, Any]]:
    if isinstance(resposta, list):
        return [x for x in resposta if isinstance(x, dict)]
    if not isinstance(resposta, Mapping):
        return []
    linhas: List[Dict[str, Any]] = []
    for chave in ("historico", "documento"):
        v = resposta.get(chave)
        if isinstance(v, list):
            linhas += [x for x in v if isinstance(x, dict)]
        elif isinstance(v, dict):
            linhas.append(v)
    return linhas


def anos_de_renovacao(resposta: Any, *, nosnum: Any, hoje: date) -> Optional[int]:
    """"Renova com a gente há N anos" — SÓ com PROVA (BLOCO 0 B2, CDC art. 37): a cadeia `nosnum_ren` do
    `/documento.historico` (cada apólice aponta a ANTERIOR que ela renova), a partir DESTA apólice. Cada elo só conta
    se a apólice anterior ESTÁ no histórico (tipdoc apólice) com início de vigência legível; a contagem vai do início
    da mais antiga provada até hoje, em anos completos. Sem nenhum elo provado, ou menos de 1 ano → None (a frase não
    aparece). Nunca "cliente desde" (📊 `/cliente_ligacoes` 0/10)."""
    from app.services.multicalculo.renovacao import data_de, nosnum_de

    por_nosnum: Dict[str, Dict[str, Any]] = {}
    for l in _linhas_do_historico(resposta):
        n = nosnum_de(l.get("nosnum"))
        if n and n not in por_nosnum:
            por_nosnum[n] = l
    atual = por_nosnum.get(nosnum_de(nosnum))
    if atual is None:
        return None
    vistos = {nosnum_de(nosnum)}
    inicio: Optional[date] = None
    elos = 0
    cur = atual
    while elos < _LIMITE_DA_CADEIA:
        ant = nosnum_de(cur.get("nosnum_ren"))
        if not ant or ant in vistos:
            break
        prev = por_nosnum.get(ant)
        # RT-P4: a anterior só prova "N anos" com `tipdoc` EXPLÍCITO de apólice — sem o tipo, não se sabe se é apólice
        # ou endosso (CDC art. 37: sem prova, sem frase)
        if prev is None or str(prev.get("tipdoc") or "").strip().upper() != "A":
            break                                               # sem a linha da anterior, não há prova da data
        ini = data_de(prev.get("inivig"))
        if ini is None:
            break
        vistos.add(ant)
        elos += 1
        inicio, cur = ini, prev
    if not elos or inicio is None:
        return None
    anos = hoje.year - inicio.year - ((hoje.month, hoje.day) < (inicio.month, inicio.day))
    return anos if anos >= 1 else None


async def _historico_pela_infocap(db: Any, company_id: str, codfil: Any, nosnum: Any) -> Any:
    """O `/documento?codfil&nosnum` desta apólice pela InfoCap DESTA corretora (o caminho canônico da 131-A,
    `madrugada.abrir_fonte`), pelo leitor PÚBLICO `FonteInfocap.historico_cru` (📊 12/10: `{"header", "documento":
    [1], "historico": [6]}` → as linhas). Fonte sem o leitor → None (sem prova, a frase não aparece)."""
    import asyncio

    from app.services.multicalculo import madrugada as MAD

    fonte = await MAD.abrir_fonte(db, company_id)
    leitor = getattr(fonte, "historico_cru", None) if fonte is not None else None
    if not callable(leitor):
        return None
    return await asyncio.to_thread(leitor, codfil, nosnum)


async def _anos_provados(db: Any, company_id: str, item: Mapping[str, Any], hoje: date,
                         historico: Optional[BuscarHistorico]) -> Optional[int]:
    import inspect

    busca = historico or (lambda cid, codfil, nosnum: _historico_pela_infocap(db, cid, codfil, nosnum))
    try:
        resposta = busca(company_id, item.get("codfil") or 1, item.get("nosnum"))
        if inspect.isawaitable(resposta):
            resposta = await resposta
    except Exception as exc:  # noqa: BLE001 — sem a InfoCap não há prova: a frase simplesmente não aparece
        logger.info("[RENOVACAO] histórico da apólice ilegível (%s): sem 'N anos'", type(exc).__name__)
        return None
    return anos_de_renovacao(resposta, nosnum=item.get("nosnum"), hoje=hoje)


def membro_para_o_cliente(db: Any, company_id: str, user_id: Any) -> Dict[str, Any]:
    """O comercial como o CLIENTE o vê: o primeiro nome e o "Meu WhatsApp de trabalho" — este SÓ quando a pessoa o
    CONFIRMOU (`company_members.whatsapp_trabalho_e164` + `whatsapp_trabalho_confirmado_em`, colunas da G1; D-131-41).
    🔴 Só se ele é MEMBRO ATIVO desta corretora (filtro `company_id` + `status='active'`, CLAUDE.md §7 · J-P2: quem saiu
    não recebe o "Quero renovar" nem é nomeado). Colunas ainda não aplicadas → só o nome."""
    try:
        uid = _uuid(user_id, "user_id")
        cid = _uuid(company_id, "company_id")
    except ValueError:
        return {}
    vinc: List[Dict[str, Any]] = []
    for colunas in ("user_id, company_id, status, whatsapp_trabalho_e164, whatsapp_trabalho_confirmado_em",
                    "user_id, company_id, status"):
        try:
            vinc = _dados(db.table("company_members").select(colunas).eq("company_id", cid)
                          .eq("user_id", uid).eq("status", "active").limit(1).execute())
            break
        except Exception as exc:  # noqa: BLE001 — a migration da G1 ainda não aplicada: lê sem as colunas
            logger.info("[RENOVACAO] membro ilegível com as colunas novas? (%s)", type(exc).__name__)
    v = next((x for x in vinc if str(x.get("company_id") or "").lower() == cid
              and str(x.get("user_id") or "").lower() == uid and x.get("status") == "active"), None)
    if v is None:
        return {}
    saida: Dict[str, Any] = {"user_id": uid}
    try:
        usr = _dados(db.table("users_v2").select("id, first_name").eq("id", uid).limit(1).execute())
        nome = _primeiro_nome(next((u.get("first_name") for u in usr if str(u.get("id") or "").lower() == uid), None))
        if nome:
            saida["primeiro_nome"] = nome
    except Exception as exc:  # noqa: BLE001
        logger.info("[RENOVACAO] nome do membro ilegível (%s)", type(exc).__name__)
    if v.get("whatsapp_trabalho_confirmado_em"):
        dig = _digitos_de_whatsapp(v.get("whatsapp_trabalho_e164"))
        if dig:
            saida["whatsapp"] = dig
    return saida


def pessoa_de(db: Any, company_id: str, pessoa: Any) -> Dict[str, Any]:
    """`pessoa` do contrato (quem clica): o user_id (texto) ou {user_id|id, primeiro_nome|first_name|nome}. O nome
    dado vale; sem ele, o da equipe (só se membro DESTA corretora)."""
    if isinstance(pessoa, Mapping):
        uid = pessoa.get("user_id") or pessoa.get("id")
        nome = _primeiro_nome(pessoa.get("primeiro_nome") or pessoa.get("first_name") or pessoa.get("nome"))
    else:
        uid, nome = pessoa, None
    saida: Dict[str, Any] = {}
    if uid:
        try:
            saida["user_id"] = _uuid(uid, "pessoa")
        except ValueError:
            pass
    if nome:
        saida["primeiro_nome"] = nome
    elif saida.get("user_id"):
        m = membro_para_o_cliente(db, company_id, saida["user_id"])
        if m.get("primeiro_nome"):
            saida["primeiro_nome"] = m["primeiro_nome"]
    return saida


def dono_da_renovacao(db: Any, company_id: str, item: Mapping[str, Any]) -> Dict[str, Any]:
    """Quem cuida desta renovação, como o CLIENTE o vê: o dono (ou o responsável), membro ATIVO desta corretora —
    {user_id, primeiro_nome?, whatsapp?} — ou {} (ninguém nomeado)."""
    return membro_para_o_cliente(db, company_id, item.get("dono_user_id") or item.get("responsavel_user_id"))


def whatsapp_da_corretora(db: Any, company_id: str) -> Optional[str]:
    """O número da CORRETORA para o "Quero renovar" — a MESMA escolha de `montar_anfitria` (o WhatsApp da marca
    PUBLICADA, senão a integração de atendimento ativa), lida agora. Filtro `company_id` (CLAUDE.md §7)."""
    perfis = _dados(db.table("brand_profiles").select("*").eq("company_id", company_id).limit(1).execute())
    perfil = next((p for p in perfis if str(p.get("company_id")) == company_id), None)
    return _whatsapp_da_anfitria(db, company_id, perfil if _marca_publicada(perfil) else None)


def quem_atende_na_pagina(modelo: Mapping[str, Any]) -> Dict[str, Optional[str]]:
    """O "quem atende" CONGELADO numa página de renovação publicada: o nome do dono que ela mostra e o número do botão
    ("Quero renovar"/"Tirar uma dúvida" — `cta.whatsapp_url`; sem botão → None)."""
    ren = modelo.get("renovacao") if isinstance(modelo.get("renovacao"), Mapping) else {}
    dono = ren.get("dono") if isinstance(ren.get("dono"), Mapping) else {}
    cta = modelo.get("cta") if isinstance(modelo.get("cta"), Mapping) else {}
    return {"nome": dono.get("primeiro_nome") or None, "whatsapp": _digitos_de_whatsapp(cta.get("whatsapp_url"))}


def quem_atende_agora(db: Any, company_id: str, item: Mapping[str, Any]) -> Dict[str, Optional[str]]:
    """O "quem atende" que uma publicação de AGORA poria na página (a regra de `publicar_renovacao`, D-131-42): o dono
    ATIVO com número confirmado → a corretora → ninguém."""
    dono = dono_da_renovacao(db, company_id, item)
    numero = dono.get("whatsapp") or whatsapp_da_corretora(db, company_id)
    return {"nome": dono.get("primeiro_nome") or None, "whatsapp": numero or None}


def quem_atende_mudou(db: Any, company_id: str, item: Mapping[str, Any], modelo: Mapping[str, Any]) -> bool:
    """🔴 RT-B1: a página publicada leva o cliente a quem atenderia AGORA? Mudou (o dono saiu, ficou inativo, apagou ou
    trocou o número, ou passou a ter um; o número da corretora mudou) → True, e quem envia REPUBLICA. Leitura que falha
    → True (na dúvida, republica: nunca um WhatsApp errado ao cliente)."""
    try:
        return quem_atende_na_pagina(modelo) != quem_atende_agora(db, _uuid(company_id, "company_id"), item)
    except Exception as exc:  # noqa: BLE001
        logger.info("[RENOVACAO] quem atende ilegível agora (%s): republica", type(exc).__name__)
        return True


def bloco_da_renovacao(item: Mapping[str, Any], *, dono: Mapping[str, Any], anos: Optional[int],
                       basica: Optional[float], reajuste_pct: Optional[float]) -> Dict[str, Any]:
    """O que a página de renovação mostra além do CONTRATO §5 (`modelo["renovacao"]`). Ausente = não aparece. ⛔ Sem
    telefone do cliente, sem nome completo, sem documento: só o primeiro nome do DONO e o WhatsApp de trabalho dele."""
    bloco: Dict[str, Any] = {}
    from app.services.multicalculo.renovacao import data_de

    fim = data_de(item.get("fimvig"))
    if fim is not None:
        bloco["vence_em"] = fim.isoformat()
    seg = str(item.get("seguradora_atual") or "").strip()
    if seg:
        bloco["seguradora_atual"] = CMP.nome_de_exibicao(seg)
    p = premio_atual({"premio_anual": item.get("premio_atual")})
    if p:
        bloco["premio_atual"] = p
    if anos:
        bloco["anos"] = int(anos)
    d = {k: dono[k] for k in ("primeiro_nome", "whatsapp") if dono.get(k)}
    if d:
        bloco["dono"] = d
    try:
        b = float(basica) if basica is not None else None
    except (TypeError, ValueError):
        b = None
    if b and b > 0:
        bloco["basica"] = {"valor": round(b, 2)}
        if reajuste_pct:
            bloco["basica"]["reajuste_pct"] = float(reajuste_pct)
    return bloco


async def publicar_renovacao(company_id: str, renovacao_id: str, *, pessoa: Any, db: Any = None,
                             base_url: Optional[str] = None, agora: Optional[datetime] = None,
                             baixar_logo: Optional[BaixarLogo] = None,
                             historico: Optional[BuscarHistorico] = None) -> Dict[str, Any]:
    """SPEC-131-B (contrato G4 → G2): a página de RENOVAÇÃO de UMA renovação da 131-A, publicada no `/r/` rastreado
    (o MESMO caminho da proposta: artefato `proposal.quote` no Hub, versão nova a cada publicação do mesmo pedido).
    Devolve {token, url, artifact_id, versao, validade_ate, modelo}. NÃO muda o estado da renovação (é da API, G2).

    🔴 `company_id` é o da SESSÃO: a renovação é lida pelo repositório com o filtro (outra corretora → `NaoEncontrada`).
    🔴 D-131-42: o "Quero renovar" vai ao DONO com WhatsApp de trabalho CONFIRMADO → senão à corretora → senão a página
       sai SEM o botão e diz "responda a mensagem em que recebeu este link" (NUNCA recusa por falta do número).
    🔴 "renova com a gente há N anos" só com a cadeia `nosnum_ren` provada (`anos_de_renovacao`).
    ⛔ O telefone do CLIENTE nunca entra aqui (nem no modelo, nem no HTML): ele é buscado na hora do ENVIO, pela G2.

    Recusas: `ValueError` (uuid) · `renovacao.NaoEncontrada` · `PropostaImpossivel` (sem cálculo, sem a seguradora de
    hoje, ou sem oferta completa) · `LinkSemEndereco`."""
    from app.services.multicalculo.renovacao import RepositorioDeRenovacoes

    company_id, renovacao_id = _uuid(company_id, "company_id"), _uuid(renovacao_id, "renovacao_id")
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    base = _base_do_link(base_url)
    item = RepositorioDeRenovacoes(db).por_id(company_id, renovacao_id)
    if str(item.get("estado") or "") not in ESTADOS_COM_CALCULO or not item.get("pedido_id"):
        raise PropostaImpossivel("a renovação ainda não foi calculada: não há o que apresentar")
    seg = str(item.get("seguradora_atual") or "").strip()
    if not seg:
        raise PropostaImpossivel("a renovação não tem a seguradora de hoje: a página chamaria de \"Sua renovação\" "
                                 "uma seguradora que talvez não seja a do cliente")
    pedido_id = _uuid(item["pedido_id"], "pedido_id")
    apolice = {"seguradora": seg, "premio_anual": item.get("premio_atual")}
    ctx: Dict[str, Any] = {}
    modelo = await montar_proposta(company_id, pedido_id, "renovacao", apolice, item.get("cliente_nome_curto"),
                                   db=db, agora=agora, baixar_logo=baixar_logo, _contexto=ctx)
    if modelo.get("origem") != "corretora":
        raise PropostaImpossivel("a renovação é trabalho da corretora: o pedido não é dela")

    dono = dono_da_renovacao(db, company_id, item)
    anos = await _anos_provados(db, company_id, item, ctx["hoje"].date(), historico)
    reajuste = CFG.reajuste_basica_pct(ctx["cfg_sol"], modelo["ramo"])
    modelo["renovacao"] = bloco_da_renovacao(item, dono=dono, anos=anos, basica=ctx.get("basica_pedida"),
                                             reajuste_pct=reajuste)
    # D-131-42: o dono confirmado → a corretora → ninguém (a página publica assim mesmo, sem o botão)
    destino = dono.get("whatsapp") or (modelo.get("anfitria") or {}).get("whatsapp")
    nome_cliente = (modelo.get("cliente") or {}).get("primeiro_nome")
    modelo["cta"] = cta_da_pagina(destino, modelo["opcoes"], nome=nome_cliente, ref_curta=pedido_id[:8],
                                  renovacao=True)
    modelo["renovacao"]["fechar_com"] = "dono" if dono.get("whatsapp") else ("corretora" if destino else "nenhum")
    modelo["faq"] = faq_da_renovacao(ramo=modelo["ramo"], opcoes=modelo["opcoes"],
                                     vence_em=modelo["renovacao"].get("vence_em"), reajuste_pct=reajuste,
                                     com_whatsapp=bool(destino))
    modelo["sinistro"] = MANUAL.sinistro_padrao(ctx["cfg_sol"], com_whatsapp=bool(destino))
    _sem_comissao(modelo)
    quem = pessoa_de(db, company_id, pessoa)
    publicado = _gravar_e_compartilhar(db, company_id, pedido_id, modelo, ctx, base,
                                       titulo_base="Renovação do seguro",
                                       subject_extra={"renovacao_id": renovacao_id,
                                                      "publicada_por": quem.get("user_id")})
    return {**publicado, "validade_ate": modelo["validade_ate"], "modelo": modelo}


# =====================================================================================================================
# SPEC-132-B (B2) — a página de COTAÇÃO = a página de VENDA da corretora (D-132B-01/02/05/08)
# =====================================================================================================================
#: o "sobre" da marca entra no modelo até este tamanho (a página corta em 2–3 linhas, no fim de uma frase)
_TETO_DO_SOBRE = 600


def _lista_de_textos(v: Any, teto: int) -> List[str]:
    return [str(x).strip() for x in (v or []) if isinstance(x, str) and str(x).strip()][:teto]


def marca_da_venda(db: Any, company_id: str) -> Dict[str, Any]:
    """Os FATOS da marca que a página de venda mostra em "Por que fechar com a corretora" — só da marca PUBLICADA
    (o mesmo critério da anfitriã) e com filtro `company_id` (CLAUDE.md §7): {diferenciais, sobre,
    seguradoras_parceiras}. Campo vazio não entra (o bloco some — D-132B-02)."""
    perfis = _dados(db.table("brand_profiles").select("*").eq("company_id", company_id).limit(1).execute())
    perfil = next((p for p in perfis if str(p.get("company_id")) == company_id), None)
    if not _marca_publicada(perfil):
        return {}
    from app.services.artifacts.proposta_cotacao_html import TETO_DE_DIFERENCIAIS, TETO_DE_PARCEIRAS_LIDAS

    saida: Dict[str, Any] = {}
    difs = _lista_de_textos(perfil.get("differentiators"), TETO_DE_DIFERENCIAIS)
    if difs:
        saida["diferenciais"] = difs
    # laudo de design 132-B, D2: o que VENDE primeiro (o lema, a missão); a história do cadastro só como reserva
    sobre = str(perfil.get("tagline") or perfil.get("mission") or perfil.get("about_md") or "").strip()
    if sobre:
        saida["sobre"] = sobre[:_TETO_DO_SOBRE]
    parceiras = {CFG.normalizar(x) for x in _lista_de_textos(perfil.get("insurers"), TETO_DE_PARCEIRAS_LIDAS)}
    if len(parceiras) > 1:
        saida["seguradoras_parceiras"] = len(parceiras)
    return saida


def _parcela_do_chat(o: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """A MESMA parcela que a página mostra (`proposta_cotacao_html._parcela`): a maior sem juros, senão a com juros."""
    from app.services.artifacts.proposta_cotacao_html import _parcela

    p = _parcela(dict(o))
    if not p:
        return None
    saida = {"vezes": int(p["vezes"]), "valor": float(p["valor"]), "sem_juros": bool(p["sem_juros"])}
    if p.get("total") is not None:
        saida["total"] = float(p["total"])
    return saida


def resumo_da_cotacao(modelo: Mapping[str, Any]) -> Dict[str, Any]:
    """O que o CHAT mostra da cotação pronta (B1): quantas seguradoras e as opções NA ORDEM da página (a recomendada
    primeiro) — {seguradoras_cotadas, com_preco_comparavel, validade_ate, opcoes: [{id, papel, seguradora, parcela,
    a_vista, franquia}]}. ⛔ Sem comissão, sem dado do cliente."""
    from app.services.artifacts import proposta_html as PH

    from app.services.artifacts.proposta_cotacao_html import opcoes_da_venda

    ops = opcoes_da_venda(dict(modelo))
    resumo = modelo.get("resumo") if isinstance(modelo.get("resumo"), Mapping) else {}
    conta = PH._conta_do_resumo(dict(modelo))
    saida_ops = []
    for o in ops:
        fq = o.get("franquia") if isinstance(o.get("franquia"), Mapping) else {}
        saida_ops.append({"id": o.get("id"), "papel": o.get("rotulo"), "seguradora": o.get("seguradora"),
                          "parcela": _parcela_do_chat(o), "a_vista": o.get("premio_anual"),
                          "franquia": fq.get("valor")})
    return {"seguradoras_cotadas": conta["cotadas"] if conta else resumo.get("seguradoras_cotadas"),
            "com_preco_comparavel": resumo.get("com_preco_comparavel"),
            "validade_ate": modelo.get("validade_ate"), "opcoes": saida_ops}


def bloco_da_venda(*, corretor: Mapping[str, Any], marca: Mapping[str, Any], pagina: Mapping[str, Any],
                   destino: Optional[str]) -> Dict[str, Any]:
    """O que a página de VENDA mostra além do CONTRATO §5 (`modelo["venda"]`). ⛔ Do corretor, só o primeiro nome e o
    WhatsApp de TRABALHO confirmado; nada do cliente. Os diferenciais: os da config da cotação (a corretora escreveu
    para esta página) → senão os da marca publicada → senão nenhum (o bloco some)."""
    bloco: Dict[str, Any] = {}
    c = {k: corretor[k] for k in ("primeiro_nome", "whatsapp") if corretor.get(k)}
    if c:
        bloco["corretor"] = c
    from app.services.artifacts.proposta_cotacao_html import TETO_DE_DIFERENCIAIS

    difs = list(pagina.get("diferenciais") or []) or list(marca.get("diferenciais") or [])
    if difs:
        bloco["diferenciais"] = difs[:TETO_DE_DIFERENCIAIS]
    m = {k: marca[k] for k in ("sobre", "seguradoras_parceiras") if marca.get(k)}
    if m:
        bloco["marca"] = m
    bloco["depois_do_sim"] = list(pagina.get("depois_do_sim") or [])
    bloco["faq"] = [dict(f) for f in pagina.get("faq") or []]
    bloco["fechar_com"] = ("corretor" if corretor.get("whatsapp") and destino == corretor.get("whatsapp")
                           else "corretora" if destino else "nenhum")
    return bloco


#: o que muda no modelo a cada montagem SEM mudar a página que o cliente vê (o carimbo da montagem)
_VOLATEIS_DO_MODELO = ("gerado_em",)


def _impressao_do_modelo(modelo: Mapping[str, Any]) -> str:
    """O modelo como TEXTO canônico (chaves ordenadas, sem o carimbo da montagem): duas montagens iguais = a mesma
    página. O JSON é o mesmo que o banco guarda (jsonb), então a versão lida de volta compara igual."""
    import json

    return json.dumps({k: v for k, v in dict(modelo or {}).items() if k not in _VOLATEIS_DO_MODELO},
                      sort_keys=True, ensure_ascii=False, default=str)


def link_que_ainda_vale(db: Any, company_id: str, pedido_id: str, modelo: Mapping[str, Any], base: str, *,
                        agora: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """SPEC-132-B (B4, pedido da B3): o link JÁ publicado deste pedido, se a página que ele mostra é EXATAMENTE a que
    se publicaria agora — o mesmo modelo (as opções, o "Quero fechar" de quem atende, a marca, a validade) — e o link
    ainda vale (não revogado, não vencido, não esgotado). Assim o "Ver apresentação"/"Copiar mensagem" da aba Cotações
    não cria uma versão e um link novos a cada clique. Qualquer diferença (quem atende mudou, o recálculo trouxe outro
    preço, virou o dia da validade) → None, e quem chama REPUBLICA. Leitura que falha → None (na dúvida, republica).
    🔴 Filtro `company_id` em toda leitura (CLAUDE.md §7)."""
    try:
        existente = _proposta_existente(db, company_id, pedido_id)
        if not existente:
            return None
        artifact_id = str(existente["id"])
        versoes = [v for v in _dados(db.table("artifact_versions")
                                     .select("id, artifact_id, company_id, version, status, payload")
                                     .eq("artifact_id", artifact_id).eq("company_id", company_id)
                                     .eq("status", "published").order("version", desc=True).limit(1).execute())
                   if str(v.get("company_id")) == company_id and str(v.get("artifact_id")) == artifact_id]
        if not versoes or not isinstance(versoes[0].get("payload"), Mapping):
            return None
        v = versoes[0]
        if _impressao_do_modelo(v["payload"]) != _impressao_do_modelo(modelo):
            return None
        instante = _agora(agora)
        validos = []
        for sh in _dados(db.table("artifact_shares")
                         .select("id, company_id, artifact_id, artifact_version_id, token, expires_at, revoked_at, "
                                 "max_views, view_count, audience_label")
                         .eq("company_id", company_id).eq("artifact_version_id", str(v["id"])).execute()):
            if (str(sh.get("company_id")) != company_id or str(sh.get("artifact_version_id")) != str(v["id"])
                    or sh.get("revoked_at") or sh.get("audience_label") != "cliente" or not sh.get("token")):
                continue
            fim = _instante(sh.get("expires_at"))
            if fim is None or fim <= instante:
                continue
            if sh.get("max_views") and int(sh.get("view_count") or 0) >= int(sh["max_views"]):
                continue
            validos.append((fim, sh))
        if not validos:
            return None
        _fim, sh = max(validos, key=lambda x: x[0])
        return {"url": f"{base}/r/{sh['token']}", "token": sh["token"], "artifact_id": artifact_id,
                "versao": int(v.get("version") or 1), "reaproveitado": True}
    except Exception as exc:  # noqa: BLE001 — na dúvida, republica (nunca um link que talvez não valha)
        logger.info("[PROPOSTA] link anterior ilegível (%s): republica", type(exc).__name__)
        return None


def apolice_com_prova(apolice_atual: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """A apólice atual como a página da COTAÇÃO pode usá-la: a seguradora sempre; o prêmio SÓ com
    `origem == "documento"` (lido e conferido pela ficha — SPEC-132-B §4.4, mutação 5). O prêmio que alguém DISSE nunca
    vira "economia" na página do cliente. Sem a seguradora → None."""
    if not isinstance(apolice_atual, Mapping) or not str(apolice_atual.get("seguradora") or "").strip():
        return None
    saida: Dict[str, Any] = {"seguradora": str(apolice_atual["seguradora"]).strip()}
    if apolice_atual.get("origem") == "documento" and premio_atual(apolice_atual) is not None:
        saida.update({"premio_anual": premio_atual(apolice_atual), "origem": "documento",
                      "base": str(apolice_atual.get("base") or "liquido")})
    return saida


async def publicar_cotacao(company_id: str, pedido_id: str, *, pessoa_user_id: Any,
                           apolice_atual: Optional[Mapping] = None, db: Any = None,
                           primeiro_nome: Optional[str] = None, base_url: Optional[str] = None,
                           agora: Optional[datetime] = None, baixar_logo: Optional[BaixarLogo] = None,
                           exemplo: bool = False, ajuste_calculo_id: Optional[str] = None) -> Dict[str, Any]:
    """SPEC-132-B (contrato B2 → B1/B3): a página de VENDA de uma cotação, publicada no `/r/` rastreado pelo MESMO
    caminho da proposta (artefato `proposal.quote` no Hub; publicar de novo = versão nova da mesma peça — CLAUDE.md §5).
    Devolve {token, url, artifact_id, versao, validade_ate, resumo, modelo}; `resumo` = as opções para o chat
    (`resumo_da_cotacao`).

    🔴 `company_id` é o da SESSÃO: o pedido é lido pela porta com o filtro (outra corretora → `NaoEncontrado`).
    🔴 O "Quero fechar" vai ao WhatsApp de TRABALHO CONFIRMADO de quem cotou (`pessoa_user_id`, membro ATIVO desta
       corretora) → senão ao da corretora → senão a página publica SEM botão e diz "responda a mensagem em que recebeu
       este link" (D-131-44). NUNCA recusa por falta de número: o link vai pelo CORRETOR (D-132B-05).
    🔴 Com `apolice_atual` a situação é `novo_com_apolice` (a economia SÓ aparece assim); sem ela, `novo_sem_apolice`.
    🔴 Conserto juiz B2 + RT B-1: o prêmio da apólice só entra (e com ele a economia) quando veio do DOCUMENTO lido
       (`apolice_atual.origem == "documento"`, a ficha da 130-B conferida); qualquer outro prêmio é descartado aqui —
       a seguradora fica ("Igual à sua atual"), o número não.
    `ajuste_calculo_id` (conserto juiz B1 + RT B-2): a página DEPOIS do recálculo — a opção ajustada com as ofertas do
    cálculo de ajuste (`comparacao.estados_do_recalculo`); o modelo muda, e com ele a versão e o link.
    `primeiro_nome`: o do CLIENTE (só o primeiro entra). `exemplo=True` (D-132B-08): a faixa "Exemplo — dados
    fictícios" no topo — só para as páginas de exemplo.
    ⛔ O telefone e o CPF do cliente nunca entram no modelo nem no HTML.

    Recusas: `ValueError` (uuid; apólice sem a seguradora) · `NaoEncontrado` · `PropostaImpossivel` (sem oferta
    completa; pedido de canal) · `LinkSemEndereco`."""
    company_id, pedido_id = _uuid(company_id, "company_id"), _uuid(pedido_id, "pedido_id")
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    base = _base_do_link(base_url)
    apolice_atual = apolice_com_prova(apolice_atual)
    situacao = "novo_com_apolice" if apolice_atual else "novo_sem_apolice"
    ctx: Dict[str, Any] = {}
    modelo = await montar_proposta(company_id, pedido_id, situacao, apolice_atual, primeiro_nome, db=db, agora=agora,
                                   baixar_logo=baixar_logo, ajuste_calculo_id=ajuste_calculo_id or None, _contexto=ctx)
    if modelo.get("origem") != "corretora":
        raise PropostaImpossivel("a página de venda é da corretora: este pedido é do canal comparador")

    corretor = membro_para_o_cliente(db, company_id, pessoa_user_id) if pessoa_user_id else {}
    destino = corretor.get("whatsapp") or (modelo.get("anfitria") or {}).get("whatsapp")
    nome_cliente = (modelo.get("cliente") or {}).get("primeiro_nome")
    modelo["cta"] = cta_da_pagina(destino, modelo["opcoes"], nome=nome_cliente, ref_curta=pedido_id[:8])
    cfg_cot = CFG.carregar(company_id, db=db, servico="cotacao")
    modelo["venda"] = bloco_da_venda(corretor=corretor, marca=marca_da_venda(db, company_id),
                                     pagina=CFG.pagina_da_cotacao(cfg_cot), destino=destino)
    modelo["faq"] = [{"p": f["pergunta"], "r": f["resposta"]} for f in modelo["venda"]["faq"]]
    modelo["sinistro"] = MANUAL.sinistro_padrao(cfg_cot, com_whatsapp=bool(destino))
    modelo["pagina"] = "venda"
    if exemplo:
        modelo["exemplo"] = True
    _sem_comissao(modelo)
    publicada_por = corretor.get("user_id") or (str(pessoa_user_id) if pessoa_user_id else None)
    # 🔴 B4: a MESMA página já publicada com um link que vale → o mesmo link (nada é gravado); senão, versão nova
    publicado = link_que_ainda_vale(db, company_id, pedido_id, modelo, base, agora=agora) or _gravar_e_compartilhar(
        db, company_id, pedido_id, modelo, ctx, base, titulo_base="Cotação de seguro",
        subject_extra={"pagina": "venda", "publicada_por": publicada_por})
    return {**publicado, "validade_ate": modelo["validade_ate"], "resumo": resumo_da_cotacao(modelo),
            "modelo": modelo}
