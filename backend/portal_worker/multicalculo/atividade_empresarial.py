# -*- coding: utf-8 -*-
"""A ATIVIDADE do empresarial, por seguradora — SPEC-129-C D-129C-04 (85 × "pedir humano sempre" 50).

📊 No empresarial (ramo 18) a atividade NÃO é um campo do risco: cada seguradora tem a SUA lista de códigos, e a tela
chama `GET pdocs/calculo/getOptionsBySegFull?executionType=10&filterText=<texto>` → `[{seguradora, KeyValue: [{Key,
Value, Description}]}]` (formulario_empresarial.json `atividade_por_seguradora`, B0-a 11/10). O código escolhido vai no
ITEM: `calculos[].valoresAjusteSeguradora.imovelAtividadeProfissionalLocal = {Key, Value, Description}` (📊 9/9 itens de
gravacao_empresarial_2). Seguradora sem atividade fica fora do cálculo (a própria tela a desmarca).

🔴 A regra: o código de cada seguradora só é escolhido quando o casamento é INEQUÍVOCO — um e só um candidato. Empate ou
nenhum → a seguradora SAI e é devolvida como "sem atividade compatível" (nunca um código errado). Em ordem:
    1. EXATO ...... o rótulo (sem o código na frente e sem o sufixo entre parênteses) é o texto do pedido (± plural);
    2. PALAVRAS ... o rótulo contém TODAS as palavras significativas do pedido;
    3. CLASSE ..... o pedido cai numa das classes mais comuns (📊 AGREGADO-POR-RAMO §4: escritórios — de longe —,
                    postos de combustível, máquinas/equipamentos, artigos médicos/dentários e consultórios, salão de
                    beleza/estética) e o rótulo casa o padrão DA classe.
Antes dos três, saem os candidatos que não servem: o PAVIMENTO (térreo / a partir do 1º / 2º em diante — 📊 Allianz,
Yelum, Mitsui e Pottencial têm um código por andar para "escritório") e os QUALIFICADORES que mudam o risco (depósito,
informática/publicidade, coworking, automotivo… — só saem se o pedido não os disser).

Puro: sem rede. As opções chegam já filtradas pela lista branca (agger_robo.JS_ATIVIDADES).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


def normalizar(texto: Any) -> str:
    """minúscula, sem acento, sem º/°/ª, pontuação → espaço simples nas pontas (vírgula e barra ficam)."""
    s = str(texto or "").replace("º", "").replace("°", "").replace("ª", "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", s).strip()


_RE_CODIGO_NA_FRENTE = re.compile(r"^\s*[\w.,-]*\d[\w.,-]*\s+-\s+")   # "167 - " · "701.75 - "
_RE_SUFIXO = re.compile(r"\s*\([^)]*\)\s*$")                           # " (420-00)"


def rotulo_limpo(valor: Any) -> str:
    s = normalizar(valor)
    s = _RE_CODIGO_NA_FRENTE.sub("", s)
    return _RE_SUFIXO.sub("", s).strip()


_PARADAS = frozenset({"de", "da", "do", "das", "dos", "e", "em", "com", "para", "ou", "a", "o", "no", "na", "loja",
                      "lojas", "comercio", "servicos", "servico"})


def palavras(texto: str) -> Tuple[str, ...]:
    return tuple(p for p in re.findall(r"[a-z0-9]+", normalizar(texto)) if len(p) >= 4 and p not in _PARADAS)


def _tem_palavra(rotulo: str, p: str) -> bool:
    base = p[:-1] if p.endswith("s") else p
    return re.search(r"\b" + re.escape(base) + r"(s|es)?\b", rotulo) is not None


# --------------------------------------------------------------------------------------------------------------------
# As classes. 💭 a forma (termos de busca e padrões) é desenho; os RÓTULOS que elas aceitam/excluem são os MEDIDOS
# (📊 formulario_empresarial.json `amostra_medida_11_10["escritorio"]`, 15 seguradoras; gravacao_empresarial_1/2: os
# códigos que as pessoas escolheram para estética e escritório). A ordem importa: "clínica de estética" é BELEZA.
# --------------------------------------------------------------------------------------------------------------------
CLASSES: Tuple[Tuple[str, Dict[str, Any]], ...] = (
    ("beleza_estetica", {
        "sinonimos": ("estetica", "salao de beleza", "cabeleireir", "cabeleleir", "barbearia", "manicure"),
        "termos": ("estetica", "beleza"),
        # 📊 gravacao_empresarial_1 (escolha humana para uma clínica de estética): "CABELEIREIROS, SALAO DE BELEZA E/OU
        # ESTETICA" (Porto, Tokio), "CLINICA DE ESTETICA" (Zurich, Axa), "Salao de beleza, clinica de estetica…" (Yelum)
        "aceita": re.compile(r"estetic|beleza|cabele[il]?reir|barbearia"),
        "exclui": re.compile(r"automotiv|veicul|lava.?(jato|rapido)|fabrica|industria"),
    }),
    ("clinica_saude", {
        "sinonimos": ("clinica medica", "consultorio", "odontolog", "dentista", "dentari", "clinica odonto",
                      "artigos medicos", "medico", "medica"),
        "termos": ("consultorio", "clinica"),
        "aceita": re.compile(r"consultorio|clinica (medica|odontolog)|odontolog|dentari|medic"),
        "exclui": re.compile(r"estetic|veterinar"),
    }),
    ("posto_combustivel", {
        "sinonimos": ("posto de combustive", "posto de gasolina", "combustive", "gasolina"),
        "termos": ("combustivel", "posto"),
        "aceita": re.compile(r"posto.{0,40}(combust|gasolina)|(combust|gasolina).{0,40}posto"),
        "exclui": re.compile(r"saude|policial|telefon"),
    }),
    ("oficina", {
        "sinonimos": ("oficina",),
        "termos": ("oficina",),
        "aceita": re.compile(r"oficina"),
        "exclui": re.compile(r"costura|artesanat"),
    }),
    ("maquinas_equipamentos", {
        "sinonimos": ("maquinas", "equipamentos"),
        "termos": ("maquinas",),
        "aceita": re.compile(r"maquinas"),
        "exclui": re.compile(r"aluguel|costura"),
    }),
    ("escritorio", {
        "sinonimos": ("escritorio", "advocacia", "advogad", "contabilidade", "contabil", "contador"),
        "termos": ("escritorio",),
        # 📊 amostra "escritorio": fora os que são OUTRO risco com a palavra escritório — "BOLSA DE VALORES:
        # ESCRITORIOS" (Zurich), "…SERV. INFORMATICA OU PUBLIC…" (Porto), "…TRANSMISSAO ELETRONICA" (HDI, Sura),
        # "LEILOEIRO, ESCRITÓRIO E DEPÓSITO…" (Tokio), "Aluguel de máquinas… para escritório" e "…apoio administrativo"
        # (Ezze), "ESPAÇOS COWORKING" (Mapfre), "Edifício residencial e/ou escritórios…" (Bradesco)
        "aceita": re.compile(r"\bescritorio"),
        "exclui": re.compile(r"bolsa de valores|informatica|public|transmissao eletronica|leiloeiro|aluguel de maquinas|"
                             r"apoio administrativo|coworking|edificio residencial"),
    }),
)
# O CNAE só decide a classe quando o TEXTO não decide. Os códigos são da tabela oficial (IBGE, CNAE 2.3 subclasses):
CNAE_DA_CLASSE: Mapping[str, str] = {
    "8630504": "clinica_saude",        # Atividade odontológica (📊 3 negócios empresariais lidos — AGREGADO §4)
    "8630503": "clinica_saude",        # Atividade médica ambulatorial restrita a consultas
    "9602501": "beleza_estetica",      # Cabeleireiros, manicure e pedicure
    "9602502": "beleza_estetica",      # Atividades de estética e outros serviços de cuidados com a beleza
    "4731800": "posto_combustivel",    # Comércio varejista de combustíveis para veículos automotores
    "4520001": "oficina",              # Serviços de manutenção e reparação mecânica de veículos automotores
    "6911701": "escritorio",           # Serviços advocatícios (📊 2 negócios — AGREGADO §4)
    "6920601": "escritorio",           # Atividades de contabilidade
}
# Qualificadores que mudam o risco: o candidato que os tem SAI, a não ser que o pedido diga a mesma coisa.
# 📊 "FARMACIAS OU DROGARIAS (LOJAS)" × "(DEPOSITOS)" (Porto), "Depósito de produtos de padaria" × "Padaria e
# confeitaria" (Bradesco) — amostra_medida_11_10.
QUALIFICADORES: Tuple[str, ...] = ("deposito", "shopping", "aeroporto", "posto de combustivel")


def classe_do_pedido(atividade: Any, cnae: Any = None) -> Optional[str]:
    txt = normalizar(atividade)
    for nome, c in CLASSES:
        if any(s in txt for s in c["sinonimos"]):
            return nome
    return CNAE_DA_CLASSE.get(re.sub(r"\D", "", str(cnae or "")))


def termos_de_busca(atividade: Any, cnae: Any = None) -> Tuple[str, ...]:
    """O que a página procura em `getOptionsBySegFull` (≥ 3 letras, como a tela exige): o texto do pedido e os termos
    da classe. A união das respostas é a lista de candidatos de cada seguradora."""
    saida: List[str] = []
    txt = normalizar(atividade)
    if len(re.sub(r"[^a-z]", "", txt)) >= 3:
        saida.append(txt)
    classe = classe_do_pedido(atividade, cnae)
    for nome, c in CLASSES:
        if nome == classe:
            saida.extend(t for t in c["termos"] if t not in saida)
    return tuple(saida)


# O PAVIMENTO (📊 contrato.CODIGOS_MEDIDOS_RE: Térreo "0" · Primeiro "1" · Segundo em diante "2") × o rótulo
_ANDARES_TODOS = frozenset({"0", "1", "2"})


def andares_do_rotulo(rotulo: str) -> frozenset:
    if re.search(r"terreo ou (1|primeiro)", rotulo):
        return frozenset({"0", "1"})
    if re.search(r"\b2 ?o? andar|segundo andar|a partir do (2|segundo)", rotulo):
        return frozenset({"2"})
    if re.search(r"a partir do (1|primeiro)|andar superior|\b1 ?o? andar ou superior", rotulo):
        return frozenset({"1", "2"})
    if re.search(r"terreo|sobrado", rotulo):
        return frozenset({"0"})
    return _ANDARES_TODOS


def _candidatos(respostas: Iterable[Any]) -> Dict[int, List[dict]]:
    """[{termo, opcoes: [{seguradora, KeyValue: [...]}]}] → {seguradora: [opção única por Key]}."""
    por_seg: Dict[int, Dict[str, dict]] = {}
    for r in respostas or ():
        for bloco in (r or {}).get("opcoes") or ():
            if not isinstance(bloco, dict) or not isinstance(bloco.get("seguradora"), int):
                continue
            for kv in bloco.get("KeyValue") or ():
                if isinstance(kv, dict) and kv.get("Key") not in (None, "") and isinstance(kv.get("Value"), str):
                    por_seg.setdefault(bloco["seguradora"], {}).setdefault(str(kv["Key"]), kv)
    return {s: list(d.values()) for s, d in por_seg.items()}


def escolher(opcoes: Sequence[dict], atividade: Any, *, cnae: Any = None,
             pavimento: Optional[str] = None) -> Tuple[Optional[dict], str]:
    """(a opção escolhida | None, o motivo). Motivos: exato · palavras · classe · ambiguo · nenhum."""
    txt = normalizar(atividade)
    classe = classe_do_pedido(atividade, cnae)
    regra = dict(CLASSES).get(classe) if classe else None
    cands = []
    for o in opcoes:
        rot = rotulo_limpo(o.get("Value"))
        if any(q in rot and q not in txt for q in QUALIFICADORES):
            continue
        if regra and regra["exclui"].search(rot) and not regra["exclui"].search(txt):
            continue
        andares = andares_do_rotulo(rot)
        if pavimento in _ANDARES_TODOS:
            if pavimento not in andares:
                continue
        elif andares != _ANDARES_TODOS:
            continue        # sem o andar do pedido, um código "por andar" não é inequívoco
        cands.append((rot, o))
    alvo = {txt, txt + "s", txt[:-1] if txt.endswith("s") else txt}
    exatos = [o for rot, o in cands if rot in alvo]
    if len(exatos) == 1:
        return exatos[0], "exato"
    if len(exatos) > 1:
        return None, "ambiguo"
    ps = palavras(txt)
    if ps:
        com_todas = [o for rot, o in cands if all(_tem_palavra(rot, p) for p in ps)]
        if len(com_todas) == 1:
            return com_todas[0], "palavras"
        if len(com_todas) > 1:
            return None, "ambiguo"
    if regra:
        da_classe = [o for rot, o in cands if regra["aceita"].search(rot)]
        if len(da_classe) == 1:
            return da_classe[0], "classe"
        if len(da_classe) > 1:
            return None, "ambiguo"
    return None, "nenhum"


def escolher_atividades(respostas: Iterable[Any], atividade: Any, *, cnae: Any = None,
                        pavimento: Optional[str] = None,
                        seguradoras: Optional[Iterable[int]] = None) -> Tuple[Dict[int, dict], Dict[int, str]]:
    """Para cada seguradora: o {Key, Value, Description} inequívoco, ou o motivo de ter ficado FORA.
    `seguradoras` = as do cálculo (as que não apareceram em nenhuma resposta saem com motivo 'nenhum')."""
    cands = _candidatos(respostas)
    alvo = sorted(set(seguradoras) if seguradoras is not None else set(cands))
    escolhidas: Dict[int, dict] = {}
    fora: Dict[int, str] = {}
    for s in alvo:
        o, motivo = escolher(cands.get(s, []), atividade, cnae=cnae, pavimento=pavimento)
        if o is None:
            fora[s] = motivo
        else:
            escolhidas[s] = {"Key": o.get("Key"), "Value": o.get("Value"), "Description": o.get("Description")}
    return escolhidas, fora
