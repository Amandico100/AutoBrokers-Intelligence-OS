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
        linhas = _dados(db.table("integrations").select("paired_phone_e164, purpose, is_active")
                        .eq("company_id", company_id).eq("purpose", "attendance").eq("is_active", True)
                        .limit(50).execute())   # o teto da leitura (o G8 proíbe os números da config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PROPOSTA] integrações ilegíveis: %s", type(exc).__name__)
        return None
    for l in linhas:
        if str(l.get("purpose")) == "attendance" and l.get("is_active") is True:
            dig = _digitos_de_whatsapp(l.get("paired_phone_e164"))
            if dig:
                return dig
    return None


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


async def montar_anfitria(db: Any, company_id: str, cfg: Mapping[str, Any], *,
                          baixar_logo: Optional[BaixarLogo] = None) -> Dict[str, Any]:
    """A anfitriã do modelo. 🔴 Filtro `company_id` em toda leitura (service role — CLAUDE.md §7)."""
    emp = _dados(db.table("companies").select("id, company_name").eq("id", company_id).limit(1).execute())
    nome_oficial = str((emp[0] if emp else {}).get("company_name") or "").strip() or None
    perfis = _dados(db.table("brand_profiles").select("*").eq("company_id", company_id).limit(1).execute())
    perfil = next((p for p in perfis if str(p.get("company_id")) == company_id), None)
    temas = ((perfil or {}).get("palette") or {}).get("themes") or {}
    publicada = bool(perfil and perfil.get("is_published") is True and temas.get("light") and temas.get("dark"))

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


