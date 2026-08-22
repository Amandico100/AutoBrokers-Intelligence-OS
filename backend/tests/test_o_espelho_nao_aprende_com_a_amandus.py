# -*- coding: utf-8 -*-
"""🔴 O LEITOR DO ESPELHO E AS DUAS TRAVAS — SPEC-084.1 FASE 0.5 / E8.

> ## Semear os apelidos com conversas FICTÍCIAS é a pior forma de furo coberto:
> a régua fica verde citando um cliente que não existe.

📊 A AMANDUS SEGUROS é a corretora de **teste**. As conversas dela são ensaios.
Se o leitor aprendesse com elas, `_SUBSERVICE_ALIASES` receberia vocabulário
inventado — e a E8 contaria isso como prova de que *"o cliente fala assim"*.

⚠️ 🔴 **E o motivo de a trava ser NOMEADA e não derivada está medido:**

```
📊 22/08/2026 — a AMANDUS está marcada `is_technical = False` no banco.
   Filtrar só as corretoras técnicas NÃO A EXCLUIRIA.
```

É o mesmo alerta que `canais_observados.py` já registra sobre outro leitor:
*"a env var que exclui a Amandus é do destilador e não cobriria isto"*.

O precedente vale porque **o C6 é exatamente outro leitor**.
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

import regua_motor as M   # noqa: E402

OK = 0
FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


print("=" * 74)
print("[1] AS DUAS TRAVAS DO LEITOR")
print("=" * 74)

# 🔴 A trava 2 é uma CONSTANTE NOMEADA, e tem de continuar sendo. Derivá-la de
#    `is_technical` seria perdê-la — ver o cabeçalho.
certo(hasattr(M, "_AMANDUS_COMPANY_ID") and M._AMANDUS_COMPANY_ID,
      "🔴 a exclusão da AMANDUS é uma constante NOMEADA no leitor",
      getattr(M, "_AMANDUS_COMPANY_ID", None))

if not M.tem_banco():
    print("\n  ⚠️ sem banco aqui — as provas de conteúdo abaixo não rodam.")
    print("     🔴 E isso NÃO é um passe: sem banco o leitor devolve [] e o")
    print("        item dos apelidos vale ZERO, nunca 4.")
    certo(M.vocabulario_do_espelho() == [],
          "sem banco, o leitor devolve VAZIO (e o item zera, não passa)")
else:
    cli = M.supabase()
    comp = {c["id"]: c for c in
            cli.table("companies").select("id,company_name,is_technical")
            .execute().data}
    amandus = comp.get(M._AMANDUS_COMPANY_ID)
    certo(amandus is not None,
          "o id nomeado existe mesmo na tabela `companies`")
    certo(bool(amandus) and "AMANDUS" in (amandus.get("company_name") or "").upper(),
          "🔴 e ele é MESMO a AMANDUS — não um id colado errado",
          (amandus or {}).get("company_name"))

    # 🔴 A LINHA QUE DÁ DIREITO À CONCLUSÃO, e ela é o motivo de o teste existir.
    certo(bool(amandus) and not amandus.get("is_technical"),
          "🔴 a AMANDUS NÃO está marcada `is_technical` — a trava derivada "
          "NÃO a excluiria, e por isso a nomeada é obrigatória",
          f"is_technical={(amandus or {}).get('is_technical')!r}")

    print()
    print("=" * 74)
    print("[2] O LEITOR NÃO LÊ A AMANDUS — provado por CONTRASTE")
    print("=" * 74)

    _conv_company = {c["id"]: c["company_id"] for c in
                     cli.table("conversations").select("id,company_id")
                     .limit(50000).execute().data}
    conv_amandus = [c["id"] for c in
                    cli.table("conversations").select("id,company_id")
                    .eq("company_id", M._AMANDUS_COMPANY_ID).execute().data]
    certo(len(conv_amandus) > 0,
          "📊 a AMANDUS TEM conversas no banco (senão o teste é vácuo)",
          f"{len(conv_amandus)} conversas")

    # as frases que SÓ existem nas conversas da Amandus
    frases_amandus = []
    for i in range(0, len(conv_amandus), 40):
        lote = conv_amandus[i:i + 40]
        frases_amandus += [
            M._norm(m.get("content") or "") for m in
            cli.table("messages").select("conversation_id,role,content")
            .in_("conversation_id", lote).eq("role", "user").execute().data]
    frases_amandus = [f for f in frases_amandus if len(f) >= 25]
    certo(len(frases_amandus) > 0,
          "📊 e ela tem mensagens de CLIENTE com texto utilizável",
          f"{len(frases_amandus)} mensagens >= 25 chars")

    espelho = M.vocabulario_do_espelho()
    certo(len(espelho) > 100,
          "📊 o leitor devolve volume real das corretoras VERDADEIRAS",
          f"{len(espelho)} mensagens")

    # 🔴 A PERGUNTA CERTA É DE PROCEDÊNCIA, NÃO DE CONTEÚDO.
    #
    # ⚠️ ESTA ASSERÇÃO NASCEU ERRADA DUAS VEZES, e a medição corrigiu as duas.
    #
    # **1ª:** exigia que NENHUMA frase existente em conversa da Amandus
    # aparecesse no vocabulário. 📊 Reprovou com 5 — e as 5 existem **também**
    # em conversa da Resulta Seguros: são mensagens de TRANSMISSÃO (link de
    # Instagram, lembrete de webinar) que caíram nas duas corretoras. Elas
    # entraram pelo lado da Resulta, que é real. **O leitor estava certo; a
    # asserção proibia coincidência de conteúdo em vez de vazamento.**
    #
    # **2ª:** montava o mapa texto→conversa SÓ com as conversas da Amandus, e
    # perguntava se ele cruzava com as reais. 🔴 Por construção nunca cruzava:
    # toda frase parecia exclusiva, e as mesmas 5 reprovavam de novo — agora
    # por um motivo diferente e igualmente errado.
    #
    # A pergunta que funciona precisa do mapa COMPLETO: em quais corretoras
    # cada texto existe. Só então "existe SÓ na Amandus" quer dizer alguma coisa.
    dono_do_texto = {}
    _i = 0
    while True:
        _p = (cli.table("messages").select("conversation_id,role,content")
              .eq("role", "user").range(_i, _i + 999).execute().data)
        if not _p:
            break
        for _m in _p:
            _c = _conv_company.get(_m.get("conversation_id"))
            if _c:
                dono_do_texto.setdefault(
                    M._norm(_m.get("content") or ""), set()).add(_c)
        if len(_p) < 1000:
            break
        _i += 1000

    so_da_amandus = [t for t in set(frases_amandus)
                     if dono_do_texto.get(t) == {M._AMANDUS_COMPANY_ID}]
    certo(len(so_da_amandus) > 0,
          "📊 há frases que existem SÓ na Amandus (senão o teste é vácuo)",
          f"{len(so_da_amandus)} frases exclusivas dela")
    vazaram = [f for f in so_da_amandus if f in espelho]
    certo(not vazaram,
          "🔴 NENHUMA frase EXCLUSIVA da AMANDUS entra no vocabulário",
          f"{len(vazaram)} vazaram; a 1ª: {vazaram[0][:70] if vazaram else ''}")

    # 🔴 E O CONTROLE QUE PROVA QUE O TESTE CONSEGUE ACUSAR: as frases que a
    #    Amandus COMPARTILHA com corretora real ESTÃO no vocabulário -- e é
    #    assim que tem de ser. Se esta linha ficar vazia, o leitor virou um
    #    filtro cego que apaga tudo que a Amandus toca.
    compartilhadas = [t for t in set(frases_amandus)
                      if M._AMANDUS_COMPANY_ID in dono_do_texto.get(t, set())
                      and len(dono_do_texto.get(t, set())) > 1]
    certo(any(t in espelho for t in compartilhadas),
          "🔴 CONTROLE: frase que a Amandus COMPARTILHA com corretora real "
          "CONTINUA no vocabulário — o filtro é por PROCEDÊNCIA, não censura",
          f"{len(compartilhadas)} compartilhadas")

    print()
    print("=" * 74)
    print("[3] O ITEM CONFERE, NÃO CONTA")
    print("=" * 74)

    # 📊 A armadilha que a E8 nomeia: "lavadora" marca 23x no CORPUS da Allianz
    #    porque a URA escreve "Lavadora de louças" — outro eletrodoméstico.
    #    O Espelho é outra fonte, e é a certa.
    pb = M.get_playbook("allianz-residencial-whatsapp@v1")
    apelidos = [k for k, v in (M.CP._SUBSERVICE_ALIASES or {}).items()
                if v == "maquina_de_lavar"]
    conf = M.apelidos_conferidos("maquina_de_lavar", apelidos)
    vivos = {a: n for a, n in conf.items() if n}
    certo(len(apelidos) > len(vivos),
          "🔴 declarar NÃO é conferir: há apelidos no código que o cliente "
          "NUNCA escreveu",
          f"{len(apelidos)} declarados, {len(vivos)} conferidos")
    certo(len(vivos) >= 3,
          "📊 e a rota de referência tem >=3 apelidos CONFERIDOS",
          sorted(vivos.items(), key=lambda kv: -kv[1]))

    # 🔴 CONTROLE NEGATIVO: um apelido inventado NÃO pode ser conferido.
    inventado = "trambolho que lava roupa do capiroto"
    certo(M.apelidos_conferidos("maquina_de_lavar", [inventado])[inventado] == 0,
          "🔴 CONTROLE: um apelido INVENTADO conta ZERO no Espelho")

    # 🔴 E o controle de COLISÃO da E8 tem de conseguir disparar.
    colide = M.apelido_colide("eletricista", "maquina_de_lavar", pb)
    certo(colide == "eletricista",
          "🔴 CONTROLE: o detector de colisão CONSEGUE acusar — um apelido "
          "que é o nome de outro serviço do mesmo menu",
          f"devolveu {colide!r}")
    certo(M.apelido_colide("maquina de lavar", "maquina_de_lavar", pb) is None,
          "🔴 CONTROLE: e NÃO acusa o apelido legítimo da própria rota")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
