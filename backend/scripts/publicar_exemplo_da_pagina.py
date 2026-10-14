# -*- coding: utf-8 -*-
"""Os EXEMPLOS da página do cliente com a marca REAL de uma corretora — SPEC-132-B (fatia E · D-132B-08).

    cd backend
    python -m scripts.publicar_exemplo_da_pagina --company-id <uuid> --pagina venda [--com-apolice]
    python -m scripts.publicar_exemplo_da_pagina --company-id <uuid> --pagina renovacao
    ... --confirmar                      publica de verdade (grava o artefato e devolve o link /r/)
    ... --saida <arquivo.html>           sem --confirmar: onde gravar o HTML (padrão: ./exemplo-<pagina>.html)

O que faz:
  · monta um modelo FICTÍCIO da página — a cliente "Mariana", um carro popular, as 3 opções do modelo do contrato
    (`tests/fixtures/proposta/modelo_contrato.json`, cujos preços são os das ofertas saneadas do canário:
    `ofertas_canario_saneadas.json`), a validade e o vencimento contados a partir de HOJE; na renovação, o "seu seguro
    hoje" e uma dona fictícia SEM telefone — com a MARCA REAL da corretora, lida do banco pelo `company_id`
    (`proposta.montar_anfitria`, a mesma leitura do produto) e a faixa "Exemplo — dados fictícios" no topo;
  · em volta das opções, tudo sai das MESMAS funções do produto: a marca, a FAQ, os passos do sinistro, o bloco da
    venda (`bloco_da_venda`/`marca_da_venda`/`pagina_da_cotacao`), o bloco da renovação (`bloco_da_renovacao`,
    `faq_da_renovacao`), o "Quero fechar" (`cta_da_pagina`) e a guarda da comissão (`_sem_comissao`);
  · com `--confirmar`, publica pelo MESMO caminho do produto (`proposta._gravar_e_compartilhar`: artefato
    `proposal.quote` no Hub → render → publicar → compartilhar), com o link valendo 💭 30 dias, e imprime SÓ o link
    `/r/…` e o tamanho do HTML. Sem `--confirmar`: só renderiza (o MESMO renderizador do template) e grava o HTML num
    arquivo local — o banco é aberto SÓ PARA LER (qualquer escrita levanta `EscritaProibida`).

🔴 O caminho mínimo e honesto (nada de linha falsa em `multicalculo_pedidos` nem em `renovacoes`): os publicadores do
produto (`publicar_cotacao`/`publicar_renovacao`) leem um pedido REAL do motor — o exemplo não tem. Então o modelo é
montado aqui e entregue a `_gravar_e_compartilhar` com um `pedido_id` SINTÉTICO (uuid5 de corretora + página: rodar de
novo = VERSÃO nova da mesma peça, nunca uma pilha de peças) e o assunto do artefato marcado
`{"kind": "exemplo_da_pagina", "exemplo": true}`. Nenhuma tabela do motor, da renovação ou da fila é escrita; o único
leitor de `subject_ref.pedido_id` é o próprio publicador (📊 14/10 `grep -rn "subject_ref->>pedido_id"` fora dos testes:
1 linha, `proposta.py`).

⛔ Nenhuma pessoa real: cliente, corretor e dona são fictícios. ⛔ Nenhum telefone: o WhatsApp da marca é TIRADO do
modelo e a página sai sem o botão "Quero fechar" (diz "responda a mensagem em que recebeu este link"). Só com
`--com-whatsapp-da-corretora` (decisão de quem roda) o botão leva ao WhatsApp de ATENDIMENTO da corretora — o número
dela, nunca de pessoa. `--whatsapp-do-dono +55…` (E.164 BR, um número FICTÍCIO de quem roda) põe esse número como
o WhatsApp de trabalho CONFIRMADO da dona/do corretor fictício — SÓ no modelo do exemplo, nunca em tabela — e a barra
"Quero fechar"/"Quero renovar" e o "Quem cuida de você" passam a apontar para ele. ⛔ Nenhum nome de corretora neste arquivo (CLAUDE.md §13.9): tudo vem do banco.

Ambiente (nomes, nunca valores): SUPABASE_URL, SUPABASE_KEY (service role) e as obrigatórias de `app.core.config`
(OPENAI_API_KEY, ENCRYPTION_KEY, MINIO_ROOT_USER, MINIO_ROOT_PASSWORD) — no contêiner do backend já estão; com
`--confirmar`, também o endereço público do painel: PUBLIC_APP_URL (ou NEXT_PUBLIC_APP_URL, SMITH_WEB_URL, FRONTEND_URL).
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import re
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

#: o modelo do CONTRATO §5 (os preços REAIS do canário saneado) — a fonte das 3 opções do exemplo
MODELO_DO_CONTRATO = BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json"
PAGINAS = ("venda", "renovacao")
#: 💭 quanto tempo o link do exemplo vale (a página diz "preços válidos até" = isto menos a folga do link da config)
DIAS_DO_LINK = 30
#: 💭 o vencimento fictício da renovação, contado a partir de hoje (DEPOIS da validade dos preços, como na vida)
DIAS_ATE_VENCER = 30
#: 💭 o reajuste fictício entre o "seu seguro hoje" e a "Sua renovação" (a página mostra o R$ e o %)
REAJUSTE_FICTICIO = 0.09
#: 💭 o prêmio da apólice fictícia que a cliente "tem hoje" (`--com-apolice`: a economia é contra ele)
PREMIO_DA_APOLICE_FICTICIA = 6390.0
#: o espaço dos `pedido_id` sintéticos (uuid5): o mesmo exemplo da mesma corretora = a MESMA peça, versão nova
ESPACO_DOS_EXEMPLOS = uuid.UUID("e4e3a132-0b0e-4e0e-8e0e-000000000132")

#: ⛔ só gente FICTÍCIA (CLAUDE.md §13.9) — nenhuma tem telefone, documento ou sobrenome
CLIENTE_FICTICIA = "Mariana"
CORRETOR_FICTICIO = "Caio"
DONA_FICTICIA = "Bruna"
CARRO_POPULAR = {"rotulo": "carro", "descricao": "Chevrolet Onix 1.0 flex", "ano": "2022/2023", "apelido": "Onix"}


#: o "Meu WhatsApp de trabalho" que `--whatsapp-do-dono` aceita: E.164 do Brasil (+55, DDD, 8 ou 9 dígitos)
_RE_E164_BR = re.compile(r"^\+55[1-9][1-9]9?\d{8}$")


def whatsapp_do_dono(valor: str) -> str:
    """O número de `--whatsapp-do-dono` validado (E.164 BR, ex.: +5511900000000) → os dígitos que a página usa."""
    v = str(valor or "").strip()
    if not _RE_E164_BR.fullmatch(v):
        raise ValueError(f"--whatsapp-do-dono precisa ser E.164 do Brasil, como +5511900000000 (veio {v!r})")
    return v[1:]


class EscritaProibida(RuntimeError):
    """Sem `--confirmar` o exemplo não escreve no banco: uma tentativa de escrita é um defeito, e para tudo."""


class _TabelaSoLeitura:
    def __init__(self, tabela: Any, nome: str):
        self._tabela, self._nome = tabela, nome

    def _recusar(self, *_a: Any, **_k: Any) -> Any:
        raise EscritaProibida(f"sem --confirmar nada é gravado (tentativa de escrever em {self._nome!r})")

    insert = upsert = update = delete = _recusar

    def __getattr__(self, nome: str) -> Any:
        return getattr(self._tabela, nome)


class SoLeitura:
    """O cliente do banco que só LÊ: `table(...).select(...)` passa; `insert/upsert/update/delete` e `rpc` levantam."""

    def __init__(self, db: Any):
        self._db = db

    def table(self, nome: str) -> _TabelaSoLeitura:
        return _TabelaSoLeitura(self._db.table(nome), nome)

    from_ = table

    def rpc(self, nome: str, *_a: Any, **_k: Any) -> Any:
        raise EscritaProibida(f"sem --confirmar nenhuma função do banco é chamada ({nome!r})")

    def __getattr__(self, nome: str) -> Any:
        # 🔴 fechado por padrão: nada além de `table`/`from_` chega ao cliente de verdade (nem `.client`, que o
        # `ArtifactService` desembrulha com `getattr(db, "client", db)` — por ele uma escrita passaria por fora)
        raise AttributeError(f"o banco do ensaio só lê tabelas (sem {nome!r})")


def pedido_do_exemplo(company_id: str, pagina: str, *, com_apolice: bool = False) -> str:
    """O `pedido_id` SINTÉTICO do exemplo (nunca existe em `multicalculo_pedidos`): estável por corretora + página."""
    return str(uuid.uuid5(ESPACO_DOS_EXEMPLOS, f"{company_id}:{pagina}:{'com_apolice' if com_apolice else 'base'}"))


def _contrato() -> Dict[str, Any]:
    m = json.loads(MODELO_DO_CONTRATO.read_text(encoding="utf-8"))
    m.pop("_contrato", None)
    return m


def _derivada(base: Mapping[str, Any], *, id_: str, rotulo: str, fator: float) -> Dict[str, Any]:
    """Uma opção da renovação a partir da "Sua renovação" (o robô a calcula assim: a mesma seguradora, outro pedido)."""
    o = copy.deepcopy(dict(base))
    o.update(id=id_, rotulo=rotulo, premio_anual=round(float(base["premio_anual"]) * fator, 2), o_que_muda=[])
    if isinstance(o.get("parcelas"), dict) and o["parcelas"].get("valor"):
        o["parcelas"] = dict(o["parcelas"], valor=round(float(o["parcelas"]["valor"]) * fator, 2))
        o["parcelas"].pop("total", None)
    o.pop("parcelas_sem_juros", None)
    o.pop("por_que_mais_barata", None)
    return o


def _opcoes_da_venda(contrato: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """As 3 opções da venda (§4.3: Recomendada · Mais em conta · Mais completa) — as do contrato, como o motor as
    devolveu; a "outra completa" do contrato faz o papel da "Mais completa" (a seguradora com mais cobertura)."""
    ops = [copy.deepcopy(o) for o in contrato["opcoes"]]
    for o in ops[1:]:
        if o["id"] == "outra_completa":
            o["id"], o["rotulo"] = "mais_completa", "Mais completa"
    return ops


#: as ofertas saneadas do canário — de onde vêm as coberturas BRUTAS que os textos do produto leem
OFERTAS_SANEADAS = BACKEND / "tests" / "fixtures" / "proposta" / "ofertas_canario_saneadas.json"


def _coberturas_brutas(seguradora: str, premio: float) -> Dict[str, Any]:
    """As coberturas da oferta saneada que deu esta opção do contrato (a mesma seguradora e o mesmo prêmio)."""
    dados = json.loads(OFERTAS_SANEADAS.read_text(encoding="utf-8"))
    o = next((x for x in dados.get("ofertas") or [] if str(x.get("seguradora")) == seguradora
              and abs(float(x.get("premio_total") or 0) - float(premio)) < 0.005), None)
    return dict((o or {}).get("coberturas") or {})


def _opcoes_da_renovacao(contrato: Mapping[str, Any], *, premio_de_hoje: float) -> List[Dict[str, Any]]:
    """A "Sua renovação" (a seguradora de hoje) em 1º · Franquia reduzida · Mais completa. Os motivos, o "o que muda"
    e o "por que" de cada cartão são os textos do PRODUTO (`comparacao._motivos`/`_o_que_muda`/
    `_por_que_da_renovacao`, os mesmos de `_opcoes_da_renovacao` da 131-B) sobre as coberturas da oferta saneada."""
    from app.services.multicalculo import comparacao as CMP

    rec = copy.deepcopy(contrato["opcoes"][0])
    ramo = int(contrato.get("ramo") or CMP.RAMO_AUTO)
    sua = dict(rec, id="sua_renovacao", rotulo="Sua renovação", o_que_muda=[])
    reduzida = _derivada(sua, id_="franquia_reduzida", rotulo="Franquia reduzida", fator=1.05)
    if isinstance(reduzida.get("franquia"), dict) and reduzida["franquia"].get("valor"):
        reduzida["franquia"] = dict(reduzida["franquia"], valor=round(float(reduzida["franquia"]["valor"]) / 2, 2),
                                    tipo="Reduzida")
    completa = _derivada(sua, id_="mais_completa", rotulo="Mais completa", fator=1.08)
    ops = [sua, reduzida, completa]
    cob = _coberturas_brutas(str(rec["seguradora"]), float(rec["premio_anual"]))
    entradas = [{"oferta_id": o["id"], "seguradora": o["seguradora"], "premio_anual": o["premio_anual"],
                 "franquia": dict(o.get("franquia") or {"valor": None}), "parcelas": o.get("parcelas"),
                 "opcao": "anterior", "ramo": ramo,
                 "coberturas_brutas": dict(cob, reparoRapido=True) if o["id"] == "mais_completa" else dict(cob)}
                for o in ops]
    base = entradas[0]
    hoje = {"seguradora": sua["seguradora"], "premio_anual": premio_de_hoje}
    for o, e in zip(ops, entradas):
        o["motivos"] = CMP._motivos(e, "renovacao", ranking_completa=[], referencia=base, rotulo_ref=sua["rotulo"],
                                    pool=entradas, apolice_atual=hoje, ramo=ramo, renovacao=True)
        o["o_que_muda"] = CMP._o_que_muda(e, base, sua["rotulo"], o["id"], renovacao=True)
        o["por_que"] = CMP._por_que_da_renovacao(e, o["id"], base, ramo)
        # R6/(e): os adicionais da oferta (os pequenos reparos da "Mais completa"), como `comparacao._opcao` os grava
        a_mais = CMP.coberturas_a_mais({"coberturas": e["coberturas_brutas"]}, ramo=ramo)
        if a_mais:
            o["coberturas_a_mais"] = a_mais
    return ops


def _economia_contra_a_apolice(modelo: Mapping[str, Any], atual: float) -> Optional[Dict[str, Any]]:
    """A MESMA conta de `proposta.economia` (contra o preço atual: o menor preço do quadro), sobre o quadro do exemplo."""
    precos = [float(x["premio_anual"]) for x in list(modelo.get("opcoes") or []) + list(modelo.get("ranking") or [])
              if x.get("premio_anual")]
    if not precos or atual - min(precos) < 0.01:
        return None
    para = min(precos)
    return {"ate": round(atual - para, 2), "de": round(atual, 2), "para": round(para, 2), "contra": "atual"}


async def montar_modelo_de_exemplo(db: Any, company_id: str, pagina: str, *, com_apolice: bool = False,
                                   com_whatsapp_da_corretora: bool = False, agora: Optional[datetime] = None,
                                   baixar_logo: Any = None, whatsapp_do_dono_ficticio: Optional[str] = None
                                   ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """(modelo, ctx, pedido_id) do exemplo. Lê do banco SÓ a marca e a config da corretora (filtro `company_id`).
    `whatsapp_do_dono_ficticio` (E.164 BR): o WhatsApp de trabalho CONFIRMADO da dona/do corretor fictício — SÓ no
    modelo (nunca em tabela); o "Quem cuida de você" e o "Quero fechar"/"Quero renovar" passam a apontar para ele."""
    from app.services.multicalculo import config as CFG
    from app.services.multicalculo import manual_de_negociacao as MANUAL
    from app.services.multicalculo import proposta as P

    if pagina not in PAGINAS:
        raise ValueError(f"página desconhecida: {pagina!r} (aceitas: {', '.join(PAGINAS)})")
    company_id = P._uuid(company_id, "company_id")
    renovacao = pagina == "renovacao"
    pedido_id = pedido_do_exemplo(company_id, pagina, com_apolice=com_apolice and not renovacao)
    cfg = CFG.carregar(company_id, db=db, servico="renovacao" if renovacao else "cotacao")
    anfitria = await P.montar_anfitria(db, company_id, cfg, baixar_logo=baixar_logo)
    numero = anfitria.pop("whatsapp", None)                     # ⛔ nenhum telefone, salvo a escolha explícita
    if com_whatsapp_da_corretora and numero:
        anfitria["whatsapp"] = numero
    do_dono = whatsapp_do_dono(whatsapp_do_dono_ficticio) if whatsapp_do_dono_ficticio else None
    # a regra do produto (D-131-42 / D-132B-05): o dono confirmado → a corretora → ninguém
    destino = do_dono or (numero if com_whatsapp_da_corretora else None)
    pessoa = {"whatsapp": do_dono} if do_dono else {}

    hoje = P._agora(agora)
    folga = int(cfg["link"]["folga_dias"])
    dias = max(1, DIAS_DO_LINK - folga)                        # o link vale `dias + folga` = DIAS_DO_LINK
    contrato = _contrato()
    modelo: Dict[str, Any] = {
        **contrato,
        "origem": "corretora",
        "cliente": {"primeiro_nome": CLIENTE_FICTICIA},
        "bem": dict(CARRO_POPULAR),
        "anfitria": anfitria,
        "entre_corretoras": None,
        "validade_ate": (hoje.date() + timedelta(days=dias)).isoformat(),
        "gerado_em": hoje.replace(microsecond=0).isoformat(),
        "aviso_legal": P.AVISO_LEGAL_CORRETORA,
        "exemplo": True,
    }
    resumo = dict(modelo.get("resumo") or {})
    resumo.pop("economia", None)
    modelo["resumo"] = resumo
    ref_curta = pedido_id[:8]

    if renovacao:
        modelo["situacao"] = "renovacao"
        premio_de_hoje = round(float(contrato["opcoes"][0]["premio_anual"]) / (1 + REAJUSTE_FICTICIO), 2)
        modelo["opcoes"] = _opcoes_da_renovacao(contrato, premio_de_hoje=premio_de_hoje)
        item = {"fimvig": (hoje.date() + timedelta(days=DIAS_ATE_VENCER)).isoformat(),
                "seguradora_atual": modelo["opcoes"][0]["seguradora"], "premio_atual": premio_de_hoje}
        reajuste = CFG.reajuste_basica_pct(cfg, modelo["ramo"])
        modelo["renovacao"] = P.bloco_da_renovacao(item, dono={"primeiro_nome": DONA_FICTICIA, **pessoa}, anos=None,
                                                   basica=None, reajuste_pct=reajuste)
        modelo["cta"] = P.cta_da_pagina(destino, modelo["opcoes"], nome=CLIENTE_FICTICIA, ref_curta=ref_curta,
                                        renovacao=True)
        modelo["renovacao"]["fechar_com"] = "dono" if do_dono else ("corretora" if destino else "nenhum")
        modelo["faq"] = P.faq_da_renovacao(ramo=modelo["ramo"], opcoes=modelo["opcoes"],
                                           vence_em=modelo["renovacao"].get("vence_em"), reajuste_pct=reajuste,
                                           com_whatsapp=bool(destino))
    else:
        modelo["situacao"] = "novo_com_apolice" if com_apolice else "novo_sem_apolice"
        modelo["opcoes"] = _opcoes_da_venda(contrato)
        if com_apolice:
            eco = _economia_contra_a_apolice(modelo, PREMIO_DA_APOLICE_FICTICIA)
            if eco:
                modelo["resumo"]["economia"] = eco
        modelo["cta"] = P.cta_da_pagina(destino, modelo["opcoes"], nome=CLIENTE_FICTICIA, ref_curta=ref_curta)
        modelo["venda"] = P.bloco_da_venda(corretor={"primeiro_nome": CORRETOR_FICTICIO, **pessoa},
                                           marca=P.marca_da_venda(db, company_id),
                                           pagina=CFG.pagina_da_cotacao(cfg), destino=destino)
        modelo["faq"] = [{"p": f["pergunta"], "r": f["resposta"]} for f in modelo["venda"]["faq"]]
        modelo["pagina"] = "venda"
    modelo["sinistro"] = MANUAL.sinistro_padrao(cfg, com_whatsapp=bool(destino))
    P._sem_comissao(modelo)
    ctx = {"anfitria_id": company_id, "cfg_sol": cfg, "dias": dias, "hoje": hoje, "refs": {}}
    return modelo, ctx, pedido_id


def renderizar(modelo: Mapping[str, Any]) -> str:
    """O HTML pelo MESMO gancho que o Hub usa ao renderizar a peça (`templates.PROPOSTA.renderizador`)."""
    from app.services.artifacts.templates import POR_CHAVE
    from app.services.multicalculo.proposta import TEMPLATE_DA_PROPOSTA

    return POR_CHAVE[TEMPLATE_DA_PROPOSTA].renderizador(dict(modelo))


async def gerar_exemplo(db: Any, company_id: str, pagina: str, *, com_apolice: bool = False,
                        com_whatsapp_da_corretora: bool = False, confirmar: bool = False,
                        whatsapp_do_dono_ficticio: Optional[str] = None,
                        saida: Optional[Path] = None, base_url: Optional[str] = None,
                        agora: Optional[datetime] = None, baixar_logo: Any = None) -> Dict[str, Any]:
    """Monta e (com `confirmar`) publica o exemplo. Devolve {url?, token?, artifact_id?, arquivo?, bytes}."""
    from app.services.multicalculo import proposta as P

    if not confirmar:
        modelo, _ctx, _pid = await montar_modelo_de_exemplo(
            SoLeitura(db), company_id, pagina, com_apolice=com_apolice,
            com_whatsapp_da_corretora=com_whatsapp_da_corretora, agora=agora, baixar_logo=baixar_logo,
            whatsapp_do_dono_ficticio=whatsapp_do_dono_ficticio)
        html = renderizar(modelo)
        destino = Path(saida) if saida else Path.cwd() / f"exemplo-{pagina}{'-com-apolice' if com_apolice else ''}.html"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(html.encode("utf-8"))              # os MESMOS bytes do render (sem trocar \n no Windows)
        return {"arquivo": str(destino), "bytes": len(html.encode("utf-8"))}

    base = P._base_do_link(base_url)                           # sem endereço público → recusa ANTES de gravar
    modelo, ctx, pedido_id = await montar_modelo_de_exemplo(
        db, company_id, pagina, com_apolice=com_apolice, com_whatsapp_da_corretora=com_whatsapp_da_corretora,
        agora=agora, baixar_logo=baixar_logo, whatsapp_do_dono_ficticio=whatsapp_do_dono_ficticio)
    titulo = "Exemplo · Renovação do seguro" if pagina == "renovacao" else "Exemplo · Cotação de seguro"
    publicado = P._gravar_e_compartilhar(db, ctx["anfitria_id"], pedido_id, modelo, ctx, base, titulo_base=titulo,
                                         subject_extra={"kind": "exemplo_da_pagina", "exemplo": True,
                                                        "pagina": pagina})
    return {**publicado, "bytes": len(renderizar(modelo).encode("utf-8"))}


def _argumentos(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Publica (ou só renderiza) um EXEMPLO da página do cliente com a marca "
                                             "real da corretora e dados fictícios.")
    ap.add_argument("--company-id", required=True, help="o uuid da corretora (a marca vem do banco)")
    ap.add_argument("--pagina", required=True, choices=PAGINAS)
    ap.add_argument("--com-apolice", action="store_true", help="venda: a cliente tem apólice (mostra a economia)")
    ap.add_argument("--com-whatsapp-da-corretora", action="store_true",
                    help="o botão 'Quero fechar' leva ao WhatsApp de atendimento da corretora (padrão: sem botão)")
    ap.add_argument("--whatsapp-do-dono", default=None, metavar="+55DDDNUMERO",
                    help="o WhatsApp de trabalho CONFIRMADO do dono/corretor fictício (E.164 BR, ex.: +5511900000000):"
                         " só no modelo do exemplo, nunca em tabela; a barra 'Quero fechar' aponta para ele")
    ap.add_argument("--confirmar", action="store_true", help="publica de verdade; sem isto, só grava o HTML local")
    ap.add_argument("--saida", type=Path, default=None, help="sem --confirmar: o arquivo .html de saída")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None, *, db: Any = None) -> int:
    a = _argumentos(argv)
    if a.whatsapp_do_dono:
        try:
            whatsapp_do_dono(a.whatsapp_do_dono)
        except ValueError as exc:
            raise SystemExit(str(exc))
    if db is None:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
    r = asyncio.run(gerar_exemplo(db, a.company_id, a.pagina, com_apolice=a.com_apolice,
                                  com_whatsapp_da_corretora=a.com_whatsapp_da_corretora, confirmar=a.confirmar,
                                  whatsapp_do_dono_ficticio=a.whatsapp_do_dono,
                                  saida=a.saida))
    print(r["url"] if a.confirmar else r["arquivo"])
    print(f"{r['bytes']} bytes de HTML")
    return 0


if __name__ == "__main__":
    sys.exit(main())
