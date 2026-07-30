"""Procura o que o templatize não sabe procurar: gente e endereço.

Por que o templatize não basta
------------------------------
O `templatize` casa PADRÃO — onze dígitos viram telefone, arroba vira e-mail,
três letras e quatro números viram placa. Nome de pessoa não tem padrão. "Maria
Silva" e "Porto Seguro" são a mesma coisa para uma expressão regular: duas
palavras capitalizadas.

E é justamente nome que o subagente pode ter deixado passar ao escrever a carta,
porque escrever "a Sra. Regina confirmou que..." parece natural quando você
acabou de ler a conversa inteira.

Então esta varredura usa o contrário de um padrão: usa CONTEXTO. Procura as
palavras que só aparecem perto de gente — tratamento, parentesco, papel — e o
vocabulário de endereço, que é fechado e pequeno.

O que ela devolve
-----------------
Candidatos, não condenados. "Sr." também aparece em "Sr. Corretor" e "Rua" em
"regra de ouro". A saída é para leitura humana, e o filtro final é o olho.

Uso
---
    python varrer_nomes.py
"""

from __future__ import annotations

import collections
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402

PAGINA = 1000

# Palavras capitalizadas que NÃO são gente. Sem esta lista, toda seguradora e
# todo estado viram suspeita e o relatório fica inútil.
NAO_E_GENTE = {
    "porto", "allianz", "azul", "tokio", "marine", "hdi", "youse", "yelum",
    "zurich", "liberty", "mapfre", "sompo", "bradesco", "itau", "sulamerica",
    "suhai", "aliro", "akad", "essor", "excelsior", "fairfax", "junto",
    "seguros", "seguradora", "corretora", "susep", "fenacor", "cnseg",
    "brasil", "sao", "paulo", "rio", "janeiro", "minas", "gerais", "bahia",
    "parana", "santa", "catarina", "grande", "sul", "norte", "goias",
    "espirito", "santo", "ceara", "pernambuco", "amazonas", "federal",
    "resulta", "autofleet", "whatsapp", "pix", "fipe", "detran", "iml",
    "cliente", "segurado", "atendente", "corretor", "perito", "regulador",
    "assistencia", "sinistro", "apolice", "cobertura", "franquia",
    "residencial", "condominio", "automovel", "vida", "empresarial",
    "codigo", "civil", "boletim", "ocorrencia", "nota", "fiscal",
}

# Contexto que denuncia gente: tratamento, parentesco, papel nominal.
PERTO_DE_GENTE = re.compile(
    r"(?i)\b(sr|sra|senhor|senhora|dona|dr|dra|segurad[oa]\s+|cliente\s+|"
    r"filh[oa]|espos[oa]|marido|mulher|mae|pai|irma[o]?|sobrinh[oa]|"
    r"cunhad[oa]|genr[o]|nora|viuv[ao]|benefici[áa]ri[oa]\s+|"
    r"condu[t]or\s+|proprietari[oa]\s+|s[óo]ci[oa]\s+|sindic[oa]\s+)"
    r"\.?\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,})")

ENDERECO = re.compile(
    r"(?i)\b(rua|avenida|av\.|alameda|travessa|rodovia|estrada|pra[çc]a|"
    r"condom[íi]nio|edif[íi]cio|resid[êe]ncial|bloco|apartamento|apto)\s+"
    r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-záéíóúâêôãõç]{2,}(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-z]+)*)")

# Nome completo solto: duas ou três capitalizadas seguidas.
NOME_SOLTO = re.compile(
    r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,})\s+"
    r"(?:(?:d[aeo]s?|e)\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]{2,})\b")


def _limpo(p: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", p.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def main() -> int:
    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)

    achados: dict = collections.defaultdict(list)
    lidas = 0
    de = 0
    while True:
        pagina = (db.table("knowledge_cards").select("id, card_text")
                  .eq("status", "published")
                  .order("id").range(de, de + PAGINA - 1).execute().data) or []
        if not pagina:
            break
        for c in pagina:
            lidas += 1
            t = c["card_text"] or ""

            for m in PERTO_DE_GENTE.finditer(t):
                if _limpo(m.group(2)) not in NAO_E_GENTE:
                    achados["gente (com tratamento ou parentesco)"].append((c["id"], m.group(0), t))
                    break

            for m in ENDERECO.finditer(t):
                if _limpo(m.group(2).split()[0]) not in NAO_E_GENTE:
                    achados["endereco"].append((c["id"], m.group(0), t))
                    break

            for m in NOME_SOLTO.finditer(t):
                a, b = _limpo(m.group(1)), _limpo(m.group(2))
                if a not in NAO_E_GENTE and b not in NAO_E_GENTE:
                    achados["duas capitalizadas seguidas"].append((c["id"], m.group(0), t))
                    break
        de += PAGINA

    print(f"  {lidas} cartas publicadas lidas\n")
    for tipo, itens in sorted(achados.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tipo}: {len(itens)}")
        for _id, trecho, texto in itens[:14]:
            print(f"     «{trecho}»  ·  {texto[:88]}")
        if len(itens) > 14:
            print(f"     ... e mais {len(itens) - 14}")
        print()
    if not achados:
        print("  nada encontrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