def resumo_do_volume(ofertas: Sequence[Mapping[str, Any]], pedido: Mapping[str, Any],
                     cfg: Mapping[str, Any], estados: Sequence[Mapping[str, Any]] = ()) -> Dict[str, Any]:
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
        fora). Sem os dois instantes, ou < 1 s (o mesmo instante não é medida), o campo NÃO existe — e a linha some."""
    opcao_do_calculo = {str(e.get("calculo_id")): str(e.get("opcao") or "") for e in estados}
    precos = [o for o in ofertas if _preco(o) is not None
              and opcao_do_calculo.get(str(o.get("calculo_id"))) in OPCOES_DO_PEDIDO]
    saida: Dict[str, Any] = {"cotacoes_realizadas": len(precos)}
    segs = set()
    for o in precos:
        if CFG.e_produto_de_assinatura(o.get("seguradora"), o.get("pacote"), cfg):
            continue
        cod = o.get("seguradora_codigo")
        segs.add(f"cod:{cod}" if cod not in (None, "") and not isinstance(cod, bool)
                 else "nome:" + CFG.normalizar(CMP.nome_de_exibicao(o.get("seguradora"))))
    saida["seguradoras_com_preco"] = len(segs)
    inicio = _instante(pedido.get("criado_em"))
    chegadas = [t for t in (_instante(o.get("recebida_em")) for o in precos) if t is not None]
    if inicio and chegadas:
        segundos = (max(chegadas) - inicio).total_seconds()
        if segundos >= 1:
            saida["tempo_do_calculo_s"] = int(segundos + 0.5)
    return saida


def economia(ranking_completo_do_pedido: Sequence[Mapping[str, Any]], opcoes: Sequence[Mapping[str, Any]],
             refs: Sequence[Mapping[str, Any]], *, opcao_completa: str,
             apolice_atual: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """SPEC-130-A.1 D-130A1-03 — "Você economiza até R$ X", com a ORIGEM da conta:

      · `ate` = `de` − `para`: `de` = a MAIS CARA com a mesma cobertura completa (o ranking completo do pedido, todas as
        corretoras); `para` = a mais barata MOSTRADA (entre as opções do modelo — a mínima, se houver).
        `mesma_cobertura` diz se a `para` é uma completa (a frase muda: a mais em conta cobre menos).
      · `vs_atual` só quando há apólice lida com prêmio: o prêmio atual − a 1ª opção (a menor completa), se a menos."""
    saida: Dict[str, Any] = {}
    precos = [float(r["premio_anual"]) for r in ranking_completo_do_pedido if r.get("premio_anual")]
    validas = [(o, r) for o, r in zip(opcoes, refs) if o.get("premio_anual")]
    if precos and validas:
        de = max(precos)
        o_para, r_para = min(validas, key=lambda x: float(x[0]["premio_anual"]))
        para = float(o_para["premio_anual"])
        if de - para >= 0.01:
            saida.update({"ate": round(de - para, 2), "de": round(de, 2), "para": round(para, 2),
                          "para_opcao": o_para.get("id"),
                          "mesma_cobertura": str((r_para or {}).get("opcao") or "") == opcao_completa})
    atual = (apolice_atual or {}).get("premio_anual") if isinstance(apolice_atual, Mapping) else None
    if atual and opcoes and opcoes[0].get("premio_anual"):
        try:
            atual_f, base = float(atual), float(opcoes[0]["premio_anual"])
        except (TypeError, ValueError):
            atual_f, base = 0.0, 0.0
        if atual_f - base >= 0.01:
            saida["vs_atual"] = {"atual": round(atual_f, 2), "para": round(base, 2), "valor": round(atual_f - base, 2)}
    return saida or None


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
            g = _google(CFG.carregar(c, db=db))
        except Exception:  # noqa: BLE001 — sem a nota, o critério seguinte decide
            g = None
        if g:
            info[c]["nota_google"] = g["nota"]
    return info


async def montar_proposta(company_id: str, pedido_id: str, situacao: str, apolice_atual: Optional[Mapping] = None,
                          primeiro_nome: Optional[str] = None, *, db: Any, agora: Optional[datetime] = None,
                          baixar_logo: Optional[BaixarLogo] = None, _contexto: Optional[dict] = None
                          ) -> Dict[str, Any]:
    """O MODELO da página (CONTRATO §5). `company_id` = o SOLICITANTE (a corretora, ou o canal).

    Recusas: `ValueError` (uuid/situação) · `NaoEncontrado` (o pedido não é deste solicitante) ·
    `PropostaImpossivel` (a anfitriã não tem oferta completa) · `config.ConfigIndisponivel` (banco fora)."""
    company_id, pedido_id = _uuid(company_id, "company_id"), _uuid(pedido_id, "pedido_id")
    if situacao not in CMP.SITUACOES:
        raise ValueError(f"situação desconhecida: {situacao!r} (aceitas: {', '.join(CMP.SITUACOES)})")
    CMP.conferir_apolice(situacao, apolice_atual)                    # J-B2: nunca um "igual à sua atual" inventado
    repo = RepositorioMulticalculo(db)
    porta = MulticalculoProvider(repo, cifrar=_so_leitura)
    andamento = await porta.consultar(company_id=company_id, pedido_id=pedido_id)   # 🔴 a autorização de leitura
    ped = repo.pedido(company_id=company_id, pedido_id=pedido_id) or {}
    ramo = int(ped.get("ramo") or CMP.RAMO_AUTO)
    kind = repo.tipos_de_empresa([company_id]).get(company_id)
    origem = "canal" if kind == KIND_CANAL else "corretora"

    cfg_sol = CFG.carregar(company_id, db=db)
    ofertas, eventos, estados = list(andamento.ofertas), list(andamento.eventos), list(andamento.estados)
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
    cfg_anf = cfg_sol if anfitria_id == company_id else CFG.carregar(anfitria_id, db=db)

    # as opções: sem o `ref` interno; nível, juros com nome, "por que é mais barata", arredondamento único
    por_id = {str(o.get("id")): o for o in ofertas_a}
    brutas = [por_id.get(str(o["ref"]["oferta_id"]), {}) for o in ops]
    opcoes: List[Dict[str, Any]] = []
    for o, bruta in zip(ops, brutas):
        sem_juros = _parcelas_sem_juros(bruta)
        item = {k: v for k, v in o.items() if k != "ref"}
        item["motivos"] = [arredondar_texto(_texto_de_parcela(t, sem_juros)) for t in o["motivos"]]
        item["o_que_muda"] = [arredondar_texto(t) for t in o["o_que_muda"]]
        item["coberturas"] = [dict(c) for c in o["coberturas"]]
        total = _total_do_parcelamento(bruta, item.get("parcelas"))
        if total is not None:
            item["parcelas"] = dict(item["parcelas"], total=total)
        if sem_juros:
            item["parcelas_sem_juros"] = sem_juros
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
    resumo.update(resumo_do_volume(ofertas, ped, cfg_sol, estados))
    eco = economia(quadro_todo.ranking(quadro_todo.opcao_completa), opcoes, [o["ref"] for o in ops],
                   opcao_completa=quadro_todo.opcao_completa, apolice_atual=apolice_atual)
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
    nome = _primeiro_nome(primeiro_nome)
    bem = _bem(ofertas_a, ramo)
    ref_curta = pedido_id[:8]
    cta = None
    if whats:
        textos = {}
        for o in opcoes:
            preco = reais_inteiros(o["premio_anual"])
            textos[o["id"]] = (f"Olá!{' Aqui é ' + nome + '.' if nome else ''} Quero fechar a opção {o['rotulo']} "
                               f"({o['seguradora']}, {preco} por ano). Ref. {ref_curta}")
        cta = {"whatsapp_url": f"https://wa.me/{whats}", "texto_por_opcao": textos}

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
        "faq": _faq(cfg_anf, resumo=resumo, opcoes=opcoes, situacao=situacao, voz=origem,
                    com_whatsapp=bool(whats)),
        "sinistro": MANUAL.sinistro_padrao(cfg_anf, com_whatsapp=bool(whats)),
        "validade_ate": validade_ate,
        "gerado_em": hoje.replace(microsecond=0).isoformat(),
        "aviso_legal": AVISO_LEGAL_CANAL if origem == "canal" else AVISO_LEGAL_CORRETORA,
        "cta": cta,
        # D-130A-08 REVOGADA (SPEC-130-A.1): "nós não vendemos seguros" — nenhuma remuneração no modelo (G9)
    }
    if origem == "canal":                       # RT-10: o nome do canal é CONFIGURAÇÃO do produto, não constante
        nome_canal = str((cfg_sol.get("canal") or {}).get("nome") or "").strip()
        if nome_canal:
            modelo["canal"] = {"nome": nome_canal}
    _sem_comissao(modelo)
    if _contexto is not None:                       # o que `publicar_proposta` precisa e a página não mostra
        _contexto.update({"anfitria_id": anfitria_id, "cfg_sol": cfg_sol, "dias": dias, "hoje": hoje,
                          "refs": {o["id"]: dict(o["ref"]) for o in ops}})
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
                            permitir_sem_whatsapp: bool = False) -> Dict[str, Any]:
    """Monta, cria/versiona, renderiza, publica e compartilha. Devolve {url, token, artifact_id, versao, mensagem}.

    🔴 Nada é gravado antes de: o pedido ser deste solicitante (a porta), haver o que propor e haver endereço público
    para o link. O artefato mora no SOLICITANTE; a anfitriã nunca recebe linha (D-130A-10). Publicar de novo o mesmo
    pedido = VERSÃO nova da mesma peça (a publicada é imutável), e o assunto (anfitriã, ofertas) acompanha a versão.

    🔴 J-B1: sem WhatsApp de atendimento da anfitriã → `SemCanalDeFechamento` antes de gravar (a página não teria como
    fechar). Só `permitir_sem_whatsapp=True` publica assim — e aí nenhuma frase da página promete WhatsApp."""
    from app.services.artifacts.service import ArtifactService, base_publica_do_app, tags_do_canario
    from app.services.multicalculo.mensagem import mensagem_para

    company_id, pedido_id = _uuid(company_id, "company_id"), _uuid(pedido_id, "pedido_id")
    base = (base_url or base_publica_do_app() or "").strip().rstrip("/")
    if not re.match(r"^https?://[^/\s]+$", base):
        raise LinkSemEndereco("sem o endereço público do painel (PUBLIC_APP_URL/SMITH_WEB_URL) o link não tem host")

    ctx: Dict[str, Any] = {}
    modelo = await montar_proposta(company_id, pedido_id, situacao, apolice_atual, primeiro_nome, db=db, agora=agora,
                                   baixar_logo=baixar_logo, _contexto=ctx)
    if not (modelo.get("anfitria") or {}).get("whatsapp") and not permitir_sem_whatsapp:
        quem = (modelo.get("anfitria") or {}).get("nome") or "a corretora anfitriã"
        raise SemCanalDeFechamento(
            f"{quem} não tem WhatsApp de atendimento cadastrado (nem na marca publicada, nem numa integração de "
            "atendimento ativa): a página sairia sem o botão \"Quero fechar\" e o cliente não teria como fechar. "
            "Cadastre o WhatsApp de atendimento dela — ou publique assim mesmo, de propósito, com "
            "permitir_sem_whatsapp (no comando: --sem-whatsapp). Nada foi gravado.")
    rec = modelo["opcoes"][0]
    bem = (modelo.get("bem") or {}).get("descricao")
    titulo = f"Proposta de seguro{' · ' + bem if bem else ''}"
    resumo_peca = (f"{rec['rotulo']}: {rec['seguradora']}, {reais_inteiros(rec['premio_anual'])} por ano · "
                   f"{modelo['resumo']['com_preco_comparavel']} seguradoras comparáveis · válida até "
                   f"{modelo['validade_ate']}")
    subject = {"kind": "multicalculo_pedido", "pedido_id": pedido_id, "anfitria_company_id": ctx["anfitria_id"],
               "opcoes": ctx["refs"]}
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
            "versao": int(publicada.get("version") or versao.get("version") or 1),
            "mensagem": mensagem_para(modelo, url, config=ctx["cfg_sol"]), "validade_ate": modelo["validade_ate"]}
