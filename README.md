# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Projeto do desafio do MBA em Engenharia de Software com IA (Full Cycle): puxar um prompt de baixa qualidade do **LangSmith Prompt Hub**, refatorá-lo com técnicas de Prompt Engineering, publicar a versão otimizada e avaliá-la com 5 métricas (Helpfulness, Correctness, F1-Score, Clarity e Precision) até todas ficarem **≥ 0.8**.

> O enunciado original do desafio está em [ENUNCIADO.md](ENUNCIADO.md).

- Prompt original (semente): `leonanluppi/bug_to_user_story_v1`
- Prompt otimizado (publicado): [`sapino/bug_to_user_story_v2`](https://smith.langchain.com/hub/sapino/bug_to_user_story_v2)
- Tarefa: converter um **relato de bug** (`{bug_report}`) em uma **User Story** com critérios de aceitação

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado está em [prompts/bug_to_user_story_v2.yml](prompts/bug_to_user_story_v2.yml) e lista as técnicas em `techniques_applied`.

### 1. Role Prompting

**Por quê:** o v1 dizia apenas "Você é um assistente". Sem uma persona, o modelo não sabe para quem escreve nem que padrão de qualidade seguir. Um PM Sênior de times ágeis já tem o formato "Como um... eu quero... para que..." e os critérios Dado/Quando/Então como padrão. O público (devs e QAs) também deixa claro que os critérios precisam ser testáveis.

**Como apliquei:**

```text
# PAPEL
Você é um Product Manager Sênior com 10 anos de experiência em times ágeis (Scrum)
de produtos digitais: e-commerce, SaaS B2B, ERP, CRM e apps mobile. [...] Seus leitores
são desenvolvedores e QAs, que precisam entender O QUE deve funcionar, PARA QUEM e COMO verificar.
```

### 2. Few-shot Learning (obrigatória)

**Por quê:** as métricas comparam a resposta com uma referência de formato bem específico, e o nível de detalhe esperado muda muito entre bugs simples e complexos. Exemplos mostram esse formato com mais precisão que qualquer descrição.

**Como apliquei:** são 3 exemplos completos de entrada → saída, um por nível de complexidade. Todos são de **domínios que não estão no dataset** (blog, upload de avatar, agendamento de consultas), para ensinar o formato sem vazar respostas:

| Exemplo | Complexidade | O que ele ensina |
|---|---|---|
| "Salvar rascunho" não funciona | Simples | story + 5 critérios e mais nada |
| Upload PNG > 2MB com HTTP 413 | Médio | critérios de sucesso/erro + `Contexto Técnico` preservando endpoint, código HTTP e causa |
| Agendamento com 3 falhas + impacto | Complexo | seções `=== ... ===`, blocos A/B/C por problema, critérios técnicos, contexto com números do impacto e tasks com prefixo `[ÁREA]` |

### 3. Chain of Thought (CoT), interno

**Por quê:** para transformar um bug em uma story é preciso pensar em etapas: quem é afetado, qual é o comportamento correto, qual valor ele recupera e quais fatos do relato precisam ser mantidos. Só que o resultado é avaliado como texto final, e um raciocínio visível derrubaria Clarity e Precision. Por isso o CoT é **interno**: o modelo segue os passos, mas não os mostra na resposta.

**Como apliquei:**

```text
# PROCESSO DE RACIOCÍNIO (pense passo a passo, internamente)
Antes de escrever, raciocine passo a passo SEM mostrar esse raciocínio na resposta:
1. Persona [...]  2. Comportamento esperado [...]  3. Benefício [...]
4. Fatos do relato [...]  5. Complexidade [...]  6. Critérios [...]
```

### 4. Skeleton of Thought

**Por quê:** o dataset tem 5 bugs simples, 7 médios e 3 complexos, e as referências têm estruturas diferentes para cada nível. Um esqueleto por complexidade evita que o modelo gere demais nos casos simples (o que prejudica Precision e Clarity) ou de menos nos complexos (o que prejudica o Recall do F1).

**Como apliquei:** o passo 5 do CoT classifica o relato, e a seção `CLASSIFICAÇÃO DE COMPLEXIDADE E ESQUELETO DA RESPOSTA` define as seções permitidas em cada nível:

```text
SIMPLES  -> User Story + "Critérios de Aceitação:" (5 itens) e NADA além disso
MÉDIO    -> + seções opcionais (Critérios Técnicos, de Acessibilidade, Exemplo de Cálculo...) + Contexto Técnico
COMPLEXO -> === USER STORY PRINCIPAL === / === CRITÉRIOS DE ACEITAÇÃO === (A, B, C...) /
            === CRITÉRIOS TÉCNICOS === / === CONTEXTO DO BUG === / === TASKS TÉCNICAS SUGERIDAS ===
```

### Outros requisitos atendidos

- **Regras explícitas de comportamento:** a seção `REGRAS DE ESCRITA` tem 8 regras numeradas: primeira linha sempre é a story, um passo por linha, preservar todos os números, não inventar fatos (usar `[marcador]` quando faltar dado), sem Markdown pesado, concisão e nenhum comentário final.
- **Edge cases:** relato vago, vários problemas, segurança (HTTP 403, auditoria, OWASP), cálculo, performance, plataforma específica, modal/acessibilidade, relato que não é bug e relato em outro idioma.
- **System vs User prompt:** o system prompt tem tudo que é fixo (papel, regras, esqueletos, exemplos). O user prompt tem só a tarefa e o `{bug_report}` delimitado por `"""`. O v1 repetia o `{bug_report}` nos dois.

---

## Resultados Finais

### Evidências no LangSmith

- **Dataset de avaliação público (15 exemplos + experimentos + traces):** https://smith.langchain.com/public/641ccceb-cd37-4a62-800c-b5c8529eadea/d
- **Prompt publicado:** https://smith.langchain.com/hub/sapino/bug_to_user_story_v2

### Notas da avaliação final (`python src/evaluate.py`)

Experimento `sapino-bug_to_user_story_v2-4da95097` (provider `openai`, `gpt-4.1-mini` + juiz `gpt-4.1`):

```
==================================================
Prompt: sapino/bug_to_user_story_v2
==================================================

Métricas Derivadas:
  - Helpfulness: 0.91 ✓
  - Correctness: 0.92 ✓

Métricas Base:
  - F1-Score: 0.90 ✓
  - Clarity: 0.87 ✓
  - Precision: 0.94 ✓

--------------------------------------------------
📊 MÉDIA GERAL: 0.9103
--------------------------------------------------

✅ STATUS: APROVADO - Todas as métricas >= 0.8
```

Notas por exemplo:

| # | Complexidade | F1 | Clarity | Precision |
|---|---|---|---|---|
| 1 | simples | 0.92 | 0.92 | 0.95 |
| 2 | simples | 0.93 | 0.85 | 0.93 |
| 3 | simples | 0.94 | 0.92 | 0.97 |
| 4 | simples | 0.75 | 0.75 | 0.70 |
| 5 | simples | 0.90 | 0.93 | 0.95 |
| 6 | médio | 0.85 | 0.90 | 0.97 |
| 7 | médio | 0.92 | 0.80 | 1.00 |
| 8 | médio | 1.00 | 0.95 | 1.00 |
| 9 | médio | 0.97 | 0.95 | 1.00 |
| 10 | médio | 0.85 | 0.85 | 0.93 |
| 11 | médio | 0.85 | 0.85 | 0.93 |
| 12 | médio | 0.85 | 0.85 | 0.93 |
| 13 | complexo | 0.95 | 0.80 | 0.93 |
| 14 | complexo | 0.89 | 0.95 | 1.00 |
| 15 | complexo | 1.00 | 0.85 | 0.93 |

Screenshots do dashboard: [docs/evidencias/](docs/evidencias/)

### Histórico de iterações

Modelos usados: `gpt-4.1-mini` para responder e `gpt-4.1` como juiz (os dois aceitam `temperature=0`, o que deixa a avaliação reproduzível).

| Iteração | Mudança | F1 | Clarity | Precision | Helpfulness | Correctness |
|---|---|---|---|---|---|---|
| 1 (local) | v2 inicial: persona, CoT interno, esqueletos, regras, 3 exemplos | 0.90 | 0.90 | 0.95 | 0.92 | 0.92 |
| 2 (local) | metas de performance devem ser o valor **corrigido** (o caso #7 usava "até 120s", o próprio sintoma do bug); proibida informação repetida entre seções; edge cases de acessibilidade e de carga | 0.90 | 0.91 | 0.96 | 0.94 | 0.93 |
| 3 (LangSmith, oficial) | mesmo prompt da iteração 2, publicado no Hub e avaliado por `src/evaluate.py` | 0.90 | 0.87 | 0.94 | 0.91 | 0.92 |

As iterações locais usaram exatamente as funções de [src/metrics.py](src/metrics.py) sobre os 15 exemplos do dataset, sem LangSmith, para iterar mais rápido e gastar menos. A avaliação oficial é a do `src/evaluate.py`.

**Como os traces guiaram as mudanças:** os comentários do juiz (gravados como feedback em cada exemplo) mostraram que a maior perda era de **Recall** (critérios da referência que ficaram de fora, como acessibilidade em modais e consistência em horário de pico) e de **Concisão** (a mesma causa técnica aparecia em duas seções). Cada regra adicionada na iteração 2 responde diretamente a um desses comentários.

### Comparação v1 × v2

| Aspecto | v1 (original) | v2 (otimizado) | Por quê |
|---|---|---|---|
| Persona | "assistente que ajuda" | PM Sênior de times ágeis, escrevendo para devs/QAs | define padrão de qualidade e vocabulário |
| Instruções | "crie uma user story" | tarefa, formato e processo de raciocínio explícitos | elimina ambiguidade |
| Formato | não definido | `Como um..., eu quero..., para que...` + Dado/Quando/Então + seções por complexidade | igual às referências, o que aumenta F1 e Clarity |
| Exemplos | nenhum | 3 few-shot (simples, médio, complexo) | mostra o formato e o nível de detalhe esperados |
| Nível de detalhe | igual para tudo | esqueleto por complexidade | evita sobra (Precision) e falta (Recall) |
| Alucinação | sem controle | "não invente fatos", marcadores `[...]`, "nunca altere números" | Precision |
| Edge cases | nenhum | 10 casos tratados | robustez |
| System × User | `{bug_report}` duplicado nos dois | system = regras; user = só o relato | separa responsabilidades e evita confusão |
| Metadados | tags | tags, `techniques_applied`, `changelog`, README no Hub | rastreabilidade |

---

## Como Executar

### Pré-requisitos

- Python 3.10+
- Conta no [LangSmith](https://smith.langchain.com) com API key e um **handle público** do Hub (veja [ENUNCIADO.md](ENUNCIADO.md#handle-do-langsmith-hub-seu-username))
- API key da OpenAI (ou Google Gemini)

### 1. Instalação

```bash
git clone https://github.com/pedrohsantos/mba-ia-pull-evaluation-prompt.git
cd mba-ia-pull-evaluation-prompt
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuração

```bash
cp .env.example .env
```

Preencha no `.env`:

| Variável | Valor usado neste projeto |
|---|---|
| `LANGSMITH_API_KEY` | sua chave do LangSmith |
| `LANGSMITH_PROJECT` | `mba-ia-pull-evaluation-prompt` |
| `USERNAME_LANGSMITH_HUB` | seu handle do Hub (aqui: `sapino`) |
| `OPENAI_API_KEY` | sua chave da OpenAI |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4.1-mini` |
| `EVAL_MODEL` | `gpt-4.1` |

> O `.env` está no `.gitignore`. Nunca faça commit das suas chaves.

### 3. Fases do projeto

```bash
# Fase 1: pull do prompt semente -> prompts/bug_to_user_story_v1.yml
python src/pull_prompts.py

# Fase 2: o prompt otimizado está em prompts/bug_to_user_story_v2.yml
#         valide a estrutura com os testes
pytest tests/test_prompts.py -v

# Fase 3: push público para {USERNAME_LANGSMITH_HUB}/bug_to_user_story_v2
python src/push_prompts.py

# Fase 4: avaliação (cria um experimento no LangSmith e imprime o link)
python src/evaluate.py
```

Para iterar: edite o YAML v2, rode `push_prompts.py` e depois `evaluate.py` de novo. Cada execução vira um experimento novo, que pode ser comparado com os anteriores no dashboard do dataset.

### O que cada script faz

- [src/pull_prompts.py](src/pull_prompts.py): faz `client.pull_prompt(..., dangerously_pull_public_prompt=True)`, extrai as mensagens system/human do `ChatPromptTemplate` e salva em YAML.
- [src/push_prompts.py](src/push_prompts.py): lê o YAML e o valida (campos obrigatórios, sem TODOs, ≥ 2 técnicas, template compilável expondo **apenas** `{bug_report}`). Depois monta o `ChatPromptTemplate` (system + user) e publica com `is_public=True`, descrição, README, tags (incluindo as técnicas) e descrição do commit.
- [tests/test_prompts.py](tests/test_prompts.py): 6 testes obrigatórios e mais 2 extras (estrutura via `validate_prompt_structure` e uso correto de `{bug_report}` apenas no user prompt).
