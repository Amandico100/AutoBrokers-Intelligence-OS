# -*- coding: utf-8 -*-
"""Catálogos de domínio do portal Maxpar/AutoGlass — fixtures sanitizadas.

ORIGEM (captura de 2026-08-15, HARs fora do Git)
------------------------------------------------
SEGURADORAS ............... GET /seguradoras/  · YELUM har entry 20 (4x idênticas)
ITENS_COBERTOS_YELUM ...... GET /apolices/itens-cobertos?Seguradora=LIBERTY · entry 173
ITENS_COBERTOS_PORTO ...... GET /apolices/itens-cobertos?Seguradora=PORTO   · PORTO entry 171
MOTIVOS_DANO_VIDRO_PORTA .. GET /motivos-dano?CodigoItemCoberto=3|129|N|10700|1|0|V
MOTIVOS_DANO_LANTERNA ..... GET /motivos-dano?CodigoItemCoberto=4|132|S|11402|1|0|V

Nenhum dado pessoal existe aqui — são tabelas de domínio. Os telefones são 0800
e centrais públicas das seguradoras. Conteúdo LITERAL, acentos inclusive.
"""
from __future__ import annotations

# 📊 A captura traz 38 seguradoras. Estas 11 cobrem as 7 do nosso registry, a
# Porto (única com escolha de cobertura) e as que o roteador precisa distinguir.
TOTAL_SEGURADORAS_NA_CAPTURA = 38

# 🔴 O slug da Yelum no portal é `LIBERTY` — herança da marca anterior. Um
# roteador que procure "YELUM" no slug não acha nada.
SLUG_DA_YELUM = "LIBERTY"

