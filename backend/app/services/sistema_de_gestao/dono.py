# -*- coding: utf-8 -*-
"""Quem é o DONO de uma renovação, e que pessoa da corretora responde por ele — SPEC-131-0 F2 (U2 + U3).

O FIO deste módulo:

    apólice (codfil, nosnum) → `/prod_docs` AVULSO da InfoCap DA CORRETORA (aberta por `_abrir`, nunca por nome)
      → `regra_de_dono` (a linha da corretora em `regras_de_dono`, senão o padrão do SISTEMA em JSON)
      → o produtor que atende à regra → `membro_produtores` → `user_id` membro ATIVO da corretora

As decisões (FOUNDER-DECISIONS):
    D-131-0-03  o dono na InfoCap = o produtor `indireto="F"` do `/prod_docs` avulso.
                📊 11/10/2026, as duas carteiras reais medidas: 99/99 e 217/217 (BLOCO0-INFOCAP §4). `ordem == 1` acerta 37/99 e 24/217.
    D-131-0-30  o vínculo é `(user_id, company_id)` → `company_members` ON DELETE CASCADE: saiu da equipe, o vínculo
                cai e a renovação dele vira "sem dono" — nunca de outra pessoa.
    D-131-0-31  a regra é DADO, e quem decidiu (corretora × padrão do sistema) é dito em `origem`.

🔴 CLAUDE.md §7: o backend usa service role — TODA leitura e escrita aqui filtra `company_id` no código, e o que
volta do banco é conferido de novo contra a corretora pedida (fail-closed).
🔴 CLAUDE.md §13.9: nenhum nome de corretora. A conexão vem de `infocap_analytics_provider._abrir(company_id)`.
⛔ Nada aqui escreve no sistema de gestão. Nada aqui devolve nome de CLIENTE.
"""
from __future__ import annotations

import asyncio
import difflib
import json
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)

SISTEMAS = ("infocap", "quiver", "outro")
STATUS = ("ok", "sem_dono", "ambiguo", "sem_membro", "sem_conexao")
ORIGEM_CORRETORA = "corretora"
ORIGEM_PADRAO = "padrao_do_sistema"
#: a régua aceita uma regra injetada (a mutação do gate: "e se o dono fosse o `ordem 1`?")
ORIGEM_INJETADA = "injetada"

TABELA_VINCULOS = "membro_produtores"
TABELA_REGRAS = "regras_de_dono"
ARQUIVO_DA_REGRA_PADRAO = "regra-de-dono-padrao.json"

#: as rotas que este módulo SABE ler por sistema. Uma regra que aponte outra rota é recusada na escrita: gravar uma
#: regra que nenhum leitor executa seria uma promessa vazia na tela.
ROTAS_LIDAS = {"infocap": ("/prod_docs",)}
_CHAVES_DA_REGRA = ("sistema", "rota", "campo", "igual", "codigo", "nome", "papel_no_nome")
_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,40}$")
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

#: 📊 o papel vem como SUFIXO do nome do produtor (`/produtores`, 11/10/2026, 119 nomes: FECHADORA 10 · INDICADOR 9 ·
#: INDICADORA 9 · FECHADOR 5 · EXECUTIVO 2; separador " " em 78 e " - " em 12). É procedência CRUA: nunca decide o
#: dono (quem decide é a regra) e nunca vira vínculo trabalhista.
_RE_PAPEL = re.compile(r"(?:^|[\s\-–—]+)(FECHADORA?|EXECUTIV[OA]|INDICADORA?|CORRETORA?)\s*$")
_RE_CODIGO_NA_FRENTE = re.compile(r"^\s*\d+\s*[-–]\s*")
#: palavras que não identificam pessoa (a comparação de nomes as ignora)
_PALAVRAS_VAZIAS = frozenset({"DA", "DE", "DO", "DAS", "DOS", "E", "SEG", "SEGUROS", "CORRETORA", "CORRETOR",
                              "CAMPANHA", "LTDA", "ME"})
#: a nota mínima, e a folga sobre a segunda pessoa, para a tela SUGERIR (nunca gravar) um vínculo
NOTA_MINIMA_DA_SUGESTAO = 0.8
FOLGA_SOBRE_A_SEGUNDA = 0.05


class Recusa(ValueError):
    """Pedido recusado — a mensagem é a frase que a pessoa lê na tela (português de gente)."""


