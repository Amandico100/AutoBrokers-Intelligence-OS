# -*- coding: utf-8 -*-
"""Ciclo de vida do atendimento — as DUAS fronteiras materiais, medidas.

ORIGEM (YELUM har, captura 2026-08-15)
--------------------------------------
RESPOSTA_POST_ATENDIMENTOS ... POST /atendimentos              entry 128 (200)
ATENDIMENTO_PRE_QUESTIONARIO . GET  /atendimentos              entry 135 — CodigoAtendimento **null**
ATENDIMENTO_COM_FRANQUIA ..... GET  /atendimentos              entry 233 — Franquias[] populado,
                               CodigoAtendimento AINDA null
ATENDIMENTO_POS_QUESTIONARIO . GET  /atendimentos              entries 270/278 — CodigoAtendimento
                               **existe**, com ScriptFinalizacao e LinkAreaSegurado
ATENDIMENTO_CANCELADO ........ GET  /atendimentos              entries 351/352, após PUT /cancelar

🔴 A SEQUÊNCIA É A PROVA DAS DUAS FRONTEIRAS
============================================
    POST /atendimentos    → NumeroProtocolo (16 díg.) + Token     ← fronteira A
    ...
    GET  /atendimentos    → CodigoAtendimento: null               (21:15:46)
    POST /questionarios   → (materializa)                          ← fronteira B
    GET  /atendimentos    → CodigoAtendimento: 8 díg. + link      (21:18:33)

E `ATENDIMENTO_COM_FRANQUIA` prova a terceira coisa: a franquia chega **antes**
do CodigoAtendimento, lá no passo 3. Na tela ela só apareceria no 100% — e o
fluxo normal para no 99%, esperando o segurado escolher loja. Raspando a tela,
a franquia nunca chegaria a ele.

SANITIZAÇÃO: CPF, nome, e-mail, telefone, CEP, placa, chassi, apólice, protocolo,
código de atendimento, token e o hash do link — todos sintéticos de mesmo
formato. Textos de domínio (ScriptFinalizacao, descrições) preservados literais.
"""
from __future__ import annotations

RESPOSTA_POST_ATENDIMENTOS = {
    "NumeroProtocolo": 2026081500000001,   # 16 dígitos — INTERNO, não é o que a tela mostra
    "Token": "00000000-0000-4000-8000-000000000000",
}

_BASE = {
    "NomeSegurado": "CLIENTE DE TESTE",
    "NomeSocial": None,
    "CpfCnpjSegurado": "11122233344",
    "Cep": "89010000",
    "DescricaoRelacaoTitular": "Corretor",
    "Placa": "Q***A91",
    "Apolice": "055309999999999",
    # Mascarado igual ao `maxpar_apolices.py`, que e a fixture irma. O valor
    # anterior era o VIN de exemplo publico da Wikipedia -- sintetico, nao era
    # chassi de ninguem -- mas um padrao de 17 caracteres numa fixture dispara
    # qualquer varredor de PII, e duas fixtures do mesmo diretorio tratando o
    # mesmo campo de formas diferentes ensina que a mascara e opcional.
    # 📊 Achado em 16/08/2026 pelo detector do Bloco J da SPEC-075.
    "Chassi": "9BW*******T004251",
    "DescricaoVeiculo": "COMPASS LIMITED 2.0 4X2 16V AUT.",
    "DataSinistro": "2026-08-14 00:00:00",
    "DescricaoItemDanificado": "VIDRO DE PORTA",
    "DescricaoOndeOcorreuDano": "Urbano (Cidade)",
    "EstadoRealizacaoServico": "SC",
    "CidadeRealizacaoServico": "BLUMENAU",
    "Email": "teste@exemplo.com.br",
    "TelefoneInformado": "47999990000",
    "CodigoSeguradora": 56,
    "Cancelado": False,
    "PermiteVistoriaMobile": False,
    "PermiteVistoriaLoja": False,
    "ExisteVistoriaCriada": False,
    "LinkVistoriaMobile": "",
    "VistoriaFinalizada": False,
    "VistoriaOnline": False,
    "MensagemVistoria": None,
    "CodigoScript": 3,
    "CodigoTipoScript": 129,
    "CodigoExterno": "ATG00099999",
}

