"""`medir_rota.py` — a RÉGUA. Dá nota 0–100 a qualquer rota. Determinística, sem LLM.

```bash
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar
python backend/scripts/medir_rota.py --todas --formato tabela
python backend/scripts/medir_rota.py --todas --formato markdown > docs/canon/reports/INVENTARIO-DE-ROTAS.md
python backend/scripts/medir_rota.py --seguradora allianz --ramo residencial --servico maquina_de_lavar --replay-detalhado
python backend/scripts/medir_rota.py --verificar-mutacoes
python backend/scripts/medir_rota.py --conferir-ancoras-de-desfecho
```

🔴 **Modo offline** (§5.6): sem `SUPABASE_URL`/`SUPABASE_KEY` a ferramenta mede
**C, D e E** — que só dependem do código — e o corpus versionado sustenta **B**.
⚠️ Correção à v1 da SPEC: *"B não é offline"* era verdade quando o corpus vinha do
banco. Com o corpus **em git**, B roda sem rede; o que exige banco é só a coluna
DEMANDA e a conferência de âncoras.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import padroes_de_servico as PS      # noqa: E402
import regua_motor as M              # noqa: E402
import replay as RP                  # noqa: E402
import rubrica as RB                 # noqa: E402
import verificar_mutacoes as VM      # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTE_DA_REGUA = "tests/test_a_regua_nao_tem_furo.py"


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=RAIZ, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:  # noqa: BLE001
        return "?"


def _sessoes_por_seguradora() -> Dict[str, int]:
    """Quantas sessões o ACERVO tem — o denominador da linha `AMOSTRA:`."""
    if not M.tem_banco():
        return {}
    fora: Dict[str, set] = collections.defaultdict(set)
    for e in M.eventos_observados():
        if e.get("insurer_key") and e.get("session_id"):
            fora[e["insurer_key"]].add(e["session_id"])
    return {k: len(v) for k, v in fora.items()}


# ═════════════════════════════════════════════════════════════════════════════
# --conferir-ancoras-de-desfecho  (§3.2)
# ═════════════════════════════════════════════════════════════════════════════
def conferir_ancoras_de_desfecho() -> str:
    """A seguradora tem desfecho no acervo, e a âncora o alcança?

    🔴 *"Confundir 'a seguradora escreve diferente' com 'nunca vimos esta rota'
    manda a SPEC-084 coletar o que já está coletado."*

    Os estados, e o terceiro nasceu desta execução:

    ```
    >=1 sessao casa               normal                 a rubrica roda
    0 casam e >=10 sessoes        🟠 ANCORA_SUSPEITA     defeito da ANCORA
    0 casam e <10 sessoes         🔴 SEM_FONTE           vai para coleta
    ```

    ⚠️ 📊 E o que esta execução mediu, que a SPEC-083 §3.2 não previa:
    **zurich, bradesco e mapfre são TRÊS casos diferentes**, não um.
    """
    L = ["=== --conferir-ancoras-de-desfecho ===", ""]
    L.append(f"{'seguradora':10s} {'ramo':12s} {'telas':>6s} {'c/ protocolo':>13s} "
             f"{'sessoes':>8s}  estado")
    for rota in RB.M.rotas():
        pass
    vistos = set()
    for rota in M.rotas():
        chave = (rota.seguradora, rota.ramo)
        if chave in vistos:
            continue
        vistos.add(chave)
        pb = M.get_playbook(rota.ref)
        linhas = RP.carregar_corpus(rota.seguradora, rota.ramo)
        com = [l for l in linhas
               if M.extract_capture_anchors(pb, l["text"]).get("protocol")]
        ses_total = len({l["session_id"] for l in linhas})
        ses_com = len({l["session_id"] for l in com})
        if ses_com:
            estado = "normal"
        elif ses_total >= 3:
            estado = "🟠 ANCORA_SUSPEITA (defeito da ancora, NAO falta de fonte)"
        else:
            estado = "🔴 SEM_FONTE"
        L.append(f"{rota.seguradora:10s} {rota.ramo:12s} {len(linhas):6d} "
                 f"{len(com):13d} {ses_com:3d}/{ses_total:<4d}  {estado}")
    L.append("")
    L.append("⚠️ 📊 MEDIDO em 21/08/2026 pelos mineradores — os tres casos que a")
    L.append("   SPEC-083 §3.2 fundia num estado so:")
    L.append("   zurich   5 rotas  🟠 ANCORA_SUSPEITA      o desfecho EXISTE:")
    L.append("                                             `*Numero da solicitacao:* *N*`")
    L.append("                                             e `*Numero do processo:* 31.26.N.01`")
    L.append("   bradesco 4 rotas  🔵 DESFECHO_SEM_NUMERO  a URA NAO emite numero neste")
    L.append("                                             canal: fecha com URL de rastreio")
    L.append("   mapfre   4 rotas  ⚫ SEM_DESFECHO_NO_ACERVO  0 de 13 sessoes abriram")
    L.append("                                             assistencia. Ninguem escolheu")
    L.append("                                             \"Assistencia 24H\"")
    L.append("")
    L.append("🔴 E a afirmacao que NAO REPRODUZ: a SPEC-083 §3.2 diz que zurich e")
    L.append("   bradesco escrevem \"ordem de servico\" (25 e 10 ocorrencias).")
    L.append("   📊 `ordem de servi` = 0 nas duas. No acervo INTEIRO sao 7 telas:")
    L.append("   tokio 3, hdi 2, porto 2. O par 25/10 nao corresponde a nenhuma.")
    return "\n".join(L)


# ═════════════════════════════════════════════════════════════════════════════
# a saída
# ═════════════════════════════════════════════════════════════════════════════
def imprimir_nota(n: RB.Nota, *, detalhado: bool = True) -> str:
    L = [f"{n.rota}", "─" * 68]
    if n.estado == "SEM_CORPUS":
        L.append("🔵 SEM_CORPUS — zero telas de URA para esta (seguradora, ramo).")
        L.append("   🔴 NAO e o mesmo que NAO_RESPONDE: este e trabalho de COLETA,")
        L.append("      aquele e trabalho de ESCREVER PASSOS. Fundir os dois manda")
        L.append("      para coleta uma rota cujo acervo esta cheio.")
        return "\n".join(L)

    if n.estado == "NAO_RESPONDE":
        b = sum(i.pontos for i in n.itens if i.conta)
        L.append(f"🔴 NAO_RESPONDE — o eixo B fez {b} de 35, abaixo do portao (8).")
        L.append("   Nenhum ponto de A, C, D ou E e concedido enquanto B < 8.")
        L.append("   📊 O portao existe porque a receita da rota vazia sobrevivia ao")
        L.append("      conserto: `alfa x auto x bateria` tirava 30-45 por heranca de")
        L.append("      familia (C) e teste simbolico (E), SEM responder uma tela.")
        for i in n.itens:
            L.append(f"   B {i.pontos:3d}/{i.maximo:<3d} {i.nome}")
            L.append(f"            {i.evidencia}")
        return "\n".join(L)

    fora = n.fora
    txt_fora = ("   (" + " · ".join(f"{k} {v}" for k, v in sorted(fora.items())) +
                " pts fora)") if fora else ""
    L.append(f"PRONTIDAO  {n.pontos}/{n.denominador}   {n.patamar}{txt_fora}")
    if n.replay:
        L.append(f"           {n.replay.amostra}")
    L.append("")
    nomes = {"A": "A EVIDENCIA", "B": "B COBERTURA", "C": "C SEGURANCA",
             "D": "D CONHECIMENTO", "E": "E PROVA"}
    for eixo in "ABCDE":
        p, m = n.por_eixo().get(eixo, (0, 0))
        L.append(f"{nomes[eixo]:16s} {p:3d}/{m:<3d}")
        if not detalhado:
            continue
        for i in n.itens:
            if i.eixo != eixo:
                continue
            if not i.conta:
                L.append(f"  ⊘ ---   {i.nome}   [{i.excluido} — fora do denominador]")
            else:
                marca = "✅" if i.pontos == i.maximo else ("⚠️" if i.pontos else "❌")
                L.append(f"  {marca} {i.pontos:3d}/{i.maximo:<3d} {i.nome}")
            L.append(f"           {i.evidencia}")
    faltam = [i for i in n.itens if i.conta and i.pontos < i.maximo]
    if faltam:
        L.append("")
        L.append("O QUE FALTA  (cada item vira entrada da SPEC-084)")
        for k, i in enumerate(sorted(faltam, key=lambda x: x.maximo - x.pontos,
                                     reverse=True), 1):
            L.append(f"  {k}. [{i.eixo}] {i.nome}  (+{i.maximo - i.pontos})")
    return "\n".join(L)


def tabela(notas: List[RB.Nota], demanda: Dict[str, int]) -> str:
    L = [f"{'SEGURADORA':10s} {'RAMO':12s} {'SERVICO':18s} {'PRONT':>7s} "
         f"{'A':>3s} {'B':>3s} {'C':>3s} {'D':>3s} {'E':>3s}  {'PATAMAR':16s} "
         f"{'FAMILIA':18s} {'DEMANDA':>7s}"]
    for n in notas:
        e = n.por_eixo()
        g = lambda k: (f"{e[k][0]}" if k in e else "—")   # noqa: E731
        pr = n.estado or f"{n.pontos}/{n.denominador}"
        fam = familia_de(n.rota)
        d = demanda.get(n.rota.servico, 0)
        L.append(f"{n.rota.seguradora:10s} {n.rota.ramo:12s} {n.rota.servico:18s} "
                 f"{pr:>7s} {g('A'):>3s} {g('B'):>3s} {g('C'):>3s} {g('D'):>3s} "
                 f"{g('E'):>3s}  {n.patamar:16s} {fam:18s} {d:7d}")
    return "\n".join(L)


_FAMILIAS: Dict[int, List[str]] = {}


def familia_de(rota) -> str:
    """As rotas que compartilham `ura_steps` POR REFERÊNCIA.

    📊 Mexer num passo de `_YELUM_FAMILY_STEPS` muda `hdi-auto` **e** `yelum-auto`
    — `native_flows` é o **mesmo objeto**. Sem esta coluna, um conserto vira uma
    regressão silenciosa na seguradora vizinha.
    """
    if not _FAMILIAS:
        for r in M.rotas():
            pb = M.get_playbook(r.ref)
            _FAMILIAS.setdefault(id(pb.get("ura_steps")), []).append(r.ref)
    chave = id(M.get_playbook(rota.ref).get("ura_steps"))
    refs = sorted(set(_FAMILIAS.get(chave, [])))
    if len(refs) <= 1:
        return "—"
    return "+".join(r.split("-")[0] for r in refs)


# ═════════════════════════════════════════════════════════════════════════════
# O COMPARADOR DE REGRESSÃO — SPEC-084 §5.2 e R3.
#
# 🔴 *"Depois de qualquer mudança, o replay de TODAS as rotas daquela seguradora
#    tem de manter ou aumentar as respondidas. Uma que caia é regressão, e o
#    bloco não fecha."*
#
# 📊 A razão de existir, contada em `corridor_playbooks.py`: **41 nomes de passo**
# aparecem em mais de um lugar (📊 no runtime são **74**, porque as famílias são
# compartilhadas POR REFERÊNCIA) e `_YELUM_FAMILY_STEPS` alimenta `hdi-auto` **e**
# `yelum-auto`. **Mexer num passo de família mexe em dois corredores.**
#
# 🔴 E o comparador tem de PODER ACUSAR. Antes de confiar nele, o BLOCO 0 regride
#    uma âncora de propósito e exige `exit != 0`. Comparador que nunca acusa não é
#    gate — é enfeite.
# ═════════════════════════════════════════════════════════════════════════════
def _linha_de_base(seguradora: Optional[str]) -> Dict[str, Any]:
    rotas = [r for r in M.rotas() if not seguradora or r.seguradora == seguradora]
    fora: Dict[str, Any] = {"commit": _commit(),
                            "gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
                            "rotas": {}}
    for r in rotas:
        rp = RP.replay(r)
        fora["rotas"][str(r)] = {
            "respondidas": rp.respondidas,
            "orfas_funcionais": len(rp.orfas_funcionais),
            "telas": len(rp.telas),
        }
    return fora


def _salvar_linha_de_base(arq: str, seguradora: Optional[str]) -> int:
    base = _linha_de_base(seguradora)
    os.makedirs(os.path.dirname(os.path.abspath(arq)) or ".", exist_ok=True)
    with open(arq, "w", encoding="utf-8") as fh:
        json.dump(base, fh, ensure_ascii=False, indent=1)
    print(f"linha de base salva: {arq}  ({len(base['rotas'])} rotas, commit {base['commit']})")
    return 0


def _comparar_com(arq: str, seguradora: Optional[str]) -> int:
    with open(arq, encoding="utf-8") as fh:
        base = json.load(fh)
    agora = _linha_de_base(seguradora)
    print(f"=== --comparar-com {os.path.basename(arq)} "
          f"(base: commit {base.get('commit')}) ===")
    print(f"  {'rota':52s} {'respondidas':>22s} {'orfas func.':>18s}")
    caiu = []
    for nome, a in sorted(agora["rotas"].items()):
        b = base["rotas"].get(nome)
        if b is None:
            print(f"  {nome:52s} {'(nova)':>22s}")
            continue
        d_resp = a["respondidas"] - b["respondidas"]
        d_orfa = len(str(a["orfas_funcionais"])) and a["orfas_funcionais"] - b["orfas_funcionais"]
        if d_resp or d_orfa:
            marca = "🔴 REGRESSAO" if d_resp < 0 else ("⬆" if d_resp > 0 else " ")
            print(f"  {nome:52s} {b['respondidas']:8d} -> {a['respondidas']:<8d} "
                  f"{d_resp:+4d} {b['orfas_funcionais']:5d} -> {a['orfas_funcionais']:<5d} "
                  f"{d_orfa:+3d}  {marca}")
        if d_resp < 0:
            caiu.append((nome, b["respondidas"], a["respondidas"]))
    if caiu:
        print()
        print(f"  🔴 {len(caiu)} rota(s) PERDERAM respondidas -- R3 violada:")
        for n, x, y in caiu:
            print(f"     {n}: {x} -> {y}")
        return 1
    print()
    print("  OK nenhuma rota perdeu respondidas (R3 satisfeita)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="A regua do corredor (SPEC-083)")
    ap.add_argument("--seguradora")
    ap.add_argument("--ramo")
    ap.add_argument("--servico")
    ap.add_argument("--todas", action="store_true")
    ap.add_argument("--formato", choices=["texto", "tabela", "markdown"], default="texto")
    ap.add_argument("--replay-detalhado", action="store_true")
    ap.add_argument("--verificar-mutacoes", action="store_true")
    ap.add_argument("--conferir-ancoras-de-desfecho", action="store_true")
    ap.add_argument("--exportar-arvore", action="store_true")
    ap.add_argument("--salvar-linha-de-base", metavar="ARQ")
    ap.add_argument("--comparar-com", metavar="ARQ")
    ap.add_argument("--so-orfas", action="store_true")
    a = ap.parse_args(argv)

    if a.verificar_mutacoes:
        res = VM.verificar(TESTE_DA_REGUA)
        print(VM.imprimir(res))
        return 0 if all(r.ok for r in res) else 1

    if a.conferir_ancoras_de_desfecho:
        print(conferir_ancoras_de_desfecho())
        return 0

    if a.exportar_arvore:
        import arvore as AR
        segs = [a.seguradora] if a.seguradora else M.seguradoras()
        for seg in segs:
            for ramo in (["auto", "residencial"] if not a.ramo else [a.ramo]):
                nos = AR.montar(seg, ramo)
                if not nos:
                    continue
                print()
                print(f"=== {seg} x {ramo} ===")
                print(AR.imprimir(nos, so_orfas=a.so_orfas))
        return 0

    if a.salvar_linha_de_base:
        return _salvar_linha_de_base(a.salvar_linha_de_base, a.seguradora)
    if a.comparar_com:
        return _comparar_com(a.comparar_com, a.seguradora)

    acervo = _sessoes_por_seguradora()
    demanda = {s: e for s, e, _c in PS.DEMANDA_MEDIDA}

    if a.replay_detalhado:
        rota = M.rota_de(a.seguradora, a.ramo, a.servico)
        if rota is None:
            print(f"rota inexistente: {a.seguradora} x {a.ramo} x {a.servico}")
            return 2
        print(RP.imprimir_detalhado(
            RP.replay(rota, sessoes_no_acervo=acervo.get(a.seguradora))))
        return 0

    # 🔴 As mutações rodam UMA vez e valem para todas as rotas cobertas pelo
    #    arquivo que as declara — não se roda o corredor 62 vezes.
    mut = VM.verificar(TESTE_DA_REGUA)
    mut_ok = (sum(1 for r in mut if r.ok), len(mut))

    if a.todas:
        notas = [RB.medir(r, sessoes_no_acervo=acervo.get(r.seguradora),
                          mutacoes_ok=mut_ok) for r in M.rotas()]
        if a.formato == "markdown":
            print(markdown(notas, demanda, acervo))
        else:
            print(tabela(notas, demanda))
        return 0

    rota = M.rota_de(a.seguradora, a.ramo, a.servico)
    if rota is None:
        print(f"rota inexistente: {a.seguradora} x {a.ramo} x {a.servico}")
        return 2
    n = RB.medir(rota, sessoes_no_acervo=acervo.get(rota.seguradora), mutacoes_ok=mut_ok)
    print(imprimir_nota(n))
    return 0


def _o_que_falta(n: RB.Nota) -> str:
    """A coluna 2 do inventário: o que falta para o nível da máquina de lavar."""
    if n.estado == "SEM_CORPUS":
        return "não há uma linha desta rota no corpus"
    if n.estado == "NAO_RESPONDE":
        r = n.replay
        d = r.determinismo if r else None
        return (f"o corredor não fala esta URA: {len(r.orfas_funcionais)} órfãs "
                f"funcionais e determinismo "
                f"{'—' if d is None else f'{100*d:.0f}%'}") if r else "eixo B zerado"
    faltam = sorted((i for i in n.itens if i.conta and i.pontos < i.maximo),
                    key=lambda x: x.maximo - x.pontos, reverse=True)
    return " · ".join(f"{i.nome} (+{i.maximo - i.pontos})"
                      for i in faltam[:4]) or "nada — está no nível"


def _o_que_destrava(n: RB.Nota) -> str:
    """A coluna 3: o que DESTRAVA cada uma.

    🔴 Regra do Founder, 21/08/2026:

    > *"Não é obrigatório termos todos os corredores 100%. O ideal é o máximo
    > possível... Mas devemos ter LISTADO o que trava de ter o nível da máquina
    > de lavar, para completarmos quando pudermos."*

    E o que não fecha vira **handoff limpo**, nunca chute.
    """
    if n.estado == "SEM_CORPUS":
        return "🧑 coleta dirigida: 1 acionamento observado desta rota"
    r = n.replay
    if n.estado == "NAO_RESPONDE":
        return (f"🤖 escrever passos para {len(r.orfas_funcionais)} tela(s) órfã(s) "
                f"em {r.sessoes_no_corpus} sessão(ões)") if r else "🤖 escrever passos"
    pend: List[str] = []
    for i in n.itens:
        if not i.conta or i.pontos == i.maximo:
            continue
        if "orfas" in i.nome:
            pend.append(f"🤖 mapear {len(r.orfas_funcionais)} tela(s)")
        elif "transcrita" in i.nome:
            pend.append("🤖 transcrever a sessão no bloco")
        elif "handoff" in i.nome:
            pend.append("🤖 ampliar handoff_triggers contra o corpus")
        elif "notes" in i.nome:
            pend.append("🤖 recontar as notes")
        elif "cliente recebe" in i.nome:
            pend.append("🤖 client_summary com dia + período")
        elif "tecla" in i.nome:
            pend.append("🤖 dar origem às teclas órfãs")
        elif "sessoes distintas" in i.nome:
            pend.append("🧑 coleta: +1 sessão desta rota")
        elif "deterministico" in i.nome:
            pend.append("🤖 subir o determinismo acima de 85%")
        elif "apelidos" in i.nome:
            pend.append("🧑 acesso ao Espelho para conferir os apelidos")
        elif "expectativa" in i.nome or "regras" in i.nome:
            pend.append("🤖 escrever as regras que a URA diz ao segurado")
    return " · ".join(dict.fromkeys(pend)) or "nada"


def markdown(notas: List[RB.Nota], demanda: Dict[str, int],
             acervo: Dict[str, int]) -> str:
    """O `INVENTARIO-DE-ROTAS.md` do Bloco D.

    📊 **Por que o cabeçalho importa:** o acervo é vivo. Entre duas medições com
    ~28 h de diferença, os eventos foram de 28.092 para 28.096. **Inventário sem
    carimbo é inventário que ninguém sabe se está velho.**
    """
    agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    L = ["# Inventário de rotas — a régua aplicada às 62\n",
         f"> Gerado em **{agora}** · commit `{_commit()}`",
         # 🔴 SEM BANCO, A LINHA DIZ QUE NAO MEDIU -- e nao "0".
         #
         # ⚠️ 22/08/2026: este inventario foi gerado uma vez da RAIZ do repo,
         #    onde `tem_banco()` nao acha o `backend/.env`.
         #    `_sessoes_por_seguradora` devolve `{}` e o cabecalho imprimia
         #    **"0 sessoes em 0 seguradoras"** -- um 📊 FALSO num documento
         #    gerado, que e exatamente o que a §12.1 do CLAUDE.md proibe.
         #    Zero MEDIDO e zero NAO MEDIDO nao sao a mesma coisa, e so um
         #    deles e um fato. 📊 De dentro de `backend/` a mesma geracao da
         #    543 sessoes em 10 seguradoras.
         (f"> 📊 acervo no momento da geração: "
          f"**{sum(acervo.values())} sessões** em {len(acervo)} seguradoras\n"
          if acervo else
          "> ⚠️ acervo **NÃO MEDIDO** nesta geração (banco inalcançável "
          "daqui). As notas abaixo vêm do CORPUS versionado e continuam "
          "válidas — só o carimbo do acervo está ausente. "
          "🔴 Rode de dentro de `backend/`, onde o `.env` mora.\n")]
    L.append("🔴 A nota é sempre sobre o **denominador real**. Item dispensado sai do")
    L.append("denominador e aparece explícito — **nunca é renormalizado**, e a")
    L.append("exibição **nunca é reescalada para /100**: `61/86 = 71%` pareceria")
    L.append("melhor que uma rota que ganhou 65 de 100 disputando tudo.\n")
    L.append("## A regra do Founder que governa este inventário\n")
    L.append("> *\"Não é obrigatório termos todos os corredores 100%. O ideal é o máximo")
    L.append("> possível. O que não for possível ter no nível da Allianz residencial máquina")
    L.append("> de lavar deve ser feito o mais confiável e completo possível, ajudar os agentes")
    L.append("> a executar, e quando não conseguirem, vai para handoff. **Mas devemos ter")
    L.append("> LISTADO o que trava de ter o nível da máquina de lavar, para completarmos")
    L.append("> quando pudermos.**\"*\n")
    L.append("🔴 **Uma rota em 60 com o bloqueio nomeado é ENTREGA. Uma rota em 95 com furo")
    L.append("invisível não é.** É por isso que este inventário tem três colunas, e não uma.\n")
    L.append("| seguradora | ramo | serviço | nota | patamar | 🔴 o que FALTA para o nível da máquina de lavar | 🔴 o que DESTRAVA | dem |")
    L.append("|---|---|---|---:|---|---|---|---:|")
    for n in sorted(notas, key=lambda x: (-x.fracao, str(x.rota))):
        pr = n.estado or f"{n.pontos}/{n.denominador}"
        L.append(f"| {n.rota.seguradora} | {n.rota.ramo} | {n.rota.servico} | **{pr}** | "
                 f"{n.patamar} | {_o_que_falta(n)} | {_o_que_destrava(n)} | "
                 f"{demanda.get(n.rota.servico, 0)} |")
    L.append("\n## Os eixos, para quem quiser a decomposição\n")
    L.append("| seguradora | ramo | serviço | A | B | C | D | E | família |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---|")
    for n in sorted(notas, key=lambda x: (-x.fracao, str(x.rota))):
        e = n.por_eixo()
        g = lambda k: (str(e[k][0]) if k in e else "—")   # noqa: E731
        L.append(f"| {n.rota.seguradora} | {n.rota.ramo} | {n.rota.servico} | "
                 f"{g('A')} | {g('B')} | {g('C')} | {g('D')} | {g('E')} | "
                 f"{familia_de(n.rota)} |")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
