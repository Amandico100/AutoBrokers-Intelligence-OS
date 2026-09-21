# -*- coding: utf-8 -*-
"""🔴 A COSTURA — do payload do agente à mensagem que o segurado recebe.

Por que este arquivo existe
===========================
O teste do fio (`test_o_fio_do_portal_de_vidros.py`) montava os `params` a
partir do HAR. Em produção quem os monta é `portal_params.build_portal_params`,
e é **entre as duas peças** que mora o defeito que nenhum dos dois lados vê:

    o agente diz "para-brisa"     ·  o catálogo da apólice diz "VIDRO PARABRISA"
    C grava `local.cidade_servico`·  A lê `local.cidade_servico`
    C compõe a descrição          ·  o portal exige 30 caracteres
    C normaliza "LIBERTY"→"Yelum" ·  A resolve "Yelum"→slug `LIBERTY`

Aqui o fio é atravessado INTEIRO, com os três motores reais e um dublê só na
borda:

    InfoCap/perfil (dublê)
      → portal_params.build_portal_params      (motor real, fatia C)
      → o `params` entra SEM RETOQUE em
        vidros_apifirst.abrir_atendimento_api  (motor real, fatia A)
        contra o replay dos HAR reais          (dublê de borda)
      → o `evidence` que sai entra em
        portal_params.format_result            (motor real, fatia C)
      → e a asserção é sobre A MENSAGEM que o atendente lê ao segurado.

⛔ PII: os valores do segurado (CPF, placa, chassi, telefone, e-mail, apólice)
são DERIVADOS do HAR em tempo de execução e nunca impressos. O que está escrito
aqui é o que o SEGURADO DIZ ("para-brisa", "amassei a porta e o paralama") —
que é a entrada sob teste, e não é dado de ninguém.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _replay_vidros as RV                                  # noqa: E402
from app.agents.tools import portal_params as PP             # noqa: E402
from portal_worker import guardrails as G                    # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF     # noqa: E402
from portal_worker.journeys import vidros_estado as ST       # noqa: E402

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


class RuntimeDeReplay:
    def __init__(self, *, liberado=True):
        self.gravacoes: list = []
        self.guard = G.PortalActionGuard(material_liberado=liberado,
                                         _checkpoint=self.checkpoint)

    async def checkpoint(self, patch):
        self.gravacoes.append(patch)


# ==========================================================================
# Os dublês de BORDA — montados do HAR, em tempo de execução
# ==========================================================================
def bordas_do_har(chamadas):
    """`(profile, infocap, catalogo)` a partir do que o portal recebeu e devolveu.

    📊 Cada campo vem de um corpo ou de uma resposta REAL. O `profile` é o
    Perfil de Acionamento da corretora (nome, e-mail, telefone, CNPJ) e o
    `infocap` é o retorno do vehicle lookup — as duas bordas que o
    `build_portal_params` consulta e que aqui não têm rede nenhuma.
    """
    abertura = RV.primeira(chamadas, "POST", "/atendimentos", requisicao=True) or {}
    apolice = RV.primeira(chamadas, "GET", "/apolices") or {}
    solicitante = RV.primeira(chamadas, "POST", "/solicitantes", requisicao=True) or {}
    corretor = RV.primeira(chamadas, "PUT", "/atendimentos/corretores",
                           requisicao=True) or {}
    patch = RV.primeira(chamadas, "PATCH", "/atendimentos", requisicao=True) or {}
    cidades = RV.primeira(chamadas, "GET", "/cidades") or []
    motivos = RV.primeira(chamadas, "GET", "/motivos-dano") or []
    itens = RV.primeira(chamadas, "GET", "/apolices/itens-cobertos") or []
    telefones = solicitante.get("Telefones") or []

    cidade = next((c for c in cidades
                   if isinstance(c, dict) and c.get("Codigo") == patch.get("CodigoCidade")),
                  {})
    motivo = next((m for m in motivos
                   if isinstance(m, dict)
                   and m.get("CodigoObjetoCausa") == patch.get("CodigoObjetoCausa")), {})
    item = next((i for i in itens
                 if isinstance(i, dict)
                 and i.get("CodigoItemCoberto") == patch.get("CodigoItemCoberto")), {})

    profile = {
        "nome": str(solicitante.get("NomeSolicitante") or "CORRETORA"),
        "email": str(solicitante.get("EmailTitularAplice")
                     or solicitante.get("EmailSegurado") or ""),
        "telefone": str((telefones[0] or {}).get("Numero") or "") if telefones else "",
        "cpf_cnpj": str(corretor.get("Documento") or ""),
    }
    iso = str(abertura.get("DataSinistro") or "")[:10]
    infocap = {
        "ok": True, "status": "found",
        "policy": {
            "numapo": str(apolice.get("NumeroDaApolice") or ""),
            # 🔴 O nome LEGADO, como a InfoCap o entrega — é ele que faz a
            # tradução `normalize_insurer` → `resolver_seguradora` acontecer
            # de verdade, em vez de ser pulada.
            "seguradora": str(abertura.get("Seguradora") or ""),
            "active": True,
        },
        "vehicle": {"placa": str(abertura.get("PlacaInformada") or ""),
                    "chassi": str(apolice.get("Chassi") or ""),
                    "veiculo": str(apolice.get("DescricaoVeiculo") or "")},
        "client": {"nome": str(apolice.get("NomeSegurado") or ""),
                   "cpf_cnpj": str(abertura.get("CpfCnpjSegurado") or ""),
                   "email": str(solicitante.get("EmailSegurado") or ""),
                   "telefone": str((telefones[0] or {}).get("Numero") or "")
                   if telefones else "",
                   "cidade": str(cidade.get("Nome") or ""),
                   "estado": str(cidade.get("UF") or ""),
                   "cep": str(patch.get("Cep") or "")},
    }
    catalogo = {
        "cidade": f"{cidade.get('Nome')}/{cidade.get('UF')}",
        "motivo": str(motivo.get("DescricaoObjetoCausa") or ""),
        "item": str(item.get("Descricao") or ""),
        "data": "/".join(reversed(iso.split("-"))) if iso else "",
        "perimetro": str(patch.get("PerimetroDano") or ""),
    }
    return profile, infocap, catalogo


def costurar(nome, *, peca, como=None, extras=None, liberado=True,
             renomear_cidade=False):
    """A costura inteira, ponta a ponta. Devolve tudo o que ela produziu."""
    chamadas = RV.carregar(nome)
    profile, infocap, catalogo = bordas_do_har(chamadas)
    especificos = {"cidade_para_o_servico": catalogo["cidade"]}
    especificos.update(extras or {})
    flat = {
        "cpf_cnpj": infocap["client"]["cpf_cnpj"],
        "data_dano": catalogo["data"],
        "peca": peca,
        # 📊 O portal manda `U` ou `R` (a PRIMEIRA LETRA do rótulo). A pergunta
        # da fatia C oferece exatamente "urbano" e "rodoviario".
        "onde_ocorreu": "rodoviario" if catalogo["perimetro"] == "R" else "urbano",
        "como_ocorreu": como if como is not None else catalogo["motivo"],
        "especificos": especificos,
    }
    params, erro = PP.build_portal_params(flat, profile, infocap,
                                          enviar_de_verdade=True)
    if params is None:
        return {"params": None, "erro": erro, "page": None, "resultado": None,
                "evidence": {}, "mensagem": "", "catalogo": catalogo}

    # 🔴 A MUTAÇÃO do gate: renomeia a chave SÓ do lado de C. Nada mais muda.
    if renomear_cidade:
        params["local"]["cidade_do_servico"] = params["local"].pop("cidade_servico")

    params["_idempotency_key"] = PP.chave_de_idempotencia(params, "empresa-de-teste")
    params["_runtime"] = RuntimeDeReplay(liberado=liberado)

    page = RV.PaginaDeReplay(chamadas)
    evidence: dict = {}
    # ⛔ `params` entra SEM RETOQUE: é exatamente o dicionário que a tool monta.
    resultado = asyncio.run(AF.abrir_atendimento_api(page, params, evidence))

    # O worker junta `captured` sobre `evidence` — `worker._augment_hitl_evidence`.
    capturado = getattr(resultado, "captured", {}) or {}
    mensagem_do_motor = str(getattr(resultado, "message", "") or "")
    job = {"status": getattr(resultado, "status", "failed"),
           "evidence": {**evidence, **capturado, "message": mensagem_do_motor}}
    return {"params": params, "erro": None, "page": page, "resultado": resultado,
            "evidence": job["evidence"], "mensagem": PP.format_result(job),
            "catalogo": catalogo, "profile": profile, "infocap": infocap}


# ==========================================================================
try:
    RV.carregar("LAT")
except RV.HarAusente as e:
    print("\n[SKIP] " + str(e))
    sys.exit(0)

# ==========================================================================
print("\n[C1] PARA-BRISA — o agente diz 'para-brisa' e o pedido sai inteiro")
# ==========================================================================
# 🔴 O que a conversa teria coletado ANTES de chamar a tool — nas palavras do
# segurado, nunca nas do portal. 📊 A captura mandou as respostas 2 (`EM FRENTE
# AO CARONA`), 2 (`MENOR (POSSIBILIDADE DE REPARO)`) e 798 (`NÃO SABE`); aqui o
# que entra é "do lado do passageiro", "pequenininha" e "nao sei", e quem
# traduz é o motor de perguntas.
DO_SEGURADO_PARABRISA = {
    "aceita_reparo": "sim",
    "onde_realizar_o_servico": "levar na oficina",
    "posicao_do_trincado": "do lado do passageiro",
    "tamanho_do_trincado": "pequenininha",
    "sensor_de_direcao_ou_faixa": "nao sei",
}
c1 = costurar("NOVO", peca="para-brisa", extras=DO_SEGURADO_PARABRISA)
check("C1: `build_portal_params` aceitou o payload do agente",
      c1["erro"] is None and c1["params"] is not None, c1["erro"])

p1 = c1["params"] or {}
check("C1: a seguradora foi traduzida pela tabela UNICA (legado → nome de tela)",
      p1.get("insurer_name") == "Yelum", p1.get("insurer_name"))
check("C1: e a journey resolveu esse nome de tela no slug da API",
      (c1["evidence"].get("seguradora") or {}).get("slug") == "LIBERTY",
      c1["evidence"].get("seguradora"))
check("C1: a descricao composta passa dos 30 caracteres que o portal exige",
      len(p1["dano"]["descricao"]) >= 30, len(p1["dano"]["descricao"]))
check("C1: o job chegou ao fim (`done`)",
      getattr(c1["resultado"], "status", "") == "done",
      getattr(c1["resultado"], "message", ""))

d1 = c1["evidence"].get("desfecho") or {}
check("C1: o desfecho e o que o PORTAL decidiu (loja_direta)",
      d1.get("tipo") == ST.DESFECHO_LOJA_DIRETA, d1.get("tipo"))
check("C1: a peca escolhida e a que o portal recebeu",
      (c1["evidence"].get("peca") or {}).get("descricao") == c1["catalogo"]["item"],
      (c1["evidence"].get("peca") or {}).get("descricao"))
check("C1: e o reparo foi gravado como o segurado decidiu", d1.get("reparo") is True)

# ---- A MENSAGEM, que e o que o segurado ouve -------------------------
msg1 = c1["mensagem"]
numero = str(c1["evidence"].get("protocolo") or "")
check("C1: a mensagem traz o NUMERO do atendimento", numero and numero in msg1,
      msg1[:200])
check("C1: e o nome da loja que o portal atribuiu",
      (d1.get("loja") or {}).get("nome", "@@") in msg1)
check("C1: e o endereco dela", (d1.get("loja") or {}).get("endereco", "@@") in msg1)
check("C1: e o aviso antifraude sobre a franquia",
      "franquia" in msg1.lower()
      and ("deposito" in msg1.lower() or "depósito" in msg1.lower()), msg1[-400:])
check("C1: e NENHUMA loja inventada — so a que veio do portal",
      msg1.count("Loja") <= 3 and "lojas proximas" not in msg1.lower())
check("C1: a mensagem proibe reabrir o pedido",
      "de novo" in msg1.lower() or "segundo" in msg1.lower(), msg1[-200:])

# ==========================================================================
print("\n[C2] LATARIA — 'amassei a porta e o paralama' atravessa a costura")
# ==========================================================================
# 🔴 Esta frase é o caso que a fatia C não conseguia classificar e que o
# catálogo não contém: ela vira família `lataria` no vocabulário único e, só
# então, `REPARO DE LATARIA E PINTURA` no catálogo daquela apólice.
c2 = costurar("LAT", peca="amassei a porta e o paralama",
              # 🔴 As palavras que a PRÓPRIA pergunta da fatia C ensina o agente
              # a devolver (`{"pecas_lataria": ["porta dianteira esquerda",
              # "paralama esquerdo"]}`). 📊 O catálogo escreve `PORTA DT
              # ESQUERDA` e `PARALAMAS DT ESQUERDO` — e por continência pura
              # NENHUMA das duas casava.
              extras={"pecas_lataria": ["paralama esquerdo", "capô"],
                      "lataria_mesmo_evento": "sim",
                      "onde_realizar_o_servico": "levar na oficina"})
check("C2: `build_portal_params` aceitou o payload", c2["erro"] is None, c2["erro"])
check("C2: a familia virou LATARIA, e nao vidro lateral",
      (c2["params"] or {}).get("dano", {}).get("peca") == "amassei a porta e o paralama"
      and (c2["evidence"].get("peca") or {}).get("categoria") == "L",
      c2["evidence"].get("peca"))
check("C2: e a peca do catalogo e a da lataria",
      (c2["evidence"].get("peca") or {}).get("descricao") == c2["catalogo"]["item"],
      (c2["evidence"].get("peca") or {}).get("descricao"))
check("C2: as pecas amassadas viajaram no PATCH",
      len(((c2["page"].corpo_de("PATCH", "/atendimentos") or {})
           .get("ServicosMartelinhoLataria") or [])) == 2,
      (c2["page"].corpo_de("PATCH", "/atendimentos") or {}).get("ServicosMartelinhoLataria"))
# 🔴 E são os MESMOS códigos que o portal recebeu — palavras de gente entraram,
# códigos de catálogo saíram.
check("C2: e com os CODIGOS de servico que o portal recebeu",
      sorted(s.get("CodigoServico") for s in
             (c2["page"].corpo_de("PATCH", "/atendimentos") or {})
             .get("ServicosMartelinhoLataria") or [])
      == sorted(s.get("CodigoServico") for s in
                (RV.primeira(RV.carregar("LAT"), "PATCH", "/atendimentos",
                             requisicao=True) or {})
                .get("ServicosMartelinhoLataria") or []),
      (c2["page"].corpo_de("PATCH", "/atendimentos") or {}).get("ServicosMartelinhoLataria"))
check("C2: o job chegou ao fim (`done`)",
      getattr(c2["resultado"], "status", "") == "done",
      getattr(c2["resultado"], "message", ""))
check("C2: com desfecho de loja direta",
      (c2["evidence"].get("desfecho") or {}).get("tipo") == ST.DESFECHO_LOJA_DIRETA)
msg2 = c2["mensagem"]
check("C2: a mensagem traz o numero do atendimento",
      str(c2["evidence"].get("protocolo") or "") in msg2, msg2[:160])
check("C2: e nao promete agenda nenhuma (o portal nao ofereceu)",
      "dia" not in msg2.lower().split("franquia")[0][:400]
      or "agendar" in msg2.lower(), msg2[:300])

# ==========================================================================
print("\n[C3] A costura CONSEGUE quebrar — o par de controle do gate")
# ==========================================================================
# 🔴 A mutação: renomear `cidade_servico` SÓ do lado de C. É a quebra de costura
# mais barata de cometer (um `rename` bem-intencionado) e a mais cara de achar,
# porque os dois lados continuam verdes sozinhos.
c3 = costurar("NOVO", peca="para-brisa", extras=DO_SEGURADO_PARABRISA,
              renomear_cidade=True)
check("C3 MUTACAO: renomeando a chave so do lado de C, o pedido NAO sai",
      getattr(c3["resultado"], "status", None) != "done", c3["resultado"])
check("C3 MUTACAO: e NENHUMA escrita foi emitida",
      c3["page"].escritas() == [], c3["page"].escritas())
check("C3 CONTROLE: com a chave certa, o mesmo payload foi ate o fim — DIFEREM",
      getattr(c1["resultado"], "status", "") == "done")

# ==========================================================================
print("\n[C4] sem a CIDADE DO SERVICO, o job nem nasce")
# ==========================================================================
chamadas4 = RV.carregar("NOVO")
profile4, infocap4, catalogo4 = bordas_do_har(chamadas4)
# 🔴 O par isola a CIDADE: os dois payloads são idênticos em tudo o mais — as
# mesmas respostas do segurado, a mesma apólice, a mesma peça. Só a cidade sai.
sem_cidade = {k: v for k, v in DO_SEGURADO_PARABRISA.items()}
flat4 = {"cpf_cnpj": infocap4["client"]["cpf_cnpj"], "data_dano": catalogo4["data"],
         "peca": "para-brisa", "onde_ocorreu": "rodoviario",
         "como_ocorreu": catalogo4["motivo"], "especificos": sem_cidade}
p4, e4 = PP.build_portal_params(flat4, profile4, infocap4, enviar_de_verdade=True)
check("C4: sem `cidade_para_o_servico`, `build_portal_params` recusa",
      p4 is None and bool(e4), (p4 is not None, e4))
check("C4: e a recusa PERGUNTA a cidade, em portugues",
      "cidade" in str(e4).lower(), str(e4)[:200])
flat4b = {**flat4, "especificos": {**sem_cidade,
                                   "cidade_para_o_servico": catalogo4["cidade"]}}
p4b, e4b = PP.build_portal_params(flat4b, profile4, infocap4, enviar_de_verdade=True)
check("C4 CONTROLE: com ela, o job nasce — os dois casos DIFEREM",
      p4b is not None and e4b is None, e4b)

# ==========================================================================
print("\n[C5] o relato do segurado NAO casa a causa — e a parada e util")
# ==========================================================================
# 📊 Medido na costura: `"uma pedra bateu no vidro"` não casa com
# `"DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA"` por texto. Esta parada é
# INEVITÁVEL depois da fronteira A (a lista de causas só existe com token), e o
# que se exige dela é que ela seja ÚTIL: que venha com as opções reais e que a
# mensagem diga ao segurado o que perguntar.
c5 = costurar("NOVO", peca="para-brisa", como="uma pedra bateu no vidro",
              extras=DO_SEGURADO_PARABRISA)
check("C5: o motor parou em `motivo_ambiguo`",
      (c5["evidence"].get("stage")) == "motivo_ambiguo", c5["evidence"].get("stage"))
check("C5: o pedido JA EXISTE, e a evidencia prova",
      G.tem_prova_de_efeito(c5["evidence"]) is True)
check("C5: a parada trouxe as opcoes REAIS do portal",
      c5["catalogo"]["motivo"] in (c5["evidence"].get("opcoes") or []),
      (c5["evidence"].get("opcoes") or [])[:3])
check("C5: e a mensagem ao atendente traz essas opcoes",
      c5["catalogo"]["motivo"] in c5["mensagem"], c5["mensagem"][:300])
check("C5: a mensagem NAO diz que o pedido falhou",
      "nao consegui abrir" not in c5["mensagem"].lower(), c5["mensagem"][:200])
check("C5 CONTROLE: com a causa nas palavras do portal, o mesmo payload conclui",
      getattr(c1["resultado"], "status", "") == "done")

# ==========================================================================
print("\n[C6] `onde ocorreu` que nao classifica NAO vira 'Nao Sabe'")
# ==========================================================================
# 🔴 O defeito da classe §9.5: `str("na cidade")[:1].upper()` == `"N"`, e `N` é
# **"Não Sabe"** para o portal — um passo que responde ERRADO e não trava.
from portal_worker.journeys import vidros_api as API  # noqa: E402

check("C6: 'urbano' e 'rodoviario' (o que a pergunta oferece) classificam",
      API.perimetro_do_texto("urbano") == "U"
      and API.perimetro_do_texto("rodoviario") == "R")
check("C6: e a linguagem de gente tambem",
      API.perimetro_do_texto("estava na estrada") == "R"
      and API.perimetro_do_texto("na cidade") == "U"
      and API.perimetro_do_texto("no estacionamento do shopping") == "U")
check("C6: o que NAO classifica devolve vazio, nunca 'N'",
      API.perimetro_do_texto("sei la") == ""
      and API.perimetro_do_texto("xyz") == "", API.perimetro_do_texto("sei la"))
check("C6 CONTROLE: a regra antiga daria 'N' (= Nao Sabe) para 'na cidade'",
      "na cidade"[:1].upper() == "N")
c6 = costurar("NOVO", peca="para-brisa", extras=DO_SEGURADO_PARABRISA)
c6b = RV.carregar("NOVO")
profile6, infocap6, catalogo6 = bordas_do_har(c6b)
_base6 = {"cpf_cnpj": infocap6["client"]["cpf_cnpj"], "data_dano": catalogo6["data"],
          "peca": "para-brisa", "como_ocorreu": catalogo6["motivo"],
          "especificos": {"cidade_para_o_servico": catalogo6["cidade"],
                          **DO_SEGURADO_PARABRISA}}
# A fatia C já barra o "não sei" declarado — `e_nao_sabe` o reconhece.
p6_nao_sabe, e6_nao_sabe = PP.build_portal_params(
    {**_base6, "onde_ocorreu": "sei la"}, profile6, infocap6, enviar_de_verdade=True)
check("C6: 'sei la' nem chega a journey — a fatia C ja pergunta de novo",
      p6_nao_sabe is None and bool(e6_nao_sabe), e6_nao_sabe)
# 🔴 E o que PASSA por C e mesmo assim não classifica para o portal: é aqui que
# a antiga regra da primeira letra gravaria `"N"` = "Não Sabe" na seguradora.
flat6 = {**_base6, "onde_ocorreu": "no meio do nada"}
p6, _ = PP.build_portal_params(flat6, profile6, infocap6, enviar_de_verdade=True)
p6["_runtime"] = RuntimeDeReplay()
page6 = RV.PaginaDeReplay(c6b)
ev6: dict = {}
r6 = asyncio.run(AF.abrir_atendimento_api(page6, p6, ev6))
check("C6: com 'onde' que nao classifica, NENHUMA escrita sai",
      page6.escritas() == [], page6.escritas())
check("C6: e o motivo diz qual campo falta",
      any("onde" in f for f in (ev6.get("api_first") or {}).get("faltou") or []),
      (ev6.get("api_first") or {}).get("faltou"))
check("C6 CONTROLE: com 'rodoviario', o mesmo payload conclui — DIFEREM",
      getattr(c6["resultado"], "status", "") == "done")

# ==========================================================================
print("\n[C7] uma tabela so de seguradora, e ela tem as tres colunas")
# ==========================================================================
check("C7: a tabela local de `portal_params` MORREU",
      not hasattr(PP, "_INSURER_ALIASES") and not hasattr(PP, "_APELIDOS_VEM_DA_API"))
check("C7: e `normalize_insurer` le a tabela do `vidros_api`",
      bool(PP._apelidos_do_portal())
      and len(PP._apelidos_do_portal()) == len(API.apelidos_de_seguradora()))
check("C7: a tabela unica carrega (fragmento, slug, nome_de_tela)",
      all(len(t) == 3 for t in API.apelidos_de_seguradora()))
for legado, tela, slug in (("LIBERTY SEGUROS S/A", "Yelum", "LIBERTY"),
                           ("LIBE", "Yelum", "LIBERTY"),
                           ("PORTO SEGURO CIA", "Porto Seguro", "PORTO"),
                           ("TOKIO MARINE SEGURADORA", "Tokio Marine", "TOKIOMARINE")):
    nome = PP.normalize_insurer(legado)
    vivos = RV.primeira(RV.carregar("NOVO"), "GET", "/seguradoras/") or []
    achado = API.resolver_seguradora(nome, vivos)
    check(f"C7: {legado!r} → tela {tela!r} → slug {slug!r} (a volta inteira)",
          nome == tela and achado and achado["slug"] == slug, (nome, achado))
check("C7: seguradora desconhecida continua caindo no `.title()`",
      PP.normalize_insurer("ESSOR") == "Essor")

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)
