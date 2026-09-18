# -*- coding: utf-8 -*-
r"""🔴 M-B4 · O PLANO VEM DA APÓLICE, NUNCA DO CHUTE.

SPEC-EXTRA-001.5 · §6.1 ③. *"③ é onde a resposta pode mentir com mais
confiança."* Se a seguradora tem três planos publicados e não se sabe qual é o
DELE, a tentação é responder pelo nível 1 — *"é o mais comum"*. Isso produz uma
resposta com fonte, com página, com cara de certa, e **sobre o contrato de
outra pessoa**.

```
estado_do_plano != 'contratado'   ->  nao_sabemos_ainda
plano ausente                     ->  nao_sabemos_ainda
```

📊 E não é hipótese: `_plano_do_pack` (`infocap_policy_provider.py:273-287`)
devolve HOJE, em produção, `estado="nao_sabemos_ainda"` para toda apólice —
porque `tabela_itens` dá o NOME do plano e nada mais. *Nome sem lista de
serviços não é "contratado"*, diz o docstring de `PlanoDeAssistencia`. Esta
Skill LÊ esse estado; não o recria (CLAUDE.md §5).

⚠️ E o par de controle importa mais que a asserção: a MESMA base, com o plano
identificado, responde. Sem ele, um motor que respondesse sempre
`nao_sabemos_ainda` passaria neste guarda.
"""
from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "tests"))

from base_de_planos_em_memoria import BaseEmMemoria  # noqa: E402

from app.providers.policy_data_provider import PlanoDeAssistencia  # noqa: E402
from app.services.skills.cobertura_e_assistencia import responder_cobertura  # noqa: E402

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


# A seguradora tem TRÊS planos publicados, e o de nível 1 cobre o serviço. É a
# armadilha: chutar o nível 1 daria "sim, tem", com fonte e página.
db = BaseEmMemoria()
N1 = db.plano(insurer_key="tokio", ramo="auto", produto="Auto Perfil",
              plano="Basico", nivel=1, documento_id="doc-tokio", pagina=5)
N2 = db.plano(insurer_key="tokio", ramo="auto", produto="Auto Perfil",
              plano="Intermediario", nivel=2, documento_id="doc-tokio", pagina=5)
N3 = db.plano(insurer_key="tokio", ramo="auto", produto="Auto Perfil",
              plano="Master", nivel=3, documento_id="doc-tokio", pagina=5)
for pid, pagina in ((N1, 21), (N2, 22), (N3, 23)):
    db.servico(pid, "carro_reserva", "sim", documento_id="doc-tokio", pagina=pagina,
               limite_valor=7, limite_unidade="dias")

PERGUNTA = "tem carro reserva?"
BASE = {"insurer": "Tokio Marine", "ramo": "auto", "produto": "Auto Perfil"}

print("\n[1] 📊 o estado que a PORTA devolve hoje, em produção")
hoje = PlanoDeAssistencia.__dataclass_fields__["estado"].default
checar(hoje == "nao_sabemos_ainda",
       "🔴 `PlanoDeAssistencia.estado` nasce `nao_sabemos_ainda` na porta — "
       "é DESSE estado que a Skill parte, e não de um padrão inventado aqui",
       repr(hoje))

print("\n[2] plano NÃO identificado (estado != contratado) -> nao_sabemos_ainda")
for rotulo, apolice in (
    ("nome do plano ausente",
     {**BASE, "plano": None, "nivel": None, "estado_do_plano": "nao_sabemos_ainda"}),
    ("nome presente, mas o ESTADO diz que não sabemos",
     {**BASE, "plano": "Basico", "nivel": 1, "estado_do_plano": "nao_sabemos_ainda"}),
    ("plano explicitamente NÃO contratado",
     {**BASE, "plano": "Master", "nivel": 3, "estado_do_plano": "nao_contratado"}),
):
    v = responder_cobertura(pergunta=PERGUNTA, apolice=apolice, db=db)
    checar(v is not None and v.estado == "nao_sabemos_ainda",
           f"🔴 {rotulo} -> `nao_sabemos_ainda`", repr(getattr(v, "estado", None)))
    checar(v is not None and v.plano_id is None and v.pagina is None,
           f"   e {rotulo}: NENHUM plano da base foi adotado (plano_id e pagina vazios)",
           repr((getattr(v, "plano_id", "?"), getattr(v, "pagina", "?"))))
    checar(v is not None and "Basico" not in v.texto and "nível 1" not in v.texto,
           "   🔴 e o texto NÃO nomeia o plano de nível 1 como se fosse o dele",
           getattr(v, "texto", ""))