SEGURADORAS = [
    {"Codigo": 7, "CodigoSeguradora": "ALFA", "NomeFantasia": "ALFA SEGUROS",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 49, "CodigoSeguradora": "ALLIANZ", "NomeFantasia": "ALLIANZ SEGUROS",
     "PermiteEnvioMensagemWhatsapp": False, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 67, "CodigoSeguradora": "AZUL", "NomeFantasia": "AZUL SEGUROS",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 52, "CodigoSeguradora": "BRADESCO", "NomeFantasia": "BRADESCO SEGUROS",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 62, "CodigoSeguradora": "HDI", "NomeFantasia": "HDI SEGUROS",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 41, "CodigoSeguradora": "MAPFRE", "NomeFantasia": "MAPFRE SEGUROS",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 128, "CodigoSeguradora": "PORTO", "NomeFantasia": "PORTO SEGURO",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 6, "CodigoSeguradora": "SULAMERICA", "NomeFantasia": "SULAMÉRICA AUTO",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 0, "CobraServicoMovel": "N"},
    {"Codigo": 23, "CodigoSeguradora": "TOKIOMARINE", "NomeFantasia": "TOKIO MARINE SEGURADORA",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 56, "CodigoSeguradora": "LIBERTY", "NomeFantasia": "YELUM SEGURADORA",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
    {"Codigo": 55, "CodigoSeguradora": "ZURICH", "NomeFantasia": "ZURICH",
     "PermiteEnvioMensagemWhatsapp": True, "ValorServicoMovel": 50, "CobraServicoMovel": "S"},
]

ITENS_COBERTOS_YELUM = [
    {"CodigoItemCoberto": "1|129|S|10700|1|0|V", "Descricao": "VIDRO PARABRISA",
     "DescricaoSimples": "VIDRO DIANTEIRO", "Bloqueios": []},
    {"CodigoItemCoberto": "3|129|N|10700|1|0|V", "Descricao": "VIDRO DE PORTA",
     "DescricaoSimples": "VIDRO DE PORTA", "Bloqueios": []},
    {"CodigoItemCoberto": "4|129|N|10700|1|0|V", "Descricao": "VIDRO DE JANELA",
     "DescricaoSimples": "VIDRO DE JANELA", "Bloqueios": []},
    {"CodigoItemCoberto": "6|129|N|10700|1|0|V", "Descricao": "VIDRO VIGIA (TRASEIRO)",
     "DescricaoSimples": "VIDRO TRASEIRO", "Bloqueios": []},
    {"CodigoItemCoberto": "1|131|N|10700|1|0|V", "Descricao": "FAROL MILHA/NEBLINA CONVENCIONAL",
     "DescricaoSimples": "FAROL MILHA/NEBLINA", "Bloqueios": []},
    {"CodigoItemCoberto": "15|134|S|10700|1|0|V", "Descricao": "LENTE DE RETROVISOR",
     "DescricaoSimples": "LENTE RETROVISOR", "Bloqueios": []},
    {"CodigoItemCoberto": "5|132|S|10700|1|0|V",
     "Descricao": "LANTERNA TRASEIRA BI-PARTIDA MALA LED",
     "DescricaoSimples": "LANTERNA MALA LED", "Bloqueios": []},
    {"CodigoItemCoberto": "1|84|S|10700|1|0|V", "Descricao": "PARACHOQUE PINTADO",
     "DescricaoSimples": "PARACHOQUE", "Bloqueios": ["AVISOSOBRECOBERTURADEPARACHOQUE"]},
    {"CodigoItemCoberto": "2|121|S|11359|1|0|U", "Descricao": "RODA LIGA LEVE",
     "DescricaoSimples": "RODA LIGA LEVE+PNEU", "Bloqueios": []},
    {"CodigoItemCoberto": "1|142|S|11337|1|0|L", "Descricao": "REPARO DE LATARIA E PINTURA",
     "DescricaoSimples": "REPARO DE LATARIA", "Bloqueios": []},
]

ITENS_COBERTOS_PORTO = [
    {"CodigoItemCoberto": "1|129|S|11402|1|0|V", "Descricao": "VIDRO PARABRISA",
     "DescricaoSimples": "VIDRO DIANTEIRO", "Bloqueios": []},
    {"CodigoItemCoberto": "3|129|N|11402|1|0|V", "Descricao": "VIDRO DE PORTA",
     "DescricaoSimples": "VIDRO DE PORTA", "Bloqueios": []},
    {"CodigoItemCoberto": "4|132|S|11402|1|0|V",
     "Descricao": "LANTERNA TRASEIRA BI-PARTIDA MALA CONVENCIONAL",
     "DescricaoSimples": "LANTERNA MALA HALOGENA", "Bloqueios": []},
    {"CodigoItemCoberto": "1|81|S|11402|1|0|V", "Descricao": "TETO SOLAR",
     "DescricaoSimples": "TETO SOLAR", "Bloqueios": []},
]

MOTIVOS_DANO_VIDRO_PORTA = [
    {"CodigoObjetoCausa": 21, "DescricaoObjetoCausa": "CHOQUE TERMICO"},
    {"CodigoObjetoCausa": 29, "DescricaoObjetoCausa": "CHUVA DE GRANIZO"},
    {"CodigoObjetoCausa": 10, "DescricaoObjetoCausa": "COLISÃO ACIDENTAL"},
    {"CodigoObjetoCausa": 1,
     "DescricaoObjetoCausa": "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA"},
    {"CodigoObjetoCausa": 27,
     "DescricaoObjetoCausa": "DANO DESCARACTERIZADO - FOI REALIZADO ALGUM REPARO"},
    {"CodigoObjetoCausa": 11,
     "DescricaoObjetoCausa": "DURANTE FORTE VENTANIA,TEMPESTADE OU ENCHENTE"},
    {"CodigoObjetoCausa": 17, "DescricaoObjetoCausa": "ENCONTROU O VEICULO DANIFICADO"},
    {"CodigoObjetoCausa": 19,
     "DescricaoObjetoCausa": "ESQUECIMENTO DE CHAVE OU PESSOA DENTRO DO VEÍCULO"},
    {"CodigoObjetoCausa": 26, "DescricaoObjetoCausa": "PEÇA AMARELADA, MANCHADA OU ARRANHADA"},
    {"CodigoObjetoCausa": 41,
     "DescricaoObjetoCausa": "QUEBRA DO VIDRO PARA TENTATIVA DE ROUBO OU FURTO"},
    {"CodigoObjetoCausa": 16, "DescricaoObjetoCausa": "QUEBRA INTENCIONAL OU VOLUNTÁRIA"},
    {"CodigoObjetoCausa": 34, "DescricaoObjetoCausa": "VIDRO NÃO SOBE OU DESCE"},
]

# 🔴 NÃO é a mesma lista da peça acima, e a diferença é o ponto:
# `AO TROCAR A LÂMPADA` e `GARRA DANIFICADA` só existem para lanterna/farol.
# Um catálogo estático de causas estaria errado para uma das duas no dia 1.
MOTIVOS_DANO_LANTERNA = [
    {"CodigoObjetoCausa": 38, "DescricaoObjetoCausa": "AO TROCAR A LÂMPADA QUEBROU O ITEM"},
    {"CodigoObjetoCausa": 29, "DescricaoObjetoCausa": "CHUVA DE GRANIZO"},
    {"CodigoObjetoCausa": 10, "DescricaoObjetoCausa": "COLISÃO ACIDENTAL"},
    {"CodigoObjetoCausa": 1,
     "DescricaoObjetoCausa": "DANO ACIDENTAL CAUSADO POR PEDRA, OBJETO OU FRUTA"},
    {"CodigoObjetoCausa": 23, "DescricaoObjetoCausa": "DANO NA PARTE ELETRICA"},
    {"CodigoObjetoCausa": 17, "DescricaoObjetoCausa": "ENCONTROU O VEICULO DANIFICADO"},
    {"CodigoObjetoCausa": 37, "DescricaoObjetoCausa": "GARRA DANIFICADA"},
    {"CodigoObjetoCausa": 25, "DescricaoObjetoCausa": "INFILTRAÇÃO SEM TRINCA OU QUEBRA"},
    {"CodigoObjetoCausa": 26, "DescricaoObjetoCausa": "PEÇA AMARELADA, MANCHADA OU ARRANHADA"},
    {"CodigoObjetoCausa": 18, "DescricaoObjetoCausa": "PELO TRANSPORTE DE CARGA"},
    {"CodigoObjetoCausa": 16, "DescricaoObjetoCausa": "QUEBRA INTENCIONAL OU VOLUNTÁRIA"},
    {"CodigoObjetoCausa": 14, "DescricaoObjetoCausa": "ROUBO OU FURTO DA PEÇA"},
]

TIPOS_TELEFONE = [
    {"Codigo": 2, "Descricao": "COMERCIAL"},
    {"Codigo": 5, "Descricao": "RECADO"},
    {"Codigo": 20, "Descricao": "CELULAR SEGURADO"},
    {"Codigo": 21, "Descricao": "CELULAR CORRETOR"},
    {"Codigo": 22, "Descricao": "RESIDENCIA SEGURADO"},
]

# 📊 Estático no template; o valor enviado é a PRIMEIRA LETRA do rótulo.
PERIMETRO_DANO = [("U", "Urbano (Cidade)"), ("R", "Rodoviário"), ("N", "Não Sabe")]

# 📊 `6` está fora de sequência e **não existe 4**. Decorar "o quarto da lista"
# daria Corretor onde se queria Filho.
RELACAO_TITULAR = [("1", "O Próprio"), ("2", "Cônjuge"), ("3", "Filho"),
                   ("6", "Corretor"), ("5", "Outros")]
