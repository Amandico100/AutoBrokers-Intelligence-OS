# -*- coding: utf-8 -*-
"""Fixtures sanitizadas do portal Maxpar/AutoGlass — SPEC-074.

Todas extraídas de HAR real capturado em 2026-08-15/16 e mantido FORA do Git
(`docs/intake/MATERIAIS/PORTAL VIDROS/`, coberto pelo `.gitignore`).

O que foi substituído por valor sintético de mesmo formato:
CPF/CNPJ · nome · placa · chassi · apólice · e-mail · telefone · CEP · token ·
GUID · NumeroProtocolo · CodigoAtendimento · CodigoExterno · hash de link.

O que ficou LITERAL, de propósito: tudo que é domínio — nomes de peça, causas,
perguntas, opções, mensagens de negócio, seguradoras e seus 0800.

🔴 E os ACENTOS ficam. Um fixture ASCII deixou passar um defeito real: o guard
comparava `avancar` com `Avançar` e recusava o clique que cria o pedido. Texto
de tela entra aqui como o portal manda, não como eu digitaria.
"""