print("\n[3] a Skill nem CONSULTA a base quando o plano é desconhecido")
sem_consulta = BaseEmMemoria()
sem_consulta.plano(insurer_key="tokio", ramo="auto", produto="Auto Perfil",
                   plano="Basico", nivel=1)
sem_consulta.chamadas_de_tabela.clear()
responder_cobertura(pergunta=PERGUNTA, db=sem_consulta,
                    apolice={**BASE, "plano": None, "estado_do_plano": "nao_sabemos_ainda"})
checar(sem_consulta.chamadas_de_tabela == [],
       "🔴 zero consultas — não há como 'escolher o plano mais provável' se a "
       "lista nem foi lida", repr(sem_consulta.chamadas_de_tabela))

print("\n[4] 🔴 O PAR DE CONTROLE: com o plano identificado, a MESMA base responde")
v_ok = responder_cobertura(
    pergunta=PERGUNTA, db=db,
    apolice={**BASE, "plano": "Intermediario", "nivel": 2, "estado_do_plano": "contratado"})
checar(v_ok is not None and v_ok.estado == "coberto",
       "🔴 CONTROLE: plano identificado -> `coberto`. O motor CONSEGUE responder",
       repr(getattr(v_ok, "estado", None)))
checar(v_ok is not None and int(v_ok.pagina) == 22,
       "🔴 e a página é a do plano DELE (22 = Intermediario), não a do nível 1 (21)",
       repr(getattr(v_ok, "pagina", None)))
checar(v_ok is not None and v_ok.plano == "Intermediario",
       "e o plano citado é o que veio da apólice", repr(getattr(v_ok, "plano", None)))

print("\n[5] seguradora fora do censo também é lacuna, não 'não'")
v_desc = responder_cobertura(
    pergunta=PERGUNTA, db=db,
    apolice={"insurer": "Seguradora XYZ Ltda", "ramo": "auto", "produto": "Auto Perfil",
             "plano": "Basico", "nivel": 1, "estado_do_plano": "contratado"})
checar(v_desc is not None and v_desc.estado == "nao_sabemos_ainda",
       "🔴 seguradora desconhecida -> `nao_sabemos_ainda` (nunca uma chave-lixo "
       "gravada, nunca um 'não')", repr(getattr(v_desc, "estado", None)))
checar(v_desc is not None and v_desc.insurer_key is None,
       "e nenhuma chave canônica é afirmada para ela",
       repr(getattr(v_desc, "insurer_key", "?")))

print("\n[5] 🔴 O PLANO ÚNICO DA CONDIÇÃO GERAL — e as três travas que o seguram")
# 📊 18/09/2026: **25 dos 38** planos propostos chamam-se "Plano único", porque a
# condição geral não nomeia pacote nenhum. Exigir o nome no texto da apólice faz
# esses 25 nunca casarem — a base publicada fica invisível ao segurado.
# A regra só vale com as TRÊS travas juntas, e é isso que este bloco mede.
from app.services.skills.cobertura_e_assistencia import identificar_plano  # noqa: E402

DOCCG = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
db5 = BaseEmMemoria()
p5 = db5.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Plano único",
               nivel=1, documento_id=DOCCG)
achado = identificar_plano(insurer_key="hdi", ramo="auto", produto="Auto Total",
                           texto_do_documento="APOLICE AUTO sem nome de pacote",
                           documento_da_condicao=DOCCG, db=db5)
checar(achado.get("estado") == "contratado"
       and achado.get("origem") == "plano_unico_da_condicao_geral",
       "🔴 UM plano publicado + condição geral casada pelo SUSEP -> contratado, "
       "com a origem dizendo por quê", repr(achado))

# 🔴 CONTROLE ①: o MESMO plano, mas o SUSEP não casou -> não sabemos.
sem_susep = identificar_plano(insurer_key="hdi", ramo="auto", produto="Auto Total",
                              texto_do_documento="APOLICE AUTO sem nome de pacote",
                              documento_da_condicao=None, db=db5)
