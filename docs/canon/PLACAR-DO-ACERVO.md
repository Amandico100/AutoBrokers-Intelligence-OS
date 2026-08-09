---
> **Status:** vivo · atualizado a cada lote executado
> **Criado em:** 08/08/2026 · **Autoridade:** SPEC-070
---

# O PLACAR DO ACERVO — o que temos, de quem, e de quando

> **Este é o documento que responde "onde estamos?" sem ninguém precisar
> perguntar.** Uma linha por seguradora × ramo. Quem executa um lote da SPEC-070
> **atualiza esta tabela** — é o passo 8 do §9.

## Como ler

| símbolo | significado |
|---|---|
| ✅ | temos, na versão **vigente** confirmada no registro da SUSEP |
| ⚠️ | temos, mas a versão é **antiga** — a SUSEP publica outra |
| 🔴 | **não temos** e a seguradora vende |
| ➖ | a seguradora não vende esse ramo |
| ❔ | não conferido ainda |

---

## 1. O placar

📊 Estado em 08/08/2026, **depois do LOTE 1** (a Porto).

| seguradora | auto | resid. | condom. | empres. | vida | fiança | equip. | conferido em |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **porto** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 🔴 | 08/08/2026 |
| **allianz** | ⚠️ | ⚠️ | 🔴 | ⚠️ | ⚠️ | ❔ | ❔ | 08/08/2026 |
| **bradesco** | 🔴 | ⚠️ | 🔴 | ⚠️ | ⚠️ | ❔ | ❔ | 08/08/2026 |
| **mapfre** | ⚠️ | ⚠️ | 🔴 | ⚠️ | ⚠️ | ❔ | ❔ | 08/08/2026 |
| **tokio** | ⚠️ | 🔴 | 🔴 | ⚠️ | 🔴 | ❔ | ❔ | 08/08/2026 |
| **azul** | ⚠️ | 🔴 | ➖ | ➖ | ➖ | ➖ | ➖ | 08/08/2026 |
| **yelum** | 🔴 | 🔴 | ❔ | ❔ | ❔ | ❔ | ❔ | 08/08/2026 |
| **hdi** | 🔴 | 🔴 | ❔ | ❔ | ❔ | ❔ | ❔ | 08/08/2026 |
| **zurich** | 🔴 | 🔴 | ❔ | ❔ | 🔴 | ❔ | ❔ | 08/08/2026 |
| **alfa** | 🔴 | ❔ | ❔ | ❔ | ❔ | ❔ | ❔ | 08/08/2026 |
| **sura** | 🔴 | ❔ | ❔ | ❔ | ❔ | ❔ | ❔ | 08/08/2026 |
| **suhai** | 🔴 | ➖ | ➖ | ➖ | ➖ | ➖ | ➖ | 08/08/2026 |
| **youse** | 🔴 | ❔ | ➖ | ➖ | ❔ | ➖ | ➖ | 08/08/2026 |
| **caixa / santander / bb** | ❔ | ❔ | ❔ | ❔ | ❔ | ❔ | ❔ | nunca |

**📊 O resumo que doía:** de 13 documentos conferidos contra o registro oficial,
**1 estava na versão vigente**. Depois do LOTE 1, os 6 da Porto estão.

### 1.1 O que o LOTE 1 trocou na Porto

📊 08/08/2026 · 6 documentos · 1.686 pedaços · 40 segundos · 0 falhos.

| ramo | o que estava no ar | passou a ser | vigência oficial |
|---|---|---|---|
| auto | CG140 (janeiro) | **CG144** | 01/07/2026 |
| condomínio | **o de 2012** | dezembro/2025 | 11/12/2025 |
| empresarial | abril/2025 | julho/2026 | 31/07/2026 |
| residencial | dezembro/2025 | dezembro/2025 | 05/12/2025 |
| fiança | sem data | agosto/2026 | 08/08/2026 |
| vida | 2022 | novembro/2025 | 27/11/2025 |

As 6 versões antigas foram **fechadas e guardadas**, não apagadas: o
`superseded_at` marca a data e o PDF continua no MinIO. Documento revogado sai
da busca e vai para o arquivo morto — decisão **D-Acervo-02**.

---

