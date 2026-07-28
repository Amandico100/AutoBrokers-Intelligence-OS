"""A corretora vê o tamanho do cérebro, nunca o conteúdo dele. SPEC-036/052.

A regra do Founder, 28/07/2026
-----------------------------
> "AS CORRETORAS NAO PODEM TER ACESSO A INTELIGENCIA, MAS DEVEM VER QUE TEM O
>  CONTEUDO, AS PASTAS, SEM ACESSO A INTELIGENCIA GLOBAL. A INTELIGENCIA
>  GLOBAL É SÓ USADA PELO SISTEMA. MAS DEVEM FICAR VISIVEIS AS PASTAS COM OS
>  NOMES DAS PASTAS PARA QUE ELES VEJAM QUE EXISTE UM CEREBRO GIGANTE
>  EXECUTANDO TUDO."

São duas exigências opostas na mesma tela, e é por isso que este teste existe:
mostrar de menos esconde o produto, mostrar de mais entrega a inteligência.

O que a tela mostrava
---------------------
Nada. A camada global lia só `documents` da empresa técnica global — que tem
**zero** linhas. Enquanto isso a inteligência real existia e era invisível:

    926 cartas de procedimento em curadoria   (auto 375 · outro 287 ·
                                               residencial 219 · vida 45)
      9 mapas de rota ativos                  (porto 4 · allianz · hdi ·
                                               yelum · zurich · tokio)

O perigo de consertar isso
--------------------------
`ura_maps.map` tem a árvore inteira da URA. `knowledge_cards.card_text` tem o
procedimento escrito. O `file_name` de um documento da biblioteca já é
conteúdo ("Manual de sinistro Porto 2026.pdf" entrega o acervo).

E `knowledge_cards.insurer_key` está sujo: existem valores como
`porto/tokio/resulta` — o nome de uma CORRETORA dentro de uma chave que seria
exibida como pasta global para as outras corretoras.

Por isso o corte é por lista de permissão: só `insurer_key` de `ura_maps`
(vocabulário controlado), só `ramo` de `knowledge_cards`, só
`knowledge_class` de `documents`. Contagem e nome de pasta. Nada mais.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROTA = os.path.join(RAIZ, "app", "api", "dashboard", "memorias", "route.ts")
PAGINA = os.path.join(RAIZ, "app", "dashboard", "memorias", "page.tsx")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    sem_bloco = re.sub(r"/\*(?:.|\n)*?\*/", "", fonte)
    return "\n".join(l for l in sem_bloco.split("\n") if not l.lstrip().startswith("//"))


def _select_de(fonte: str, tabela: str) -> str:
    """O que a consulta daquela tabela pede ao banco."""
    m = re.search(r"from\(['\"]" + re.escape(tabela) + r"['\"]\)\s*\.select\(([^)]*)\)", fonte)
    return m.group(1) if m else ""


def teste_a_rota_existe_e_exige_sessao():
    print("\n[1] Só quem é da corretora abre esta rota")
    fonte = _sem_comentario(_ler(ROTA))
    checar("requireCompanyMember" in fonte, "a rota exige membro de corretora")
    checar("auth.ok" in fonte and "auth.status" in fonte,
           "e recusa antes de consultar qualquer coisa")


def teste_o_mapa_da_ura_nunca_sai():
    print("\n[2] `ura_maps.map` é a árvore inteira da URA — não sai daqui")
    fonte = _sem_comentario(_ler(ROTA))
    sel = _select_de(fonte, "ura_maps")
    checar(bool(sel), "a rota consulta os mapas para contar as pastas")
    checar("map" not in re.sub(r"insurer_key|ura_maps", "", sel),
           "e NÃO pede a coluna `map`", sel)
    checar("insurer_key" in sel, "pede só a chave da seguradora", sel)


def teste_o_texto_da_carta_nunca_sai():
    print("\n[3] `knowledge_cards.card_text` é o procedimento escrito")
    fonte = _sem_comentario(_ler(ROTA))
    sel = _select_de(fonte, "knowledge_cards")
    checar(bool(sel), "a rota consulta as cartas para contar as pastas")
    checar("card_text" not in sel, "e NÃO pede o texto da carta", sel)
    checar("ramo" in sel, "pede só o ramo", sel)
    # Cartas barradas por PII não entram nem na contagem.
    # Passou de `neq('rejected_pii')` para uma LISTA de permissão. Existem
    # quatro status agora e só dois são conhecimento vivo: `superseded` são as
    # quase-cópias que a curadoria juntou, `rejected_pii` e
    # `rejected_absoluto` foram barradas. Excluir uma a uma erra no dia em que
    # nascer o quinto status — permitir explicitamente, não.
    checar("'pending_review', 'published'" in fonte,
           "só o conhecimento vivo é contado",
           "lista de permissão, não de exclusão")
    checar("rejected" not in _select_de(fonte, "knowledge_cards"),
           "e a carta barrada por PII não entra nem na contagem")


def teste_o_nome_do_documento_global_ja_e_conteudo():
    print("\n[4] O nome do arquivo da biblioteca também é conteúdo")
    # "Manual de sinistro Porto 2026.pdf" entrega o acervo sem abrir o acervo.
    # A consulta da CORRETORA pede `file_name` por dever de ofício e fica logo
    # acima. Uma janela de caracteres pega a vizinha e dá alarme falso — o
    # recorte tem de ser a consulta inteira, do `from(` até o `GK_COMPANY_ID`.
    fonte = _sem_comentario(_ler(ROTA))
    consultas = [f"sb.from({p}" for p in fonte.split("sb.from(")[1:]]
    do_acervo = [c for c in consultas if "GK_COMPANY_ID" in c.split(".limit(")[0]]
    checar(len(do_acervo) == 1, "a consulta do acervo global existe, e é uma só",
           f"achou {len(do_acervo)}")
    consulta = do_acervo[0].split(".limit(")[0] if do_acervo else ""
    checar("file_name" not in consulta,
           "e não pede `file_name`", consulta)
    checar("knowledge_class" in consulta, "pede só a classe, que vira nome de pasta")


def teste_nome_de_corretora_nao_vira_pasta_global():
    print("\n[5] O nome de uma corretora nunca vira pasta global")
    # `knowledge_cards.insurer_key` tem sujeira de extração: `porto/tokio/resulta`
    # e `technical__hdi` estão lá. Exibir isso mostraria a UMA corretora que
    # OUTRA é cliente.
    fonte = _sem_comentario(_ler(ROTA))
    checar("insurer_key" not in _select_de(fonte, "knowledge_cards"),
           "as pastas de procedimento não usam `insurer_key` das cartas",
           "é onde está a sujeira com nome de corretora")
    checar("includes('__')" in fonte or 'includes("__")' in fonte,
           "chaves técnicas (`technical__hdi`) são descartadas")
    checar("includes('/')" in fonte or 'includes("/")' in fonte,
           "chaves compostas (`porto/tokio/resulta`) são descartadas")


def teste_a_corretora_ve_as_pastas_e_o_volume():
    print("\n[6] E precisa VER o cérebro — senão o produto some")
    fonte = _sem_comentario(_ler(ROTA))
    checar("pastasGlobais" in fonte, "as pastas globais são montadas")
    checar("global_total" in fonte,
           "e o total VERDADEIRO viaja para o cabeçalho",
           "o grafo desenha no máximo 24 por pasta; dizer 52 quando há 987 "
           "vende o cérebro por menos do que ele é")
    checar("locked: true" in fonte, "todo item global vai marcado como trancado")

    pagina = _sem_comentario(_ler(PAGINA))
    checar("global_total" in pagina, "e a tela usa esse total, não o desenhado")
    checar("sel.locked ?" in pagina,
           "o painel trata o nó trancado de forma diferente")


def teste_o_no_trancado_nao_tem_atalho_para_o_conteudo():
    print("\n[7] Nó trancado não abre caminho para o conteúdo")
    pagina = _sem_comentario(_ler(PAGINA))
    i = pagina.find("sel.locked ?")
    j = pagina.find("Conexões", i) if i >= 0 else -1
    bloco = pagina[i:j] if i >= 0 and j > i else ""
    checar(bool(bloco), "o painel de detalhe do nó trancado existe")
    # O ramo trancado do ternário vem ANTES do ramo normal: o link para o chat
    # só pode estar no ramo de baixo.
    ramo_trancado = bloco.split(") : (")[0] if ") : (" in bloco else bloco
    checar("/dashboard/chat" not in ramo_trancado,
           "e ele NÃO oferece o atalho de perguntar sobre o conteúdo",
           "o rótulo é mascarado: a pergunta sairia sem sentido e o atalho "
           "sugeriria um acesso que não existe")
    checar("protegido" in ramo_trancado.lower(),
           "diz claramente que o conteúdo é protegido")


def main() -> int:
    print("=" * 70)
    print("A CORRETORA VÊ O TAMANHO DO CÉREBRO, NUNCA O CONTEÚDO DELE")
    print("=" * 70)
    for teste in (teste_a_rota_existe_e_exige_sessao,
                  teste_o_mapa_da_ura_nunca_sai,
                  teste_o_texto_da_carta_nunca_sai,
                  teste_o_nome_do_documento_global_ja_e_conteudo,
                  teste_nome_de_corretora_nao_vira_pasta_global,
                  teste_a_corretora_ve_as_pastas_e_o_volume,
                  teste_o_no_trancado_nao_tem_atalho_para_o_conteudo):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("AS PASTAS APARECEM; A INTELIGÊNCIA FICA COM O SISTEMA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