# --------------------------------------------------------------------------------------------------------------------
# O que sai daqui
# --------------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Regra:
    sistema: str
    rota: str
    campo: str
    igual: str
    codigo: str
    nome: Optional[str]
    papel_no_nome: bool
    origem: str

    def como_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DonoDaApolice:
    status: str
    codigo_produtor: Optional[str] = None
    papel_cru: Optional[str] = None
    user_id: Optional[str] = None
    regra_origem: Optional[str] = None
    motivo: str = ""

    def como_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Candidato:
    codigo: str
    nome: str
    papel_cru: Optional[str]
    ordem: Optional[str]


# --------------------------------------------------------------------------------------------------------------------
# Ajudantes puros
# --------------------------------------------------------------------------------------------------------------------
def _uuid(valor: Any, nome: str = "company_id") -> str:
    v = str(valor or "").strip().lower()
    if not _UUID.match(v):
        raise Recusa(f"{nome} inválido")
    return v


def _sistema(valor: Any) -> str:
    s = str(valor or "").strip().lower()
    if s not in SISTEMAS:
        raise Recusa("sistema de gestão desconhecido")
    return s


def _codfil(valor: Any) -> int:
    try:
        n = int(str(valor if valor is not None else 1).strip())
    except (TypeError, ValueError):
        raise Recusa("filial inválida") from None
    if n < 1:
        raise Recusa("filial inválida")
    return n


def codigo_normalizado(valor: Any) -> str:
    """`247`, `"247"` e `"0247"` são o MESMO código. Texto não numérico fica como veio (sem espaços nas pontas)."""
    if valor is None or isinstance(valor, bool):
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    s = str(valor).strip()
    return str(int(s)) if s.isdigit() else s


def _valor_comparavel(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip().upper()


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto or "")) if not unicodedata.combining(c))


def papel_do_nome(nome: Any) -> Optional[str]:
    """O papel CRU escrito no fim do nome do produtor (`FECHADOR`, `INDICADORA`…), ou None ("sem rótulo")."""
    m = _RE_PAPEL.search(_sem_acento(str(nome or "")).strip().upper())
    return m.group(1) if m else None


def nome_sem_papel(nome: Any) -> str:
    """O nome do produtor sem o código na frente e sem o papel no fim — é o que se compara com o nome da pessoa."""
    s = _RE_CODIGO_NA_FRENTE.sub("", str(nome or "").strip())
    m = _RE_PAPEL.search(_sem_acento(s).upper())
    if m:
        s = s[: m.start()]
    return s.strip(" -–—.").strip()


def _tokens(nome: str) -> List[str]:
    partes = re.split(r"[^A-Z0-9]+", _sem_acento(nome).upper())
    return [p for p in partes if len(p) >= 3 and p not in _PALAVRAS_VAZIAS]


def nota_de_semelhanca(nome_do_produtor: str, nome_da_pessoa: str) -> float:
    """0–1: quanto o nome do produtor (sem o papel) lembra o nome da pessoa. Iniciais soltas não contam.

    `MEMB` × `Membro Teste` → 0,9 (prefixo); `M. MEMB` → o `M` cai; `R.L.S.` → 0 (nada para comparar)."""
    tp, tm = _tokens(nome_do_produtor), _tokens(nome_da_pessoa)
    if not tp or not tm:
        return 0.0
    total = 0.0
    for a in tp:
        melhor = 0.0
        for b in tm:
            if a == b:
                s = 1.0
            elif min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
                s = 0.9
            else:
                s = difflib.SequenceMatcher(None, a, b).ratio()
            melhor = max(melhor, s)
        total += melhor
    return round(total / len(tp), 3)


def _t(db: Any, tabela: str) -> Any:
    alvo = db if hasattr(db, "table") else getattr(db, "client", db)
    return alvo.table(tabela)


def _dados(resp: Any) -> List[Dict[str, Any]]:
    d = getattr(resp, "data", None) if resp is not None else None
    if isinstance(d, dict):
        return [d]
    return [x for x in (d or []) if isinstance(x, dict)]