## 2. 🔴 A descoberta que reorganiza tudo: marca ≠ companhia

📊 Achado no `--diagnostico` da Porto em 08/08/2026.

A **Porto Seguro Companhia de Seguros Gerais** é a emissora legal dos produtos
de várias marcas. O `--diagnostico` trouxe, sob o CNPJ dela:

```
CG71_Itaú Seguro Auto_Susep.pdf
Itaú Seguro Residencial — Condições Gerais
Condições Gerais Itaú Residencial
CG09 - Itaú Assistência 24 horas
4009 - CG23 Azul Seguro Auto
4007 - CG09 Azul Seguro Moto e Azul Seguro Auto Compacto
3797 - CG24 Mitsui
3844 - CG Frota Mitsui
```

**O que isso significa na prática:** o segurado diz *"tenho seguro na Azul"*, e o
contrato dele está registrado sob a **Porto**. Se o acervo tratar `azul` e
`porto` como coisas separadas, a busca por `azul` não acha o contrato — que
existe, sob outro nome.

| marca comercial | companhia emissora |
|---|---|
| Azul Seguros | Porto Seguro Cia de Seguros Gerais |
| Itaú Seguro Auto / Residencial | Porto Seguro Cia de Seguros Gerais |
| Mitsui (frota) | Porto Seguro Cia de Seguros Gerais |
| Liberty | Yelum (renome da mesma pessoa jurídica) |
| Sompo varejo | vendido à HDI em 2023 |

🔴 **Pendência aberta:** o acervo precisa saber que a marca da apólice e a
companhia emissora podem diferir. Sem isso, quem tem Azul não acha o próprio
contrato. **Registrado, não resolvido** — decisão para depois do LOTE 1.

---

## 3. ⚠️ O problema do ramo "vida"

📊 A Porto tem **41 produtos** classificados como vida na SUSEP — de 71 no total.
Entre eles: `Vida Individual`, `Vida Coletivo`, `Capital Global`, `Vida Mais
Mulher`, `Vida Mais Simples`, `AP Plus`, `Vida Presente`, `Faixa Etária`.

E vários com nome de arquivo que não diz nada: `CG.pdf`, `CG4.pdf`, `cg9.pdf`,
`CGVI2.pdf`, `C Contratuais.pdf`.

> **Trazer 41 documentos de vida de uma seguradora só encheria o índice de
> variações do mesmo produto.** E o recurso escasso não é disco — são as vagas
> que chegam ao agente.

**A regra que vale até termos medida melhor:** de vida, entra o produto que o
acervo de conversas mostra que os clientes perguntam. Os demais ficam nesta
lista, e entram quando houver pergunta que os justifique.

---

## 4. A fila de ramos pendentes, por seguradora

O que entra depois do primeiro passe. **Não é para fazer agora** — é para não
esquecer.

| prioridade | o que falta | por quê |
|---|---|---|
| 🔥 1 | **bradesco auto** | 📊 é a maior lacuna isolada do acervo: a seguradora tem 138 cartas e nenhum contrato de auto |
| 🔥 2 | **yelum: todos os ramos** | 📊 359 cartas, 174 de cobertura, corredor ativo nas duas corretoras, zero documentos |
| 🔥 3 | **hdi: todos os ramos** | 📊 267 cartas, 128 de cobertura, zero documentos, e o site próprio morreu |
| 4 | **condomínio** de allianz, bradesco, mapfre, tokio | ramo real, com síndico como cliente distinto |
| 5 | **fiança locatícia** das que vendem | produto de imobiliária, pergunta recorrente |
| 6 | **frota** (auto pesado) | 📊 a AutoFleet é 3.375 atendimentos e o nome diz o ramo |
| 7 | **RC / responsabilidade civil** | 📊 41 cartas hoje; cresce com corretora empresarial |
| 8 | **equipamentos / riscos diversos** | 📊 a pergunta da retroescavadeira não tinha onde cair |
| 9 | zurich, alfa, sura, suhai | volume menor, corredor ativo |
| 10 | caixa, santander, bb | entram quando uma corretora bancária parear |

---

## 5. Registro de execução

*(cada lote acrescenta seu bloco — quem executou, quando, o que entrou)*

```
LOTE 1 — Porto            ⬜ não executado
```
