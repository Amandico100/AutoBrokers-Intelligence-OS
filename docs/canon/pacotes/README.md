# Pacotes-modelo — o que um subagente recebe

> Protocolo AAA v11 §1: o agente recebe um PACOTE, nunca o canon. Estes cinco são os
> pacotes vivos. O orquestrador copia o modelo, preenche os `{campos}` e despacha.
> Todo subagente roda em **Opus 5** (§10). O guarda `test_o_protocolo_tem_policia.py`
> bloco [9] confere que cada pacote carrega o protocolo e, quando executa, o card.

| pacote | quem | quando |
|---|---|---|
| [`PACOTE-PESQUISADOR.md`](PACOTE-PESQUISADOR.md) | 🌐 pesquisador | conversão: reabre o research-pack e escolhe o que modelar (§7.3) |
| [`PACOTE-AQUECIMENTO.md`](PACOTE-AQUECIMENTO.md) | 🔨 executor, contexto limpo | conversão: refuta a SPEC contra código e banco (§5.2) |
| [`PACOTE-BUILDER.md`](PACOTE-BUILDER.md) | 🔧 builder | execução de uma unidade |
| [`PACOTE-JUIZ.md`](PACOTE-JUIZ.md) | ⚖️ uma lente do painel · 🏁 juiz de confirmação | depois do verificador mecânico (§5 ④ e ⑦) |
| [`PACOTE-AUDITOR-EXTERNO.md`](PACOTE-AUDITOR-EXTERNO.md) | auditoria externa | só nível CRÍTICO (§6.1) |

Travas que vão em TODO pacote, sem exceção:

```
⛔ NENHUMA mensagem sai para segurado ou seguradora. NENHUM agente é ligado.
⛔ NENHUMA entrada em portal de seguradora. API InfoCap: somente leitura.
⛔ Banco: SELECT livre. Escrita só pelas migrations da SPEC em execução.
⛔ NUNCA imprimir CPF, telefone, apólice, placa, nome de pessoa, senha ou token.
⛔ NUNCA `git add -A`. NÃO tocar em variável de ambiente.
```
