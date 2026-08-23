# -*- coding: utf-8 -*-
r"""🔴 As rotas AAA acionam pelo caminho REAL da ferramenta?

A régua da SPEC-084.1 mede o CORREDOR: dada uma tela, o produto responde certo?
📊 Ela deu 19 rotas AAA, com 100% das telas respondidas e 100% de determinismo.

⚠️ **E nenhuma delas acionava.** O bloqueio não está no corredor — está ANTES
dele, no contrato da ferramenta, que é onde a régua não olha.

```
com TUDO que a ferramenta consegue carregar   →  missing_data    🔴
com os slots que ela NÃO carrega, em memória  →  ready_to_send   ✅
```

🔴 **O caminho REAL é o que o LLM consegue percorrer.** Só os campos que
`InsurerDispatchInput` DECLARA podem chegar a `build_dry_run_plan`. Um slot que
o portão exige e o schema não anuncia **não tem como chegar** — o atendente não
tem onde escrever a resposta, por mais que a pergunta esteja em
`_COMO_PERGUNTAR`.

⚠️ E não vale confiar na saída de emergência: 📊 `nodes.py` chama
`tool._arun(**args)` cru, sem Pydantic, então funcionaria se o modelo inventasse
um parâmetro que o schema não anuncia. **Apostar um guincho real nisso não é
engenharia** — é contar com o modelo adivinhar o nome de um campo que ninguém
lhe mostrou.

## A linha de controle, e ela é o que dá direito à conclusão

Duas, em cada rodada:

```
CONTROLE 1  a mesma rota, com os slots faltantes injetados EM MEMÓRIA
            → tem de dar ready_to_send. Prova que o corredor está certo e o
              bloqueio é do CONTRATO.
CONTROLE 2  uma rota à qual falta um slot LEGÍTIMO (o CPF do titular)
            → tem de CONTINUAR bloqueada. Sem isto, "19 de 19 passam" não
              distingue portão consertado de portão desligado.
```

Uso:

    cd backend
    python scripts/acionamento_pelo_contrato.py            # as AAA
    python scripts/acionamento_pelo_contrato.py --todas    # as 73
    python scripts/acionamento_pelo_contrato.py --json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from typing import Any, Dict, List

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, RAIZ)

import regua_motor as M            # noqa: E402
import replay as RP                # noqa: E402
import rubrica as RB               # noqa: E402


def _carregar(dotted: str, rel: str):
    """Importa um módulo de `app/` SEM passar pelo `__init__` do pacote.

    ⚠️ `app.agents.__init__` importa `langgraph` e `app.services.__init__`
    importa `fastembed` — dependências de runtime que não estão no ambiente de
    medição. Ler o arquivo direto é o que os guardas deste repo já fazem.
    """
    caminho = os.path.join(RAIZ, rel)
    spec = importlib.util.spec_from_file_location(dotted, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


TOOL = _carregar("app.agents.tools.insurer_dispatch_tool",
                 "app/agents/tools/insurer_dispatch_tool.py")
IDS = _carregar("app.services.insurer_dispatch_service",
                "app/services/insurer_dispatch_service.py")

CAMPOS_DO_SCHEMA = set(TOOL.InsurerDispatchInput.model_fields)

# 💭 O caso mais completo que um atendente consegue montar: TODO campo que o
#    schema declara, com valor plausível. Se ainda assim faltar alguma coisa,
#    o que falta é CONTRATO — não é dado do cliente.
#
# 🔴 Os valores são sintéticos de propósito e a forma anuncia isso (`AAA1111`,
#    `11122233344`). Nada aqui é dado de pessoa.
CASO_CHEIO: Dict[str, Any] = {
    "titular_cpf": "11122233344",
    "titular_nascimento": "01/01/1980",
    "telefone_contato": "47900000000",
    "problema_descricao": "o aparelho parou de funcionar",
    "endereco_numero": "100",
    "periodo_preferido": "manha",
    "risco_confirmado_sem_fumaca": "sim",
    "aparelho_marca": "Electrolux",
    "aparelho_modelo": "Turbo 15kg",
    "aparelho_marca_modelo": "Electrolux Turbo 15kg",
    "aparelho_idade": "3 anos",
    "veiculo_placa": "AAA1111",
    "local_atual": "Rua das Flores, 100 - Centro",
    "local_destino": "oficina referenciada",
    "pessoa_no_local": "Fulano",
    "quando": "agora",
    "ponto_referencia": "ao lado da praca",
    "dados_confirmados": True,
}

# ⚠️ Valor de preenchimento para campo novo que o CASO_CHEIO ainda não nomeia.
#    A regra é o SUFIXO, como no resto do motor: `_opcao` é escolha de menu.
_PREENCHIMENTO = {
    "local_seguro": "sim, estou num lugar seguro",
    "vazamento_local": "embaixo da pia da cozinha",
    "agua_escorrendo": "sim",
    "risco_confirmado_registro_fechado": "sim",
    "estepe_situacao": "tenho estepe cheio",
    "ferramentas_no_veiculo": "sim",
    "tipo_imovel": "casa",
    "ar_condicionado_tipo": "split",
    "ar_condicionado_btus": "9000",
    "email_segurado": "segurado@exemplo.com.br",
    "veiculo_em_garagem": "nao",
    "veiculo_nivel_rua": "sim",
    "local_situacao": "na rua, em frente ao numero 100",
    "transporte_destino": "para casa",
    "taxi_passageiros": "2",
}


def caso_do_schema() -> Dict[str, Any]:
    """Só o que a ferramenta DECLARA — e TUDO que ela declara.

    🔴 A primeira redação preenchia apenas os campos que `CASO_CHEIO` e
    `_PREENCHIMENTO` nomeavam, e deixava em branco qualquer campo novo. 📊 O
    efeito, medido: depois do C1 a ferramenta declarava `encanador_tipo_opcao`
    e o instrumento não o preenchia — a rota aparecia bloqueada por um slot que
    o contrato JÁ tinha. O instrumento acusava o produto de um defeito que era
    dele mesmo.

    ⚠️ Um medidor que não usa tudo o que o contrato oferece mede o próprio
    esquecimento. Aqui **todo** campo declarado é preenchido; quem não tem
    redação específica recebe um valor pela regra do sufixo.
    """
    fora = {k: v for k, v in CASO_CHEIO.items() if k in CAMPOS_DO_SCHEMA}
    for campo in CAMPOS_DO_SCHEMA:
        if campo in fora or campo in ("session_id", "subservice", "insurer_key",
                                      "line_kind"):
            continue
        fora[campo] = _PREENCHIMENTO.get(campo) or (
            "sim" if campo.endswith("_opcao") else "informado pelo cliente")
    return fora


def medir(rota, *, slots_extra: Dict[str, Any] = None) -> Dict[str, Any]:
    slots = caso_do_schema()
    slots.update(slots_extra or {})
    plano = IDS.build_dry_run_plan(rota.ref, rota.servico, dict(slots))
    falta = list(plano.get("missing_slots") or [])
    return {
        "rota": str(rota),
        "ok": bool(plano.get("ok")) and not falta,
        "erro": plano.get("error"),
        "falta": falta,
        "fora_do_schema": [s for s in falta if s not in CAMPOS_DO_SCHEMA],
    }


def controle_em_memoria(rota, falta: List[str]) -> bool:
    """CONTROLE 1: com os slots faltantes injetados, a rota fecha?"""
    extra = {s: "sim" for s in falta}
    return medir(rota, slots_extra=extra)["ok"]


def controle_slot_legitimo(rota) -> Dict[str, Any]:
    """CONTROLE 2: tirando o CPF do titular, a rota TEM de continuar bloqueada.

    🔴 Sem esta metade, "19 de 19 passam" não distingue portão consertado de
    portão desligado. É a diferença entre consertar e afrouxar.
    """
    slots = caso_do_schema()
    slots.pop("titular_cpf", None)
    plano = IDS.build_dry_run_plan(rota.ref, rota.servico, dict(slots))
    falta = list(plano.get("missing_slots") or [])
    return {"bloqueada": bool(falta), "falta": falta}


def controle_campo_novo(alvo, campo: str) -> Dict[str, Any]:
    """CONTROLE 3: o campo que o C1 acrescentou é MESMO cobrado?

    🔴 "19 de 19 passam" tem duas explicações, e elas são opostas: ou o
    contrato passou a carregar o dado, ou o portão parou de pedi-lo. O
    CONTROLE 2 (tirar o CPF) só prova que o portão continua vivo para um campo
    ANTIGO. Este prova para os campos NOVOS, um a um: tirando `local_seguro`,
    as 13 rotas de auto **têm de voltar a bloquear**.

    ⚠️ Se um campo novo sair daqui sem derrubar rota nenhuma, ele é enfeite:
    foi acrescentado ao contrato sem que ninguém o exija.
    """
    derrubadas = []
    for rota in alvo:
        slots = caso_do_schema()
        slots.pop(campo, None)
        plano = IDS.build_dry_run_plan(rota.ref, rota.servico, dict(slots))
        if campo in (plano.get("missing_slots") or []):
            derrubadas.append(str(rota))
    return {"campo": campo, "derrubadas": derrubadas}


def rotas_alvo(todas: bool):
    tem = M.tem_banco()
    M.vocabulario_do_espelho(recarregar=True)
    fora = []
    for rota in M.rotas():
        if not RP.replay(rota).telas:
            continue
        if todas:
            fora.append(rota)
            continue
        nota = RB.medir(rota, tem_espelho=tem, mutacoes_ok=(12, 12))
        if nota.pontos / nota.denominador >= .95:
            fora.append(rota)
    return fora


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--todas", action="store_true",
                    help="mede as rotas com corpus, não só as AAA")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    alvo = rotas_alvo(a.todas)
    linhas = [medir(r) for r in alvo]
    bloqueadas = [x for x in linhas if not x["ok"]]

    if a.json:
        print(json.dumps({"rotas": linhas,
                          "acionam": len(linhas) - len(bloqueadas),
                          "de": len(linhas)}, ensure_ascii=False, indent=2))
        return 0

    print("=" * 78)
    print("AS ROTAS ACIONAM PELO CAMINHO REAL DA FERRAMENTA?")
    print("=" * 78)
    print(f"  campos declarados em InsurerDispatchInput: {len(CAMPOS_DO_SCHEMA)}")
    print()
    fora_schema: Dict[str, List[str]] = {}
    for r, x in zip(alvo, linhas):
        if x["ok"]:
            print(f"  OK  {x['rota']:42s} ready_to_send")
            continue
        for s in x["fora_do_schema"]:
            fora_schema.setdefault(s, []).append(x["rota"])
        ctrl = controle_em_memoria(r, x["falta"])
        print(f"  \U0001F534 {x['rota']:42s} {x['erro']}")
        print(f"        falta: {', '.join(x['falta']) or '(nenhum slot)'}")
        print(f"        CONTROLE 1 (em memória): "
              + ("ready_to_send → o corredor está CERTO, o contrato é que bloqueia"
                 if ctrl else "AINDA bloqueada → não é só contrato"))

    print()
    print("=" * 78)
    print(f"  ACIONAM: {len(linhas) - len(bloqueadas)} de {len(linhas)}")
    if fora_schema:
        print()
        print("  SLOTS QUE O PORTÃO EXIGE E O SCHEMA NÃO DECLARA:")
        for s, rr in sorted(fora_schema.items(), key=lambda kv: -len(kv[1])):
            print(f"    {s:42s} x{len(rr)}  ({rr[0]})")

    # ── CONTROLE 2 ───────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("  \U0001F534 CONTROLE 2 — o portão CONTINUA cobrando o que é legítimo")
    print("=" * 78)
    print("     tira-se o CPF do titular; cada rota TEM de voltar a bloquear")
    passou = falhou = 0
    for r in alvo:
        c = controle_slot_legitimo(r)
        if c["bloqueada"]:
            passou += 1
        else:
            falhou += 1
            print(f"    \U0001F534 {str(r):42s} passou SEM CPF — o portão afrouxou")
    print(f"    {passou} de {len(alvo)} continuam bloqueadas sem o CPF")

    # ── CONTROLE 3 ───────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("  \U0001F534 CONTROLE 3 — cada campo NOVO é mesmo cobrado?")
    print("=" * 78)
    print("     tira-se UM campo por vez; ele tem de derrubar as rotas que o exigem")
    enfeites = []
    for campo in sorted(_PREENCHIMENTO):
        if campo not in CAMPOS_DO_SCHEMA:
            continue
        c = controle_campo_novo(alvo, campo)
        if c["derrubadas"]:
            print(f"    ok  {campo:38s} derruba {len(c['derrubadas'])} rota(s)")
        else:
            enfeites.append(campo)
    for campo in enfeites:
        print(f"    ⚠️  {campo:38s} não derruba rota AAA nenhuma")

    if falhou:
        print("    \U0001F534 UM PORTÃO QUE DEIXA PASSAR SEM CPF NÃO É UM PORTÃO CONSERTADO")
    return 0 if not falhou else 1


if __name__ == "__main__":
    raise SystemExit(main())
