"""A CONFERÊNCIA DAS 05:30 — "nenhuma renovação esquecida". SPEC-131-A (F1), laudo I1 §3.

🔴 O ELO da SPEC: "nada esquecido PORQUE a conferência relê a InfoCap". Por isso este módulo é um caminho de código
SEPARADO do que montou a lista: ele NÃO importa `madrugada` (o montador) — um guarda por AST no teste confere — e lê
`/renovacoes` DE NOVO, nunca a lista congelada. A lista de `renovacoes` só entra aqui como o que é CONFERIDO.

    InfoCap /renovacoes [dia, dia + antecedência + margem]  →  ESPERADAS (só as que vencem até dia + antecedência)
    × itens da tabela                                      →  faltou?  cria o item + evento `esquecida_pela_preparacao`
                                                              e o dia fica VERMELHO
    InfoCap fora                                           →  o dia é `sem_conexao` (contagens NULAS, nunca "0") +
                                                              alerta à corretora

completude = (calculadas + pendentes COM motivo) ÷ esperadas · e à parte calculadas ÷ cotáveis. `calculando` às 05:30
não conta como feito (nunca contou: só `calculada`/`pendente` entram no numerador) — e o que está em voo SEM batida do
motor há mais de 15 min vai para `detalhes.calculando_sem_batida`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional

from app.services.multicalculo import renovacao as R

logger = logging.getLogger(__name__)

POR = "conferencia"
MOTIVO_ESQUECIDA = "esquecida_pela_preparacao"
SEM_BATIDA = timedelta(minutes=15)


async def _abrir_fonte(db: Any, company_id: str) -> Any:
    """A InfoCap DESTA corretora pelo caminho canônico (`dono.abrir_fonte`, a MESMA borda do produto)."""
    from app.services.sistema_de_gestao import dono as DONO

    return await DONO.abrir_fonte(db, company_id)


def _config(db: Any, company_id: str) -> Dict[str, Any]:
    from app.services.multicalculo import config as C

    return C.carregar(company_id, db=getattr(db, "client", db), servico="renovacao")


def _pct(parte: int, todo: int) -> float:
    if todo <= 0:
        return 100.0
    return round(100.0 * parte / todo, 2)


def _ts(valor: Any) -> Optional[datetime]:
    if not valor:
        return None
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _sem_batida(db: Any, company_id: str, item: Mapping[str, Any], agora: datetime) -> bool:
    """O item em voo cujo pedido não tem cálculo com batida do motor nos últimos 15 min."""
    if not item.get("pedido_id"):
        return True
    cli = getattr(db, "client", db)
    try:
        calcs = (cli.table("multicalculo_calculos").select("status, batida_em, solicitante_company_id")
                 .eq("pedido_id", str(item["pedido_id"])).eq("solicitante_company_id", company_id).execute().data
                 or [])
    except Exception:  # noqa: BLE001
        return True
    for c in calcs:
        if str(c.get("solicitante_company_id")) != str(company_id):
            continue
        batida = _ts(c.get("batida_em"))
        if batida is not None and agora - batida <= SEM_BATIDA:
            return False
    return True


async def conferir_dia(db: Any, company_id: str, dia: Any, *, work_run_id: Optional[str] = None,
                       canario: bool = False) -> Dict[str, Any]:
    """`canario=True` (só o script do canário): o item esquecido nasce `canario` e a medida do dia diz que é canário."""
    cid = R._uuid(company_id)
    d = R.data_de(dia)
    if d is None:
        raise ValueError("dia precisa ser AAAA-MM-DD")
    repo = R.RepositorioDeRenovacoes(db)
    params = R.parametros(_config(db, cid))
    antecedencia = int(params["antecedencia_dias"])
    ate = d + timedelta(days=antecedencia)

    # 1 · a InfoCap DE NOVO (nunca a lista congelada)
    try:
        fonte = await _abrir_fonte(db, cid)
        crus = await asyncio.to_thread(fonte.renovacoes_cruas, d,
                                       d + timedelta(days=antecedencia + int(params["margem_dias"])))
    except Exception as exc:  # noqa: BLE001 — o tipo basta
        logger.warning("[RENOV] conferência sem InfoCap (%s)", type(exc).__name__)
        repo.gravar_dia(cid, d.isoformat(), {
            "estado": "sem_conexao", "esperadas": None, "calculadas": None, "pendentes": None, "falharam": None,
            "faltaram": None, "completude_pct": None, "cotaveis": None, "calculadas_de_cotaveis_pct": None,
            "detalhes": {"erro": type(exc).__name__}})
        R.registrar_aviso(db, cid, dia=d.isoformat(), assunto="conferencia", user_id=None, severidade="high",
                          texto=("A conferência das renovações não conseguiu ler a InfoCap: não dá para garantir "
                                 "que nenhuma ficou esquecida hoje. Confira a conexão da InfoCap."),
                          valores={"sem_conexao": 1}, work_run_id=work_run_id,
                          fuso=R.fuso_da_corretora(db, cid), janela=params["janela"])
        return {"estado": "sem_conexao", "esperadas": None, "faltaram": None, "completude_pct": None}

    # 2 · as ESPERADAS do dia: vencem até dia + antecedência (as da margem ainda não são de hoje)
    esperadas: Dict[tuple, Dict[str, Any]] = {}
    for cru in crus or []:
        try:
            campos = R.linha_da_infocap(cru)
        except Exception:  # noqa: BLE001 — sem a chave do HMAC: o item é conferido só mascarado
            limpo = {k: v for k, v in dict(cru).items() if k not in ("cic", "cpf_cnpj")}
            campos = R.linha_da_infocap(limpo)
        if campos is None:
            continue
        fim = R.data_de(campos["fimvig"])
        if fim is None or fim < d or fim > ate:
            continue
        esperadas.setdefault(R.chave_do_item(campos), campos)

    # 3 · × os itens (a tabela é o que se CONFERE)
    itens = {R.chave_do_item(x): x for x in repo.listar(cid) if x.get("estado") != "substituida"}
    faltaram = 0
    for chave, campos in esperadas.items():
        if chave in itens:
            continue
        # (não criada = existia só como `substituida`: para o dia, ela faltou do mesmo jeito)
        linha, _criada = repo.upsert_da_lista(cid, campos, por=POR, motivo_do_evento=MOTIVO_ESQUECIDA, canario=canario)
        itens[chave] = linha
        faltaram += 1

    calculadas = pendentes = falharam = nao_cotaveis = em_voo = 0
    sem_batida = 0
    agora = datetime.now(timezone.utc)
    motivos: Dict[str, int] = {}
    for chave in esperadas:
        item = itens[chave]
        estado = str(item.get("estado") or "")
        if estado in R.ESTADOS_CALCULADOS:
            calculadas += 1
        elif estado == "pendente" and R.motivo_valido(item.get("motivo")):
            pendentes += 1
            motivos[str(item["motivo"])] = motivos.get(str(item["motivo"]), 0) + 1
            if item.get("motivo") in R.MOTIVOS_NAO_COTAVEIS:
                nao_cotaveis += 1
        elif estado == "falhou":
            falharam += 1
        elif estado in R.ESTADOS_EM_VOO:
            em_voo += 1
            sem_batida += int(_sem_batida(db, cid, item, agora))

    total = len(esperadas)
    cotaveis = total - nao_cotaveis
    completude = _pct(calculadas + pendentes, total)
    estado_do_dia = "vermelho" if faltaram else ("completo" if completude >= 100.0 else "incompleto")
    medida = {
        "estado": estado_do_dia, "esperadas": total, "calculadas": calculadas, "pendentes": pendentes,
        "falharam": falharam, "faltaram": faltaram, "completude_pct": completude, "cotaveis": cotaveis,
        "calculadas_de_cotaveis_pct": _pct(calculadas, cotaveis),
        "detalhes": {"em_voo": em_voo, "calculando_sem_batida": sem_batida, "motivos": motivos,
                     "antecedencia_dias": antecedencia, **({"canario": True} if canario else {})},
    }
    repo.gravar_dia(cid, d.isoformat(), medida)
    if faltaram:
        R.registrar_aviso(db, cid, dia=d.isoformat(), assunto="conferencia", user_id=None, severidade="high",
                          texto=(f"🔴 A conferência achou {faltaram} renovação(ões) que a lista do dia esqueceu. "
                                 "Elas entraram na lista agora e vão para o cálculo da próxima madrugada."),
                          valores={"faltaram": faltaram, "esperadas": total}, work_run_id=work_run_id,
                          fuso=R.fuso_da_corretora(db, cid), janela=params["janela"])
    return {"estado": estado_do_dia, "esperadas": total, "faltaram": faltaram, "completude_pct": completude}