checar(sem_susep.get("estado") == "nao_sabemos_ainda",
       "🔴 CONTROLE: um plano só, mas SEM o elo SUSEP -> `nao_sabemos_ainda`",
       repr(sem_susep))

# 🔴 CONTROLE ②: dois planos publicados, mesmo com o SUSEP casado -> não sabemos.
db5.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Premium",
          nivel=2, documento_id=DOCCG)
dois = identificar_plano(insurer_key="hdi", ramo="auto", produto="Auto Total",
                         texto_do_documento="APOLICE AUTO sem nome de pacote",
                         documento_da_condicao=DOCCG, db=db5)
checar(dois.get("estado") == "nao_sabemos_ainda",
       "🔴 CONTROLE: com DOIS planos publicados, escolher seria adivinhar -> não escolhe",
       repr(dois))

# 🔴 CONTROLE ③: um plano só e SUSEP casado, mas de OUTRO documento.
db6 = BaseEmMemoria()
db6.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Plano único",
          nivel=1, documento_id="ffffffff-0000-0000-0000-000000000000")
outro = identificar_plano(insurer_key="hdi", ramo="auto", produto="Auto Total",
                          texto_do_documento="APOLICE AUTO", documento_da_condicao=DOCCG,
                          db=db6)
checar(outro.get("estado") == "nao_sabemos_ainda",
       "🔴 CONTROLE: o plano publicado veio de OUTRO documento -> não sabemos")

print("\n[6] DOIS planos NOMEADOS no mesmo texto não são um vencedor")
# 📊 "...plano Essencial contratado. Conheça também o Completo." — o nome mais
# LONGO vencia, e o segurado do Essencial recebia a cobertura do Completo.
db7 = BaseEmMemoria()
db7.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Essencial", nivel=1)
db7.plano(insurer_key="hdi", ramo="auto", produto="Auto Total", plano="Auto Completo", nivel=2)
um = identificar_plano(insurer_key="hdi", ramo="auto", produto="Auto Total",
                       texto_do_documento="Assistencia 24h - plano Essencial", db=db7)
checar(um.get("estado") == "contratado" and um.get("plano") == "Essencial",
       "UM nome no texto -> contratado, e é aquele", repr(um))
ambiguo = identificar_plano(
    insurer_key="hdi", ramo="auto", produto="Auto Total",
    texto_do_documento="plano Essencial contratado. Conheca tambem o Auto Completo.",
    db=db7)
checar(ambiguo.get("estado") == "nao_sabemos_ainda",
       "🔴 DOIS nomes no mesmo texto -> `nao_sabemos_ainda` (texto ambíguo é lacuna, "
       "não empate)", repr(ambiguo))

print("\n[7] o FALLBACK residencial responde SEM plano identificado (§6.4)")
# 📊 18/09/2026: o fallback só era alcançado depois da trava do plano, e a porta
# devolve `nao_sabemos_ainda` em 100 % dos casos reais — o caminho estava MORTO,
# e a 001.5 tinha tirado do ar uma resposta que a casa já dava.
apolice_res = {"insurer": "HDI", "ramo": "residencial", "produto": "Residencial",
               "estado_do_plano": "nao_sabemos_ainda", "residencial": True,
               "assistencia_confirmada": True}
v_eletricista = responder_cobertura(pergunta="a assistencia cobre eletricista?",
                                    apolice=apolice_res, db=BaseEmMemoria())
checar(v_eletricista is not None and v_eletricista.estado == "coberto"
       and v_eletricista.origem == "regra_generica" and v_eletricista.plano is None,
       "🔴 eletricista, sem plano identificado -> `coberto` MARCADO como genérico",
       repr(getattr(v_eletricista, "origem", None)))
checar(v_eletricista is not None and "padr" in v_eletricista.texto.lower()
       and "nao" not in v_eletricista.texto[:6].lower(),
       "e o texto diz que é padrão de mercado, não o contrato dele",
       v_eletricista.texto[:120])
# 🔴 CONTROLE: fora dos TRÊS serviços, o fallback NÃO responde.
v_reserva = responder_cobertura(pergunta="a assistencia cobre carro reserva?",
                                apolice=apolice_res, db=BaseEmMemoria())
checar(v_reserva is not None and v_reserva.estado == "nao_sabemos_ainda",
       "🔴 CONTROLE: carro reserva (fora dos três) -> `nao_sabemos_ainda`, nunca 'sim'",
       repr(v_reserva.estado))

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