def _mesma(a: Any, b: str) -> bool:
    return str(a or "").strip().lower() == b


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------------------------------------------------
# A regra do dono — DADO, com origem
# --------------------------------------------------------------------------------------------------------------------
def validar_regra(bruta: Any, sistema: str = "infocap") -> Dict[str, Any]:
    """A forma de uma regra de dono, normalizada — ou `Recusa` com a frase que a tela mostra.

    Chaves `_…` são comentário e caem. Chave desconhecida é recusada: uma regra com um campo que nenhum leitor
    conhece seria lida como outra coisa, em silêncio."""
    sis = _sistema(sistema)
    if not isinstance(bruta, Mapping):
        raise Recusa("a regra precisa ser um objeto")
    regra = {k: v for k, v in bruta.items() if not str(k).startswith("_")}
    estranhas = sorted(set(regra) - set(_CHAVES_DA_REGRA))
    if estranhas:
        raise Recusa(f"a regra tem um campo que não conheço: {estranhas[0]}")
    if regra.get("sistema") not in (None, "", sis):
        raise Recusa("a regra é de outro sistema de gestão")
    campo = str(regra.get("campo") or "").strip()
    codigo = str(regra.get("codigo") or "").strip()
    if not _IDENT.match(campo):
        raise Recusa("a regra precisa dizer qual campo decide o dono")
    if not _IDENT.match(codigo):
        raise Recusa("a regra precisa dizer qual campo traz o código do produtor")
    igual = _valor_comparavel(regra.get("igual"))
    if igual is None or len(igual) > 40:
        raise Recusa("a regra precisa dizer o valor que marca o dono")
    nome = regra.get("nome")
    nome = str(nome).strip() if nome not in (None, "") else None
    if nome is not None and not _IDENT.match(nome):
        raise Recusa("o campo do nome do produtor é inválido")
    papel = regra.get("papel_no_nome", False)
    if not isinstance(papel, bool):
        raise Recusa("papel_no_nome precisa ser sim ou não")
    lidas = ROTAS_LIDAS.get(sis)
    rota = str(regra.get("rota") or (lidas[0] if lidas else "")).strip()
    if lidas is not None and rota not in lidas:
        raise Recusa("esta rota do sistema de gestão ainda não é lida pelo AutoBrokers")
    if not rota.startswith("/"):
        raise Recusa("a regra precisa dizer de onde ler os produtores")
    return {"sistema": sis, "rota": rota, "campo": campo, "igual": igual, "codigo": codigo, "nome": nome,
            "papel_no_nome": papel}


def _regra(normalizada: Mapping[str, Any], origem: str) -> Regra:
    return Regra(origem=origem, **{k: normalizada[k] for k in _CHAVES_DA_REGRA})


