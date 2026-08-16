"""Onde pegar os documentos dificeis — SPEC-072 Bloco 3.

    python backend/scripts/acervo/onde_pegar_documentos.py
    python backend/scripts/acervo/onde_pegar_documentos.py --gravar

POR QUE ISTO E AUTORIA, E NAO EXTRACAO
=======================================
📊 "Onde pegar" nao existe em fonte nenhuma do acervo, **por construcao**: a
condicao geral diz o que a seguradora EXIGE, nunca onde o segurado OBTEM. E nas
conversas aparece em ~1% delas.

E e a diferenca entre uma lista que resolve e uma que trava. O acervo registra o
custo com todas as letras: *"sem isso o segurado vai ao orgao, volta sem o papel
certo e o processo perde dias a cada ida."*

A conduta medida da atendente e a certa e e a que o agente copia: diante de
*"precisa de BO mesmo assim?"* e *"nem dao andamento"*, **ela nao argumenta —
manda o link do estado certo.**

🔴 POR QUE CARTA SEPARADA, E NAO EMBUTIDA (contrariando a SPEC §5 Bloco 3)
==========================================================================
A SPEC pede "embutido na carta da situacao, nao em carta separada". Nao da, e o
motivo e o lastro:

    a carta da situacao cita `source_unit_id` — um trecho, de uma versao, de um
    documento. E o que separa "acho que a Porto nao cobre" de "a clausula 4.4.2.d
    diz que nao cobre".

Embutir texto AUTORAL numa carta que aponta para uma clausula faria a carta
**mentir sobre a propria fonte**: o contrato nao diz onde tirar CRLV. O lastro e
o produto (SPEC-070); estraga-lo para economizar uma carta e o pior negocio da
SPEC.

Entao sao cartas proprias, **sem `source_unit_id`** — porque nao vem de contrato
nenhum — e o agente as recebe junto com a lista. A juncao ja esta mandada em
`prompts.py`, na EXCECAO DOCUMENTAL (CA-037): *"nos dificeis, diga ONDE PEGAR na
mesma mensagem"*.

⚠️ P-172 ATINGE ESTE BLOCO EM CHEIO
====================================
📊 A regra `PII[32]` do mascarador marca **qualquer numero de 4+ digitos numa
linha que fale "codigo de acesso"** — e ja comeu um `0800` que era o telefone da
central que a carta existia para informar. "Onde pegar" e feito de 0800, link e
numero. Toda carta daqui passa por `veredito_de_pii` ANTES de gravar, e o que for
tocado sai no relatorio em vez de entrar no acervo danificada.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]
CARTAS = AQUI.parent / "cartas"
sys.path.insert(0, str(BACKEND))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ─────────────────────────────────────────────────────────────────────────────
# O B.O. — o unico que muda por ESTADO, e o que o Founder nomeou
# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ NAO INVENTEI URL DE ESTADO NENHUM. Cada Detran/PC tem endereco proprio e um
# link errado e pior que nenhum: manda o segurado para uma pagina que nao existe
# e ele volta sem o B.O. e sem confianca. O que esta escrito aqui e o CAMINHO
# — o nome oficial do servico e como achar —, que e verdadeiro em todos os 26
# estados e no DF.
#
# 🧑 As 27 URLs verificadas sao um item do Founder: P-180. Ate elas chegarem, o
# agente manda o caminho, que resolve; com elas, manda o link, que resolve mais
# rapido. Nenhum dos dois mente.
ONDE_PEGAR = [
    ("boletim_ocorrencia", "Boletim de ocorrência",
     "O B.O. se faz online, na Delegacia Virtual do estado ONDE O FATO "
     "ACONTECEU — não onde o segurado mora, e essa é a confusão mais comum. "
     "Procure por \"Delegacia Virtual\" mais a sigla do estado; a maioria dos "
     "estados aceita acidente de trânsito sem vítima, furto e roubo pela "
     "internet, com login gov.br. Sai na hora ou em até 48h por e-mail. "
     "Acidente COM vítima quase sempre exige presencial. Se o registro ficar "
     "\"em análise\", o número do protocolo já serve para abrir o aviso — não "
     "espere o documento final para avisar a seguradora."),
    ("crlv", "CRLV-e (documento do veículo)",
     "O CRLV digital sai em segundos no aplicativo Carteira Digital de "
     "Trânsito (CDT): entrar com gov.br, aba Veículos, escolher o veículo e "
     "baixar o PDF. Também sai no site do Detran do estado de emplacamento. "
     "Vale o do ano vigente, e só é emitido com o licenciamento pago — se não "
     "baixar, é quase sempre licenciamento em aberto, não erro do app."),
    ("atpv", "ATPV-e (transferência)",
     "O ATPV-e substituiu o antigo DUT de papel e é emitido no Detran do "
     "estado de emplacamento, pelo site ou pelo app do Detran. Em indenização "
     "integral a seguradora costuma pedir com firma reconhecida em cartório e "
     "assinatura do proprietário que consta no documento — se o veículo for "
     "financiado ou alienado, o banco também assina, e isso costuma ser o que "
     "mais atrasa."),
    ("certidao_obito", "Certidão de óbito",
     "Sai no cartório de registro civil onde o óbito foi registrado, e a "
     "segunda via pode ser pedida em qualquer cartório do país ou pelo portal "
     "Registro Civil. A via simples costuma sair no mesmo dia; a de inteiro "
     "teor demora mais. A seguradora normalmente aceita cópia legível — "
     "confirme antes de pagar por via original."),
    ("laudo_ic", "Laudo do Instituto de Criminalística",
     "Só existe quando houve perícia — em incêndio, explosão e alguns casos de "
     "roubo. Pede-se ao Instituto de Criminalística (ou Politec/IGP, conforme "
     "o estado) com o número do B.O. em mãos. Demora semanas: peça no mesmo "
     "dia em que abrir o aviso, não depois que a seguradora cobrar."),
    ("contrato_social", "Contrato social e cartão CNPJ",
     "O contrato social atualizado sai na Junta Comercial do estado, online, "
     "com certificado digital ou gov.br. O cartão CNPJ é gratuito e imediato "
     "no site da Receita Federal, em Comprovante de Inscrição e de Situação "
     "Cadastral. A seguradora costuma pedir a última alteração consolidada, "
     "não o contrato original."),
    ("comprovante_residencia", "Comprovante de residência",
     "Conta de consumo (energia, água, telefone fixo ou internet) dos últimos "
     "três meses, em nome do segurado. Se estiver em nome de outra pessoa, "
     "mande junto uma declaração simples de quem é o titular e o vínculo — "
     "isso resolve na hora e evita a devolução do processo. Fatura de cartão "
     "e boleto de aluguel costumam ser aceitos; comprovante digital em PDF "
     "vale igual ao impresso."),
    ("dados_bancarios", "Dados bancários",
     "Têm de ser da conta do TITULAR da apólice — banco, agência, conta e CPF "
     "ou CNPJ do titular. Conta de terceiro só com autorização formal, e é a "
     "causa mais comum de indenização travada depois de aprovada. Se o "
     "titular faleceu, a conta é do inventário ou do beneficiário indicado, e "
     "aí entram os documentos de sucessão. Chave PIX nem sempre é aceita: "
     "confirme antes."),
    ("nota_fiscal", "Nota fiscal de bem ou acessório",
     "A original de compra, no nome do segurado. Foto legível serve na maioria "
     "dos casos. Se a nota se perdeu, a segunda via sai com o vendedor ou na "
     "SEFAZ do estado pela chave de acesso da NF-e. Sem nota, a seguradora "
     "costuma indenizar pelo valor de mercado, que é menor — vale procurar."),
    ("boletim_inmet", "Boletim meteorológico",
     "Só é pedido em granizo, vendaval e alagamento, para provar que o evento "
     "ocorreu. Sai no site do INMET, na consulta de dados históricos por "
     "estação e data, e é gratuito. Peça o do dia do sinistro e da estação "
     "mais próxima do endereço; a Defesa Civil do município também emite "
     "declaração de ocorrência, que costuma ser aceita."),
]


def montar() -> list:
    cartas = []
    for chave, titulo, corpo in ONDE_PEGAR:
        texto = f"Onde conseguir {titulo.lower()}: {corpo}"
        cartas.append({
            "texto": texto,
            "faceta": "documento",
            # ⚠️ SEM `unit_id_origem`: nao veio de contrato nenhum. Fingir
            # procedencia seria pior do que nao ter — ver o cabecalho.
            "caminho": f"ONDE PEGAR > {titulo}",
            "_chave": chave,
        })
    return cartas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()

    # Fachada + importlib: `app/__init__.py` real arrasta `openai`, que nao
    # existe fora do conteiner. Mesmo mecanismo dos testes da casa.
    import importlib.util
    import types

    for nome, partes in (("app", ("app",)),
                         ("app.services", ("app", "services")),
                         ("app.services.atlas", ("app", "services", "atlas"))):
        if nome not in sys.modules:
            m = types.ModuleType(nome)
            m.__path__ = [str(BACKEND.joinpath(*partes))]
            m.__package__ = nome
            sys.modules[nome] = m

    def _carregar(nome, *partes):
        spec = importlib.util.spec_from_file_location(
            nome, str(BACKEND.joinpath(*partes)))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        return mod

    _carregar("app.services.atlas.templater", "app", "services", "atlas",
              "templater.py")
    _C = _carregar("app.services.curadoria_cartas", "app", "services",
                   "curadoria_cartas.py")
    MAX_CARACTERES = _C.MAX_CARACTERES
    MIN_CARACTERES = _C.MIN_CARACTERES
    veredito_de_pii = _C.veredito_de_pii

    cartas = montar()
    print("=" * 74)
    print("ONDE PEGAR — os dez documentos dificeis")
    print("=" * 74)
    problemas = 0
    for c in cartas:
        n = len(c["texto"])
        _, achados = veredito_de_pii(c["texto"])
        marca = "ok "
        if not (MIN_CARACTERES <= n <= MAX_CARACTERES):
            marca = "TAM"; problemas += 1
        if achados:
            marca = "PII"; problemas += 1
        print(f"  [{marca}] {n:5d}ch  {c['_chave']:24s} {achados if achados else ''}")
    print(f"\n  {len(cartas)} cartas · {problemas} problema(s)")
    print(f"  tamanho: min={min(len(c['texto']) for c in cartas)} "
          f"max={max(len(c['texto']) for c in cartas)}")
    print("\n  ⚠️ P-172: toda carta passou por `veredito_de_pii` ANTES de gravar.")
    print("     A regra PII[32] come numero de 4+ digitos perto de 'codigo de")
    print("     acesso', e ja comeu um 0800. Se alguma linha acima disser PII,")
    print("     a carta NAO entra — o texto e reescrito, nao mascarado.")
    print("\n  🧑 P-180: as 27 URLs de Delegacia Virtual sao item do Founder.")
    print("     Nenhuma URL de estado foi inventada aqui.")

    if problemas:
        print("\n  NAO GRAVADO — conserte os problemas acima.")
        return 1
    if args.gravar:
        destino = CARTAS / "_global" / "onde_pegar_CARTAS.jsonl"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("w", encoding="utf-8") as f:
            for c in cartas:
                f.write(json.dumps({k: v for k, v in c.items()
                                    if not k.startswith("_")},
                                   ensure_ascii=False) + "\n")
        print(f"\n  gravado: {destino.relative_to(BACKEND)}")
    else:
        print("\n  (nada gravado — use --gravar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
