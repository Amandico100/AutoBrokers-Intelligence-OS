# A lista de coleta — SPEC-084 BLOCO 5

> Gerado do corpus e do corredor · commit `ad6ab25`

🔴 **Uma rota só entra aqui se o CORPUS está vazio E o ACERVO da
seguradora também não a tem.** Se o acervo tem e o corpus não, o
problema é do classificador — e a linha sai com esse diagnóstico,
não como pedido de coleta. 📊 Foi assim que `tecnico` (109 linhas)
quase virou pedido de coleta com o material já no banco.


## ALFA

**1 · O número:** `insurer_contact_ref = 'alfa_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  menu_tipo_seguro
  -> pedir_cpf
  -> confirmar_veiculo
  -> menu_servico_auto
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`guincho`**, que hoje pontua **67/96**.

   Se `guincho` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

## AZUL

**1 · O número:** `insurer_contact_ref = 'azul_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  menu_inicial_lista
  -> saudacao_atendente
  -> pedir_cpf
  -> menu_atendimento
  -> menu_servico
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`bateria`**, que hoje pontua **31/96**.

   Se `bateria` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | pneu | 10 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

## BRADESCO

**1 · O número:** `insurer_contact_ref = 'bradesco_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  menu_inicial
  -> confirmar_veiculo
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 SEM LINHA DE CONTROLE POSSÍVEL:** nenhuma rota desta seguradora pontua hoje. ⚠️ Isso significa que a coleta aqui **não terá como distinguir** 'a URA mudou' de 'este serviço é diferente'. Colete o serviço mais comum PRIMEIRO, e ele passa a ser o controle dos próximos.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | guincho | 72 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | pneu | 10 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

## HDI

**1 · O número:** `insurer_contact_ref = 'hdi_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  identificacao_dado
  -> continuar_com_placa
  -> informar_nome
  -> perfil
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`pneu`**, que hoje pontua **60/96**.

   Se `pneu` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| residencial | desentupimento | 1 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| residencial | eletrodomesticos | 0 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |

## MAPFRE

**1 · O número:** `insurer_contact_ref = 'mapfre_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  pedir_cpf
  -> perfil_segurado
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 SEM LINHA DE CONTROLE POSSÍVEL:** nenhuma rota desta seguradora pontua hoje. ⚠️ Isso significa que a coleta aqui **não terá como distinguir** 'a URA mudou' de 'este serviço é diferente'. Colete o serviço mais comum PRIMEIRO, e ele passa a ser o controle dos próximos.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | guincho | 72 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | pneu | 10 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

## PORTO

**1 · O número:** `insurer_contact_ref = 'porto_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  menu_raiz
  -> pedir_cpf
  -> saudacao_de_volta
  -> menu_servico_resid
  -> menu_atendimento_resid
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`chaveiro`**, que hoje pontua **43/96**.

   Se `chaveiro` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| residencial | eletricista | 12 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| auto | pneu | 10 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| auto | taxi | 1 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| residencial | desentupimento | 1 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |
| auto | bateria_nova | 0 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |

## TOKIO

**1 · O número:** `insurer_contact_ref = 'tokio_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  pedir_cpf
  -> menu_servicos_auto
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`guincho`**, que hoje pontua **42/96**.

   Se `guincho` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | pneu | 10 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

## YELUM

**1 · O número:** `insurer_contact_ref = 'yelum_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  identificacao_dado
  -> continuar_com_placa
  -> informar_nome
  -> perfil
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`pneu`**, que hoje pontua **64/96**.

   Se `pneu` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| residencial | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| residencial | desentupimento | 1 | 🔴 o RÓTULO do menu, que o corredor ainda não tem |

## ZURICH

**1 · O número:** `insurer_contact_ref = 'zurich_assistencia_24h'` — ⚠️ o número real vem da configuração da corretora, não do código.

**2 · O caminho até o ponto desconhecido:**

```
  menu_servicos
  -> pedir_cpf
  -> confirmar_veiculo
  -> saudacao_laiz
  -> [ AQUI: escolher o serviço ]
```

**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com **`guincho`**, que hoje pontua **23/96**.

   Se `guincho` der o mesmo desfecho de hoje, o que a primeira rodada mostrar é do SERVIÇO. Se der diferente, a URA mudou — e nenhuma das duas conclusões vale.

**4 · O que se espera aprender, por rota:**

| ramo | serviço | demanda | o que falta ver |
|---|---|---:|---|
| auto | bateria | 16 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | pneu | 10 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | socorro_mecanico | 7 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | chaveiro | 5 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |
| auto | vidros | 0 | a tela SEGUINTE ao clique no menu — é ela que separa este serviço dos outros |

---

## ⚠️ NÃO SÃO COLETA — o acervo TEM, o corpus não

📊 Estas rotas aparecem `SEM_CORPUS` na régua, mas a seguradora
**já tem sessões desse serviço no acervo**. O problema é o
classificador ou a cota por rota, não a falta de material.
Mandá-las para coleta é o erro que a SPEC-083 nomeou.

- `allianz/auto/chaveiro`

---

📊 **31 rotas pedem coleta de verdade** · 1 eram artefato do medidor · 32 apareciam SEM_CORPUS na régua.