@lru_cache(maxsize=8)
def _padrao_bruto(sistema: str) -> Optional[str]:
    from app.comercial import manifesto

    caminho = manifesto.caminho_do_censo(sistema, ARQUIVO_DA_REGRA_PADRAO)
    try:
        with open(caminho, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        if sistema in ROTAS_LIDAS:
            # 🔴 grita: sem o padrão, toda renovação de quem não gravou regra própria sai "sem dono"
            logger.error("[DONO] regra padrão AUSENTE para %s: %s", sistema, caminho)
        return None


def regra_padrao_do_sistema(sistema: str = "infocap") -> Optional[Regra]:
    """A regra que vale quando a corretora não gravou a dela. None se o sistema não tem padrão."""
    sis = _sistema(sistema)
    bruto = _padrao_bruto(sis)
    if not bruto:
        return None
    try:
        return _regra(validar_regra(json.loads(bruto), sis), ORIGEM_PADRAO)
    except (ValueError, Recusa) as exc:
        logger.error("[DONO] regra padrão de %s ilegível (%s)", sis, type(exc).__name__)
        return None


def regra_de_dono(db: Any, company_id: str, sistema: str = "infocap") -> Optional[Regra]:
    """A regra que decide o dono NESTA corretora: a linha dela em `regras_de_dono`, senão o padrão do sistema.

    `origem` diz qual das duas decidiu (D-131-0-31). Linha da corretora ilegível NÃO vale: cai no padrão, e a origem
    conta a verdade. Erro de banco sobe — não conseguir ler a regra não é o mesmo que não ter regra."""
    cid, sis = _uuid(company_id), _sistema(sistema)
    resp = (_t(db, TABELA_REGRAS).select("company_id, sistema, regra")
            .eq("company_id", cid).eq("sistema", sis).limit(1).execute())
    linhas = [l for l in _dados(resp) if _mesma(l.get("company_id"), cid) and l.get("sistema") == sis]
    if linhas:
        try:
            return _regra(validar_regra(linhas[0].get("regra"), sis), ORIGEM_CORRETORA)
        except Recusa as exc:
            logger.error("[DONO] regra da corretora %s ilegível (%s) — vale o padrão do sistema", cid[:8], exc)
    return regra_padrao_do_sistema(sis)


def aplicar_regra(linhas: List[Dict[str, Any]], regra: Regra) -> List[_Candidato]:
    """Os produtores DISTINTOS que atendem à regra. 0 = sem dono · 1 = o dono · 2+ = ambíguo."""
    alvo = regra.igual
    achados: Dict[str, _Candidato] = {}
    for linha in linhas or []:
        if not isinstance(linha, Mapping) or _valor_comparavel(linha.get(regra.campo)) != alvo:
            continue
        cod = codigo_normalizado(linha.get(regra.codigo))
        if not cod or cod in achados:
            continue
        nome = str(linha.get(regra.nome) or "").strip() if regra.nome else ""
        achados[cod] = _Candidato(codigo=cod, nome=nome,
                                  papel_cru=papel_do_nome(nome) if regra.papel_no_nome else None,
                                  ordem=codigo_normalizado(linha.get("ordem")) or None)
    return list(achados.values())


# --------------------------------------------------------------------------------------------------------------------
# A pessoa por trás do código
# --------------------------------------------------------------------------------------------------------------------
def membro_ativo(db: Any, company_id: str, user_id: str) -> bool:
    """`company_members.status='active'` NA corretora E `users_v2.status='active'` sem `deleted_at`."""
    cid = _uuid(company_id)
    uid = str(user_id or "").strip().lower()
    if not _UUID.match(uid):
        return False
    vinc = _dados(_t(db, "company_members").select("user_id, company_id, status")
                  .eq("company_id", cid).eq("user_id", uid).limit(1).execute())
    if not any(_mesma(v.get("company_id"), cid) and _mesma(v.get("user_id"), uid) and v.get("status") == "active"
               for v in vinc):
        return False
    pessoa = _dados(_t(db, "users_v2").select("id, status, deleted_at").eq("id", uid).limit(1).execute())
    return any(_mesma(p.get("id"), uid) and p.get("status") == "active" and not p.get("deleted_at")
               for p in pessoa)


def membro_do_produtor(db: Any, company_id: str, sistema: str, codfil: Any, codigo: Any) -> Optional[str]:
    """O `user_id` da pessoa ligada a este código de produtor NESTA corretora — só se ela for membro ATIVO."""
    cid, sis, fil, cod = _uuid(company_id), _sistema(sistema), _codfil(codfil), codigo_normalizado(codigo)
    if not cod:
        return None
    resp = (_t(db, TABELA_VINCULOS).select("user_id, company_id, sistema, codfil, codigo_produtor")
            .eq("company_id", cid).eq("sistema", sis).eq("codfil", fil).eq("codigo_produtor", cod)
            .limit(2).execute())
    linhas = [l for l in _dados(resp)
              if _mesma(l.get("company_id"), cid) and l.get("sistema") == sis
              and str(l.get("codfil")) == str(fil) and codigo_normalizado(l.get("codigo_produtor")) == cod]
    if len(linhas) != 1:   # 2 é impossível pela UNIQUE; se acontecer, ninguém é o dono (fail-closed)
        return None
    uid = str(linhas[0].get("user_id") or "")
    return uid if membro_ativo(db, cid, uid) else None


def membros_ativos(db: Any, company_id: str) -> List[Dict[str, str]]:
    """`[{user_id, nome}]` dos membros ativos da corretora. Sem e-mail, sem telefone."""
    cid = _uuid(company_id)
    vinc = _dados(_t(db, "company_members").select("user_id, company_id, status")
                  .eq("company_id", cid).eq("status", "active").execute())
    ids = sorted({str(v["user_id"]).lower() for v in vinc
                  if _mesma(v.get("company_id"), cid) and v.get("status") == "active" and v.get("user_id")})
    if not ids:
        return []
    pessoas = _dados(_t(db, "users_v2").select("id, first_name, last_name, status, deleted_at")
                     .in_("id", ids).execute())
    saida = []
    for p in pessoas:
        uid = str(p.get("id") or "").lower()
        if uid not in ids or p.get("status") != "active" or p.get("deleted_at"):
            continue
        nome = " ".join(x for x in (str(p.get("first_name") or "").strip(), str(p.get("last_name") or "").strip())
                        if x)
        saida.append({"user_id": uid, "nome": nome or "Sem nome"})
    return sorted(saida, key=lambda m: m["nome"].lower())


# --------------------------------------------------------------------------------------------------------------------
# Os vínculos (escrita só no banco do produto)
# --------------------------------------------------------------------------------------------------------------------
def listar_vinculos(db: Any, company_id: str, sistema: Optional[str] = None) -> List[Dict[str, Any]]:
    cid = _uuid(company_id)
    q = (_t(db, TABELA_VINCULOS)
         .select("id, company_id, user_id, sistema, codfil, codigo_produtor, nome_produtor, papel_cru, criado_em")
         .eq("company_id", cid))
    if sistema:
        q = q.eq("sistema", _sistema(sistema))
    linhas = [l for l in _dados(q.execute()) if _mesma(l.get("company_id"), cid)]
    nomes = {m["user_id"]: m["nome"] for m in membros_ativos(db, cid)}
    saida = []
    for l in linhas:
        uid = str(l.get("user_id") or "").lower()
        saida.append({
            "id": l.get("id"), "user_id": uid, "sistema": l.get("sistema"), "codfil": l.get("codfil"),
            "codigo_produtor": codigo_normalizado(l.get("codigo_produtor")), "nome_produtor": l.get("nome_produtor"),
            "papel_cru": l.get("papel_cru"), "criado_em": l.get("criado_em"),
            "membro_ativo": uid in nomes, "nome_do_membro": nomes.get(uid),
        })
    return sorted(saida, key=lambda v: (v["sistema"] or "", v["codfil"] or 0, v["codigo_produtor"]))


def vincular(db: Any, company_id: str, *, user_id: Any, sistema: Any, codfil: Any = 1, codigo_produtor: Any,
             nome_produtor: Any = None, papel_cru: Any = None, por_user_id: Any = None) -> Dict[str, Any]:
    """Liga um código de produtor a uma PESSOA da corretora. Recusa se ela não for membro ativo DESTA corretora, ou
    se o código já for de outra pessoa (desfaça o vínculo antes — nunca se troca o dono em silêncio)."""
    cid, sis, fil = _uuid(company_id), _sistema(sistema), _codfil(codfil)
    uid = _uuid(user_id, "pessoa")
    cod = codigo_normalizado(codigo_produtor)
    if not cod or len(cod) > 40:
        raise Recusa("informe o código do produtor")
    if not membro_ativo(db, cid, uid):
        raise Recusa("esta pessoa não é membro ativo da corretora")
    nome = str(nome_produtor or "").strip()[:120] or None
    papel = (str(papel_cru or "").strip().upper()[:40] or None) if papel_cru else papel_do_nome(nome)
    por = str(por_user_id or "").strip().lower()
    existentes = [l for l in _dados(_t(db, TABELA_VINCULOS).select("id, company_id, user_id, codigo_produtor")
                                    .eq("company_id", cid).eq("sistema", sis).eq("codfil", fil)
                                    .eq("codigo_produtor", cod).limit(2).execute())
                  if _mesma(l.get("company_id"), cid)]
    if existentes:
        if _mesma(existentes[0].get("user_id"), uid):
            return {"id": existentes[0].get("id"), "ja_existia": True}
        raise Recusa("este código de produtor já está ligado a outra pessoa — desfaça aquele vínculo antes")
    linha = {"company_id": cid, "user_id": uid, "sistema": sis, "codfil": fil, "codigo_produtor": cod,
             "nome_produtor": nome, "papel_cru": papel, "criado_por": por if _UUID.match(por) else None}
    try:
        criadas = _dados(_t(db, TABELA_VINCULOS).insert(linha).execute())
    except Exception as exc:  # noqa: BLE001 — a corrida perdida para outra gravação cai aqui (23505)
        if "23505" in str(getattr(exc, "code", "")) or "duplicate key" in str(exc):
            raise Recusa("este código de produtor já está ligado a outra pessoa — desfaça aquele vínculo antes") \
                from None
        if "23503" in str(getattr(exc, "code", "")) or "foreign key" in str(exc):
            raise Recusa("esta pessoa não é membro ativo da corretora") from None
        raise
    return {"id": (criadas[0].get("id") if criadas else None), "ja_existia": False}


def desvincular(db: Any, company_id: str, vinculo_id: Any) -> int:
    """Desfaz UM vínculo da corretora. Um id de outra corretora apaga zero linhas (o filtro `company_id` vai junto)."""
    cid = _uuid(company_id)
    vid = _uuid(vinculo_id, "vínculo")
    apagadas = _dados(_t(db, TABELA_VINCULOS).delete().eq("id", vid).eq("company_id", cid).execute())
    return len(apagadas)


def gravar_regra(db: Any, company_id: str, sistema: Any, regra: Any, por_user_id: Any = None) -> Regra:
    cid, sis = _uuid(company_id), _sistema(sistema)
    normal = validar_regra(regra, sis)
    por = str(por_user_id or "").strip().lower()
    (_t(db, TABELA_REGRAS).upsert({"company_id": cid, "sistema": sis, "regra": normal,
                                   "atualizado_por": por if _UUID.match(por) else None,
                                   "atualizado_em": _agora()}, on_conflict="company_id,sistema").execute())
    return _regra(normal, ORIGEM_CORRETORA)


def apagar_regra(db: Any, company_id: str, sistema: Any) -> int:
    """Volta ao padrão do sistema (apaga só a linha DESTA corretora)."""
    cid, sis = _uuid(company_id), _sistema(sistema)
    return len(_dados(_t(db, TABELA_REGRAS).delete().eq("company_id", cid).eq("sistema", sis).execute()))


# --------------------------------------------------------------------------------------------------------------------
# A InfoCap DA corretora — pelo caminho canônico, nunca por nome
# --------------------------------------------------------------------------------------------------------------------
async def abrir_fonte(db: Any, company_id: str) -> Any:
    """A `FonteInfocap` da conexão DESTA corretora, por `infocap_analytics_provider._abrir` (o resolvedor do Vault,
    o gate de conta compartilhada e a chave de cache `company_id:connection_id`). ⛔ Nunca `FonteInfocap.para_empresa`
    (credencial por NOME de corretora no ambiente — CLAUDE.md §13.9)."""
    from app.providers.infocap_analytics_provider import InfocapAnalyticsProvider

    cid = _uuid(company_id)
    provedor = InfocapAnalyticsProvider(company_id=cid, db=db)
    fonte, _conexao, _impressao, _db = await provedor._abrir(company_id=cid, db=db)
    return fonte


async def _em_serie(func: Any, *args: Any) -> Any:
    """A fonte é SÍNCRONA (urllib): roda fora do loop, uma chamada de cada vez (📊 10 paralelas → um 500)."""
    return await asyncio.to_thread(func, *args)


async def dono_da_apolice(db: Any, company_id: str, *, codfil: Any, nosnum: Any,
                          fonte: Any = None) -> DonoDaApolice:
    """O dono de UMA apólice e a pessoa da corretora que responde por ele.

    status: 'ok' (um dono, membro achado) · 'sem_membro' (um dono, nenhum membro ativo ligado ao código) ·
    'sem_dono' (nenhum produtor atende à regra) · 'ambiguo' (mais de um) · 'sem_conexao' (InfoCap fora/sem conexão).
    `fonte` injetada = a régua real do gate com o login de cada corretora (e o dublê dos testes)."""
    cid = _uuid(company_id)
    regra = regra_de_dono(db, cid, "infocap")
    if regra is None:
        return DonoDaApolice("sem_dono", motivo="não há regra de dono para este sistema de gestão")
    if fonte is None:
        try:
            fonte = await abrir_fonte(db, cid)
        except Exception as exc:  # noqa: BLE001 — o tipo basta; a mensagem pode carregar dado da conexão
            return DonoDaApolice("sem_conexao", regra_origem=regra.origem,
                                 motivo=f"não consegui abrir a InfoCap da corretora ({type(exc).__name__})")
    try:
        linhas = await _em_serie(fonte.prod_docs_avulso, codfil, nosnum)
    except Exception as exc:  # noqa: BLE001
        return DonoDaApolice("sem_conexao", regra_origem=regra.origem,
                             motivo=f"a InfoCap não respondeu os produtores da apólice ({type(exc).__name__})")
    candidatos = aplicar_regra(linhas, regra)
    if not candidatos:
        motivo = ("a InfoCap não devolveu produtores para esta apólice" if not linhas
                  else "nenhum produtor desta apólice atende à regra do dono")
        return DonoDaApolice("sem_dono", regra_origem=regra.origem, motivo=motivo)
    if len(candidatos) > 1:
        return DonoDaApolice("ambiguo", regra_origem=regra.origem,
                             motivo=f"{len(candidatos)} produtores atendem à regra do dono")
    c = candidatos[0]
    uid = membro_do_produtor(db, cid, "infocap", codfil, c.codigo)
    if uid is None:
        return DonoDaApolice("sem_membro", codigo_produtor=c.codigo, papel_cru=c.papel_cru,
                             regra_origem=regra.origem,
                             motivo="o código do produtor dono não está ligado a um membro ativo da corretora")
    return DonoDaApolice("ok", codigo_produtor=c.codigo, papel_cru=c.papel_cru, user_id=uid,
                         regra_origem=regra.origem, motivo="")


def _e_cancelada(linha: Mapping[str, Any]) -> bool:
    return str(linha.get("cancelado") or "").strip().upper() in ("T", "S", "TRUE", "1")


async def medir_regra(db: Any, company_id: str, *, dias: int = 30, limite: int = 150, fonte: Any = None,
                      regra: Any = None) -> Dict[str, Any]:
    """A RÉGUA: aplica a regra às renovações dos próximos `dias` (um `/prod_docs` por apólice, em SÉRIE).

    Devolve só contagens e códigos de produtor — ⛔ nunca nome de cliente.

    🔴 `com_um_dono` sozinho é carimbo: a regra `ordem == 1` dá exatamente um produtor em TODA apólice (100 %) e
    erra o dono em 62 de 99. Por isso a régua também diz `confere_com_o_padrao` (o dono desta regra é o mesmo do
    padrão do sistema?) e `por_papel_cru` (📊 o dono certo é FECHADOR em 92/99 e 213/217). A mutação do gate injeta
    `regra={"campo": "ordem", "igual": 1, "codigo": "codpro"}` e vê `confere_com_o_padrao` cair (≈ 37/99, 24/217)."""
    cid = _uuid(company_id)
    dias = max(1, min(int(dias or 30), 366))
    limite = max(1, min(int(limite or 150), 1000))
    if regra is None:
        usada = regra_de_dono(db, cid, "infocap")
    elif isinstance(regra, Regra):
        usada = regra
    else:
        usada = _regra(validar_regra(regra, "infocap"), ORIGEM_INJETADA)
    padrao = regra_padrao_do_sistema("infocap")
    hoje = date.today()
    fim = hoje + timedelta(days=dias)
    base: Dict[str, Any] = {"sistema": "infocap", "janela": {"de": hoje.isoformat(), "ate": fim.isoformat(),
                                                             "dias": dias},
                            "regra": usada.como_dict() if usada else None,
                            "regra_origem": usada.origem if usada else None}
    if usada is None:
        return {**base, "status": "sem_regra", "motivo": "não há regra de dono para este sistema de gestão"}
    if fonte is None:
        try:
            fonte = await abrir_fonte(db, cid)
        except Exception as exc:  # noqa: BLE001
            return {**base, "status": "sem_conexao",
                    "motivo": f"não consegui abrir a InfoCap da corretora ({type(exc).__name__})"}
    try:
        renovacoes = await _em_serie(fonte.renovacoes_cruas, hoje, fim)
    except Exception as exc:  # noqa: BLE001
        return {**base, "status": "sem_conexao",
                "motivo": f"a InfoCap não respondeu as renovações ({type(exc).__name__})"}

    vistas: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    for r in renovacoes:
        if str(r.get("tipdoc") or "").strip().upper() != "A" or _e_cancelada(r):
            continue
        chave = (codigo_normalizado(r.get("codfil")) or "1", codigo_normalizado(r.get("nosnum")))
        if chave[1] and chave not in vistas:
            vistas[chave] = r
    apolices = list(vistas)[:limite]

    com_um = sem_dono = ambiguas = falhas = confere = 0
    sem_membro_apolices = 0
    por_papel: Counter = Counter()
    por_posicao: Counter = Counter()
    donos: Counter = Counter()
    papel_do_dono: Dict[str, Optional[str]] = {}
    membro_de: Dict[Tuple[str, str], Optional[str]] = {}
    for codfil, nosnum in apolices:
        try:
            linhas = await _em_serie(fonte.prod_docs_avulso, codfil, nosnum)
        except Exception:  # noqa: BLE001
            falhas += 1
            continue
        cands = aplicar_regra(linhas, usada)
        if not cands:
            sem_dono += 1
            continue
        if len(cands) > 1:
            ambiguas += 1
            continue
        c = cands[0]
        com_um += 1
        por_papel[c.papel_cru or "sem rótulo"] += 1
        por_posicao[c.ordem or "?"] += 1
        donos[c.codigo] += 1
        papel_do_dono.setdefault(c.codigo, c.papel_cru)
        if padrao is not None:
            cp = aplicar_regra(linhas, padrao)
            confere += int(len(cp) == 1 and cp[0].codigo == c.codigo)
        if (codfil, c.codigo) not in membro_de:
            membro_de[(codfil, c.codigo)] = membro_do_produtor(db, cid, "infocap", codfil, c.codigo)
        if membro_de[(codfil, c.codigo)] is None:
            sem_membro_apolices += 1

    sem_membro_codigos = {cod for (_f, cod), uid in membro_de.items() if uid is None}
    return {
        **base, "status": "ok",
        "apolices": len(apolices), "apolices_na_janela": len(vistas), "limite_atingido": len(vistas) > len(apolices),
        "com_um_dono": com_um, "sem_dono": sem_dono, "ambiguas": ambiguas, "falhas": falhas,
        "confere_com_o_padrao": confere if padrao is not None else None,
        "por_papel_cru": dict(por_papel.most_common()),
        "posicao_do_dono": dict(sorted(por_posicao.items())),
        "donos_distintos": len(donos), "donos_sem_membro": len(sem_membro_codigos),
        "apolices_sem_membro": sem_membro_apolices,
        "donos": [{"codigo_produtor": cod, "papel_cru": papel_do_dono.get(cod), "apolices": n,
                   "tem_membro": cod not in sem_membro_codigos} for cod, n in donos.most_common()],
    }


async def sugerir_vinculos(db: Any, company_id: str, fonte: Any = None) -> Dict[str, Any]:
    """Os códigos de produtor da InfoCap × os membros da corretora, com uma SUGESTÃO de pessoa por semelhança de
    nome (sem o papel). ⛔ Nunca grava: quem confirma é a pessoa na tela."""
    cid = _uuid(company_id)
    if fonte is None:
        try:
            fonte = await abrir_fonte(db, cid)
        except Exception as exc:  # noqa: BLE001
            return {"status": "sem_conexao", "motivo": f"não consegui abrir a InfoCap da corretora "
                                                       f"({type(exc).__name__})", "produtores": [], "membros": []}
    try:
        produtores = await _em_serie(fonte.produtores)
    except Exception as exc:  # noqa: BLE001
        return {"status": "sem_conexao", "motivo": f"a InfoCap não respondeu os produtores ({type(exc).__name__})",
                "produtores": [], "membros": []}
    membros = membros_ativos(db, cid)
    vinculos = {(str(v["codfil"]), v["codigo_produtor"]): v for v in listar_vinculos(db, cid, "infocap")}
    saida = []
    for p in produtores:
        cod = codigo_normalizado(p.get("codigo"))
        if not cod:
            continue
        nome = str(p.get("nome") or "").strip()
        limpo = nome_sem_papel(nome)
        v = vinculos.get(("1", cod))
        sugestao = None
        if v is None and membros:
            notas = sorted(((nota_de_semelhanca(limpo, m["nome"]), m) for m in membros),
                           key=lambda x: x[0], reverse=True)
            melhor = notas[0]
            segunda = notas[1][0] if len(notas) > 1 else 0.0
            if melhor[0] >= NOTA_MINIMA_DA_SUGESTAO and melhor[0] - segunda >= FOLGA_SOBRE_A_SEGUNDA:
                sugestao = {"user_id": melhor[1]["user_id"], "nome": melhor[1]["nome"], "nota": melhor[0]}
        saida.append({
            "codfil": 1, "codigo_produtor": cod, "nome_produtor": nome, "nome_sem_papel": limpo,
            "papel_cru": papel_do_nome(nome),
            "vinculo": ({"id": v["id"], "user_id": v["user_id"], "nome_do_membro": v["nome_do_membro"],
                         "membro_ativo": v["membro_ativo"]} if v else None),
            "sugestao": sugestao,
        })

    def _ordem(x: Dict[str, Any]) -> Tuple[int, float, int, str]:
        cod = x["codigo_produtor"]
        return (0 if x["vinculo"] else 1 if x["sugestao"] else 2, -(x["sugestao"] or {}).get("nota", 0.0),
                int(cod) if cod.isdigit() else 10 ** 9, cod)

    return {"status": "ok", "produtores": sorted(saida, key=_ordem), "membros": membros}