ATENDIMENTO_PRE_QUESTIONARIO = {
    **_BASE,
    "CodigoAtendimento": None,
    "LinkAreaSegurado": None,
    "ScriptFinalizacao": None,
    "PossuiOrdemServico": None,
    "Questionarios": [],
    "Franquias": {"Franquias": None, "RequerFranquia": True,
                  "ExibirValorDeFranquia": True, "ExibeValorDeTroca": True},
}

# 📊 A franquia já está aqui, e o CodigoAtendimento ainda não.
ATENDIMENTO_COM_FRANQUIA = {
    **_BASE,
    "CodigoAtendimento": None,
    "LinkAreaSegurado": None,
    "ScriptFinalizacao": None,
    "PossuiOrdemServico": None,
    "Questionarios": [],
    "Franquias": {
        "Franquias": [{"ExibeValorParaTroca": True, "Titulo": "Valor para troca",
                       "Valor": "925"}],
        "RequerFranquia": True, "ExibirValorDeFranquia": True, "ExibeValorDeTroca": True,
    },
}

ATENDIMENTO_POS_QUESTIONARIO = {
    **_BASE,
    "CodigoAtendimento": 99999999,          # 8 dígitos — É ISTO que a tela mostra
    "LinkAreaSegurado": ("https://areadosegurado.autoglass.com.br/#/detalhe/"
                         "00000000-0000-4000-8000-000000000000/"
                         "00000000000000000000000000000000"),
    "ScriptFinalizacao": {
        "Titulo": ("Seu atendimento já está com o analista responsável. Você receberá "
                   "as orientações por um dos nossos canais digitais ou ligação até o "
                   "próximo dia útil. Fique atento ao seu WhatsApp, SMS e e-mail."),
        "Rodape": "A YELUM SEGURADORA agradece, conte sempre conosco!",
        "PrioridadeRetorno": False, "MensagemAdas": False, "InformacoesAdicionais": [],
    },
    "PossuiOrdemServico": False,
    "Questionarios": [
        {"DescricaoPergunta": "O VIDRO DANIFICADO TEM PELÍCULA DE CONTROLE SOLAR (INSULFILM)?",
         "DescricaoResposta": "SIM"},
        {"DescricaoPergunta": "O VIDRO DANIFICADO É DA PORTA DIANTEIRA OU TRASEIRA?",
         "DescricaoResposta": "DIANTEIRA"},
        {"DescricaoPergunta": "QUAL O LADO DO ITEM DANIFICADO?",
         "DescricaoResposta": "LADO DO CARONA"},
    ],
    "Franquias": {
        "Franquias": [{"ExibeValorParaTroca": True, "Titulo": "Valor para troca",
                       "Valor": "925"}],
        "RequerFranquia": True, "ExibirValorDeFranquia": True, "ExibeValorDeTroca": True,
    },
}

ATENDIMENTO_CANCELADO = {
    **ATENDIMENTO_POS_QUESTIONARIO,
    "Cancelado": True,
}

# 📊 Duas saídas DIFERENTES, e confundi-las seria erro de negócio:
#   abandonar → desistência antes de materializar (PATCH)
#   cancelar  → cancela um atendimento que já existe (PUT), com motivo codificado
ABANDONO_REQUEST = {"MotivoAbandono": "desistencia do usuario"}
ABANDONO_RESPONSE = {"AtendimentoCancelado": True}
CANCELAR_REQUEST = {"codigoMotivoCancelamento": 39, "codigoAtendimento": 99999999,
                    "observacaoMotivoCancelamento": "cancelado a pedido do segurado"}

# 📊 Dedup do próprio portal — devolve o booleano cru, não um objeto.
ATENDIMENTO_ABERTO_EXISTENTE_FALSE = False
ATENDIMENTO_ABERTO_EXISTENTE_TRUE = True
