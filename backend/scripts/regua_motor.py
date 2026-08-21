"""A camada de reuso da régua — UM SÓ lugar do repositório importa o motor.

SPEC-083 §5.4 é literal: *"Reimplementar qualquer uma faz a ferramenta medir uma
coisa e o produto fazer outra — o mesmo defeito do helper `_captura`, um nível
acima."* E o CLAUDE.md §5 proíbe motor paralelo.

Por isso este módulo existe. `medir_rota.py` e `gerar_corpus_de_telas.py` importam
DAQUI. Nenhum dos dois abre `corridor_playbooks` por conta própria — se abrissem,
os dois dariam jeitos diferentes para o mesmo `sys.path`, e um dia divergiriam.

⚠️ O import difícil, e a SPEC-083 §5.4 diz qual é: `insurer_dispatch_service` faz
`from app.services.corridor_playbooks import (...)` — import de pacote real. E
`app/services/__init__.py` puxa `IngestionService`, que puxa `fastembed`, que não
está instalado fora do contêiner. O truque de `types.ModuleType` cobre os pacotes
sem executar o `__init__.py` de nenhum deles.

📊 Conferido em 21/08/2026: sem o shim, `from app.services.atlas.templater import
templatize` morre em `ModuleNotFoundError: No module named 'fastembed'`.
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from typing import Any, Dict, Iterator, List, Optional, Tuple

# ── o shim de import (SPEC-083 §5.4) ─────────────────────────────────────────
# `scripts/` mora em `backend/scripts`, então a raiz do pacote `app` é o pai.
RAIZ_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `app.services.atlas` não está na lista da SPEC-083 §5.4 e precisa estar: o
# mascarador (`templatize`) mora lá, e a SPEC-084 §2.5.1.3 manda reusá-lo.
_PACOTES = ("app", "app.services", "app.core", "app.services.atlas")

for _pkg in _PACOTES:
    if _pkg not in sys.modules:
        _mod = types.ModuleType(_pkg)
        _mod.__path__ = [os.path.join(RAIZ_BACKEND, *_pkg.split("."))]
        sys.modules[_pkg] = _mod

if RAIZ_BACKEND not in sys.path:
    sys.path.insert(0, RAIZ_BACKEND)

CP = importlib.import_module("app.services.corridor_playbooks")
IDS = importlib.import_module("app.services.insurer_dispatch_service")
TPL = importlib.import_module("app.services.atlas.templater")


# ── o motor, reexportado com o nome do produto ───────────────────────────────
# 🔴 Nada aqui é implementação. Tudo é ponteiro. Se algum dia uma destas linhas
#    virar um `def`, a régua parou de medir o produto e passou a medir a si mesma.
_norm = CP._norm
match_ura_step = CP.match_ura_step
extract_capture_anchors = CP.extract_capture_anchors
detect_finalize_anchor = CP.detect_finalize_anchor
detect_handoff_trigger = CP.detect_handoff_trigger
canonical_subservice = CP.canonical_subservice
missing_slots_for_subservice = CP.missing_slots_for_subservice
render_reply = CP.render_reply
auto_subservice_menu_value = CP.auto_subservice_menu_value
subservice_supported = CP.subservice_supported
resolve_playbook_ref = CP.resolve_playbook_ref
get_playbook = CP.get_playbook
list_playbooks = CP.list_playbooks

# 📊 `_tela_pede_alguma_coisa(playbook, texto) -> bool`, em
# `insurer_dispatch_service.py:1974`. A SPEC-083 §3.3 exige ESTE discriminador e
# nenhum outro: *"Um segundo discriminador divergiria em silêncio."*
tela_pede_alguma_coisa = IDS._tela_pede_alguma_coisa

# 📊 `client_summary_from_capture(session)` — recebe a SESSÃO, não a captura.
# É o item de 5 pontos do eixo B (SPEC-083 §3.3), e o furo nº 3 da §1.2.
client_summary_from_capture = IDS.client_summary_from_capture

# o mascarador do Atlas — SPEC-084 §2.5.1.3: *"NUNCA um segundo"*
templatize = TPL.templatize
marcas_de_corretora = TPL.marcas_de_corretora

PLAYBOOKS: Dict[str, Dict[str, Any]] = CP._PLAYBOOKS


# ── as rotas ─────────────────────────────────────────────────────────────────
class Rota(tuple):
    """`(seguradora, ramo, servico, playbook_ref)` com nomes legíveis."""

    __slots__ = ()

    def __new__(cls, seguradora: str, ramo: str, servico: str, ref: str):
        return super().__new__(cls, (seguradora, ramo, servico, ref))

    seguradora = property(lambda s: s[0])
    ramo = property(lambda s: s[1])
    servico = property(lambda s: s[2])
    ref = property(lambda s: s[3])

    def __str__(self) -> str:  # noqa: D105
        return f"{self[0]} x {self[1]} x {self[2]}"


def _seguradora_e_ramo(ref: str) -> Tuple[str, str]:
    """`allianz-residencial-whatsapp@v1` -> `('allianz', 'residencial')`.

    ⚠️ Derivado da CHAVE, não de uma tabela nova: a chave é a fonte, e uma tabela
    ao lado dela divergiria no dia em que um playbook fosse renomeado.
    """
    base = ref.split("@", 1)[0]
    partes = base.split("-")
    # <seguradora>-<ramo>-<canal>. Seguradora pode ter hífen? Hoje não tem, e o
    # `assert` abaixo é o guarda que avisa no dia em que tiver.
    assert len(partes) == 3, f"chave de playbook fora do formato esperado: {ref}"
    return partes[0], partes[1]


def rotas() -> List[Rota]:
    """As rotas do produto, derivadas dos playbooks.

    📊 62 em 21/08/2026 — a soma dos `subservices` dos 14 playbooks.
    🔴 NUNCA fixar 62: a SPEC-083 (Bloco D, VERIFY) é explícita — *"o número de
    linhas de dados É CALCULADO, não fixo em 62"*, porque a SPEC-084 §10.4 lista
    8+ serviços que ela vai criar, e um VERIFY fixo nasceria errado.
    """
    fora: List[Rota] = []
    for ref, pb in sorted(PLAYBOOKS.items()):
        seg, ramo = _seguradora_e_ramo(ref)
        for servico in sorted((pb.get("subservices") or {})):
            fora.append(Rota(seg, ramo, servico, ref))
    return fora


def rota_de(seguradora: str, ramo: str, servico: str) -> Optional[Rota]:
    """A rota pedida, ou `None` se ela não existe no produto."""
    for r in rotas():
        if (r.seguradora, r.ramo, r.servico) == (seguradora, ramo, servico):
            return r
    return None


def seguradoras() -> List[str]:
    """As seguradoras que têm playbook. 📊 10 em 21/08/2026."""
    return sorted({r.seguradora for r in rotas()})


# ── o banco ──────────────────────────────────────────────────────────────────
def tem_banco() -> bool:
    """Há credencial para ler `observed_events`?

    🔴 Presença/ausência, NUNCA o valor (CLAUDE.md §13.3).
    """
    try:
        from app.core.config import settings

        return bool(getattr(settings, "SUPABASE_URL", None)
                    and getattr(settings, "SUPABASE_KEY", None))
    except Exception:  # noqa: BLE001
        return False


def supabase():
    """O cliente do produto. Não abrimos conexão própria."""
    from app.core.database import get_supabase_client

    return get_supabase_client().client


def controle_do_mascarador() -> int:
    """🔴 O CONTROLE que dá direito a qualquer medição sobre o mascarador.

    SPEC-084 §2.5.1.3, literal:

        CONTROLE OBRIGATÓRIO de qualquer medição sobre o mascarador:
            assert len(marcas_de_corretora(recarregar=True)) > 0
        Se falhar, a medição é INVÁLIDA e não autoriza ampliação nenhuma.

    📊 Foi esta linha que transformou "o mascarador tem três buracos" em "tem um":
    a medição anterior rodou sem banco, `marcas_de_corretora()` devolveu zero, e a
    quarta linha da saída — que era o controle das três primeiras — não foi lida
    como tal.

    Devolve o número de marcas. Levanta `AssertionError` se for zero.
    """
    marcas = marcas_de_corretora(recarregar=True)
    assert len(marcas) > 0, (
        "CONTROLE VERMELHO: marcas_de_corretora() devolveu 0. A medição rodou SEM "
        "BANCO e é INVÁLIDA. Nenhuma conclusão sobre mascaramento vale a partir "
        "daqui. (SPEC-084 §2.5.1.3)"
    )
    return len(marcas)


def eventos_observados(
    *,
    seguradora: Optional[str] = None,
    direction: Optional[str] = None,
    pagina: int = 1000,
) -> Iterator[Dict[str, Any]]:
    """Percorre `observed_events` em páginas, ordenado por `wa_timestamp`.

    ⚠️ Paginação obrigatória: o PostgREST corta em 1000 por padrão, e 📊 o acervo
    tem 28.096 eventos. Uma leitura sem paginação devolveria 3,6% dele e ninguém
    veria — a mesma classe do `limit 22` que fez a SPEC-084 declarar
    `"zurich": []` por corte de query (§2.5.1).
    """
    cli = supabase()
    inicio = 0
    while True:
        # 🔴 `msg_type` e `interactive` entram por medição do JUIZ 2, não por
        #    completude: 📊 **934 respostas de botão têm `text` VAZIO** — yelum
        #    370, hdi 254, porto 165, bradesco 62, azul 54 — e `interactive`
        #    guardou só as CHAVES (`selectedButtonID` entre elas) sem o valor.
        #    **A escolha do segurado não está no banco.**
        #
        #    É a maior causa isolada de perda do nível 1 da cascata. E 📊 1.151
        #    outras TÊM `interactive->>'title'` legível — sem estas colunas,
        #    nenhum consumidor da régua consegue sequer VER que a resposta existe.
        q = (cli.table("observed_events")
             .select("session_id,insurer_key,company_id,direction,text,"
                     "wa_timestamp,msg_type,interactive")
             .order("wa_timestamp")
             .range(inicio, inicio + pagina - 1))
        if seguradora is not None:
            q = q.eq("insurer_key", seguradora)
        if direction is not None:
            q = q.eq("direction", direction)
        linhas = q.execute().data or []
        if not linhas:
            return
        for linha in linhas:
            yield linha
        if len(linhas) < pagina:
            return
        inicio += pagina


__all__ = [
    "CP", "IDS", "TPL", "RAIZ_BACKEND",
    "_norm", "match_ura_step", "extract_capture_anchors", "detect_finalize_anchor",
    "detect_handoff_trigger", "canonical_subservice", "missing_slots_for_subservice",
    "render_reply", "auto_subservice_menu_value", "subservice_supported",
    "resolve_playbook_ref", "get_playbook", "list_playbooks",
    "tela_pede_alguma_coisa", "client_summary_from_capture",
    "templatize", "marcas_de_corretora", "PLAYBOOKS",
    "Rota", "rotas", "rota_de", "seguradoras",
    "tem_banco", "supabase", "controle_do_mascarador", "eventos_observados",
]
