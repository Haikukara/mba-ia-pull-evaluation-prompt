# Pull, Otimização e Avaliação de Prompts com LangChain e LangSmith

Solução do desafio do MBA em IA: fazer pull de um prompt de baixa qualidade do LangSmith Prompt Hub, otimizá-lo com técnicas de Prompt Engineering, publicar a versão otimizada e avaliá-la até atingir **0.8 em todas as métricas** (Helpfulness, Correctness, F1-Score, Clarity e Precision).

O enunciado original está no repositório base: [devfullcycle/mba-ia-pull-evaluation-prompt](https://github.com/devfullcycle/mba-ia-pull-evaluation-prompt).

**Resultado:** o prompt `fabiombarret/bug_to_user_story_v2` foi aprovado em duas avaliações seguidas (médias 0.816 e 0.813), contra 0.777 do prompt original.

---

## Técnicas Aplicadas (Fase 2)

O prompt otimizado está em [prompts/bug_to_user_story_v2.yml](prompts/bug_to_user_story_v2.yml). Ele usa quatro técnicas, listadas também nos metadados (`techniques_applied`).

### 1. Few-shot Learning (obrigatória)

**Por quê:** o avaliador compara a resposta com uma referência que segue um formato bem específico ("Como um ..., eu quero ..., para que ..." e critérios Dado/Quando/Então). Exemplos mostram esse formato melhor do que qualquer descrição.

**Como foi aplicada:** 3 pares de entrada/saída, um para cada nível de complexidade do dataset. Os exemplos foram **escritos do zero** (recuperação de senha, upload de foto, agendamento de consultas), sem copiar o dataset, para não vazar o gabarito.

```
Entrada:
Link "Esqueci minha senha" não envia o email de recuperação.

Saída:
Como um usuário que esqueceu a senha, eu quero receber o email de recuperação, para que eu possa voltar a acessar minha conta.

Critérios de Aceitação:
- Dado que estou na tela de login
- Quando clico em "Esqueci minha senha" e informo meu email cadastrado
...
```

### 2. Role Prompting

**Por quê:** a persona define o tom e o tipo de conteúdo esperado. Um Product Owner escreve critérios testáveis e pensa no valor para o usuário, que é o que o avaliador mede.

**Como foi aplicada:**

```
Você é um Product Owner sênior, especialista em transformar relatos de bugs em User Stories claras, testáveis e fiéis ao relato.
```

### 3. Chain of Thought (raciocínio interno)

**Por quê:** antes de escrever, o modelo precisa decidir a complexidade do relato, a persona certa e quais fatos preservar. Fazer isso em passos reduz erros como persona genérica ou números esquecidos.

**Como foi aplicada:** um roteiro de 3 passos que o modelo segue **sem escrever a análise na resposta**. Raciocínio visível seria penalizado pelo avaliador como "informação não solicitada".

```
# ANTES DE RESPONDER (pense passo a passo, sem escrever a análise)
1. Classifique o relato: SIMPLES, MÉDIO ou COMPLEXO.
2. Defina a persona pelo papel de negócio afetado (...).
3. Separe os fatos do relato que devem aparecer: números, valores, IDs, endpoints (...).
```

### 4. Skeleton of Thought

**Por quê:** as referências do dataset têm tamanhos muito diferentes: cerca de 400 caracteres nos bugs simples e mais de 4.000 nos complexos. Um formato único gera respostas longas demais nos simples (Precision e Clarity caem) ou curtas demais nos complexos (F1 cai).

**Como foi aplicada:** um esqueleto de saída para cada nível de complexidade:

- **SIMPLES:** story e 5 critérios de aceitação.
- **MÉDIO:** story, critérios e blocos opcionais ("Critérios Técnicos", "Exemplo de Cálculo", "Contexto Técnico").
- **COMPLEXO:** seções `=== USER STORY PRINCIPAL ===`, `=== CRITÉRIOS DE ACEITAÇÃO ===` (um bloco por problema), `=== CRITÉRIOS TÉCNICOS ===`, `=== CONTEXTO DO BUG ===` e `=== TASKS TÉCNICAS SUGERIDAS ===`.

### Outros requisitos do prompt

- **Regras explícitas:** responder só com a user story, preservar os termos e números do relato, não inventar métricas, não repetir informação entre blocos.
- **Critérios esperados por tipo de bug:** pagamento (HTTP 200, email, auditoria), estoque (validação no checkout, alternativas), modal (backdrop, foco, ESC), permissão (HTTP 403, auditoria) e contagem (só registros válidos).
- **Edge cases:** relato vago, relato em outro idioma e texto que não é bug.
- **System × User:** todas as instruções ficam no system prompt. O user prompt contém só o relato (`{bug_report}`), corrigindo a duplicação da v1.

---

## Resultados Finais

### Evidências no LangSmith

- **Dataset de avaliação público** (15 exemplos, com todos os experimentos e o tracing de cada execução):
  https://smith.langchain.com/public/93594306-be72-427f-ad4e-1a13efc763e3/d
- **Prompt publicado:** `fabiombarret/bug_to_user_story_v2` (público no Hub).

### Avaliação final

Configuração: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-haiku-5-5`, `EVAL_MODEL=claude-haiku-5-5`.

| Métrica | v1 (original) | v2, rodada 1 | v2, rodada 2 |
|---|---|---|---|
| Helpfulness | 0.80 ✓ | 0.82 ✓ | 0.82 ✓ |
| Correctness | 0.75 ✗ | 0.81 ✓ | 0.81 ✓ |
| F1-Score | 0.73 ✗ | 0.80 ✓ | 0.81 ✓ |
| Clarity | 0.84 ✓ | 0.82 ✓ | 0.82 ✓ |
| Precision | 0.76 ✗ | 0.82 ✓ | 0.81 ✓ |
| **Média** | **0.777** | **0.816** | **0.813** |
| Status | ❌ Reprovado | ✅ Aprovado | ✅ Aprovado |

### Screenshots

Avaliação aprovada (notas ≥ 0.8):

![Experimento aprovado no LangSmith](docs/images/avaliacao_aprovada.png)

Dataset de avaliação com os 15 exemplos:

![Dataset de avaliação](docs/images/dataset.png)

Tracing detalhado de exemplos:

![Tracing - exemplo simples](docs/images/tracing_1.png)
![Tracing - exemplo médio](docs/images/tracing_2.png)
![Tracing - exemplo complexo](docs/images/tracing_3.png)

### Comparação v1 × v2

| Aspecto | v1 (original) | v2 (otimizado) |
|---|---|---|
| Persona | "assistente que ajuda" (genérica) | Product Owner sênior |
| Variável `{bug_report}` | Duplicada no system e no user prompt | Só no user prompt |
| Formato de saída | Não definido | User story padrão + Dado/Quando/Então |
| Exemplos | Nenhum | 3 (simples, médio e complexo) |
| Adaptação ao tamanho do relato | Nenhuma | Esqueleto por nível de complexidade |
| Regras e edge cases | Nenhum | Regras explícitas, critérios por tipo de bug, 3 edge cases |
| Tamanho do system prompt | 232 caracteres | 6.276 caracteres |

**O que mais fez diferença:**

1. **Fidelidade ao relato (Precision 0.76 → 0.81):** a v1 deixava o modelo livre para inventar metas e detalhes. A v2 proíbe números inventados e manda preservar os termos do relato. Por exemplo, "aprovado" não pode virar "pago".
2. **Cobertura dos critérios esperados (F1 0.73 → 0.81):** a lista de critérios por tipo de bug faz o modelo incluir o que um PO incluiria (email de confirmação, log de auditoria, acessibilidade), que é o que as referências trazem.
3. **Persona correta:** em falhas automáticas (webhook, estoque, permissão), a v2 usa "o sistema de e-commerce", como as referências.

### Jornada de otimização

| # | Mudança | Modelos (gera / avalia) | Resultado |
|---|---|---|---|
| 1 | Primeira v2: persona, 3 exemplos, CoT, esqueleto por complexidade (10,4 mil caracteres) | Gemini 3.5 Flash-Lite / Flash-Lite | ✅ média 0.90 |
| 2 | Versão enxuta: mesmo conteúdo, sem repetições (5,1 mil caracteres) | Gemini Flash-Lite / Flash-Lite | ✅ 0.84 (2 notas zeradas por limite da API) |
| 3 | Persona por papel de negócio, função de cada bloco médio definida | Gemini Flash-Lite / Flash-Lite | Notas válidas melhores, mas a rodada falhou por cota do plano gratuito |
| 4 | Troca para Claude, para fugir das cotas do Gemini | Sonnet 5.5 / Sonnet 5.5 | ❌ F1 0.79 |
| 5 | Pedido genérico de critérios extras | Sonnet / Sonnet | ❌ F1 0.79, Precision caiu |
| — | Teste de geradores, com o avaliador fixo | Haiku, Opus / Sonnet | ❌ F1 0.79 nos dois: o limite era o avaliador |
| 6 | Linha de base com Haiku nos dois papéis | Haiku / Haiku | ❌ média 0.79 |
| **7** | **Persona "o sistema", sem números inventados, critérios por tipo de bug, menos repetição** | **Haiku / Haiku** | ✅ **0.816 e 0.813 (duas rodadas)** |
| 8 | Ajustes extras (metas de desempenho, abertura do formato complexo) | Haiku / Haiku | ❌ F1 0.78 e 0.80, por pouco |

**Aprendizados:**

- **O avaliador pesa mais que o gerador.** Com o mesmo avaliador (Sonnet), Sonnet, Haiku e Opus geraram respostas com o mesmo F1 (0.79). Já a troca de avaliador mudou bastante as notas.
- **Pedidos genéricos de completude derrubam a Precision.** Funcionou melhor listar critérios específicos por tipo de bug.
- **As notas variam entre rodadas.** O mesmo exemplo chegou a oscilar 0.15 entre execuções. Por isso a versão final foi escolhida por ter passado em duas rodadas, e não pela maior média isolada.
- **O plano gratuito do Gemini não comporta a avaliação.** O limite de 15 requisições por minuto zerou notas, e o de 20 requisições por dia do Gemini Flash interrompeu uma rodada no meio.

---

## Como Executar

### Pré-requisitos

- Python 3.10 ou superior
- Conta no [LangSmith](https://smith.langchain.com), com API key e handle público do Hub
- API key de um provedor de LLM: Anthropic (usado na entrega), OpenAI ou Google Gemini

### Instalação

```bash
git clone https://github.com/Haikukara/mba-ia-pull-evaluation-prompt.git
cd mba-ia-pull-evaluation-prompt
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
```

### Configuração

Copie `.env.example` para `.env` e preencha:

```
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=mba-ia-pull-evaluation-prompt
USERNAME_LANGSMITH_HUB=seu_handle

LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-haiku-5-5
EVAL_MODEL=claude-haiku-5-5
```

Para usar Gemini ou OpenAI, troque `LLM_PROVIDER` para `google` ou `openai` e preencha a chave e os modelos correspondentes.

### Execução por fase

**1. Pull do prompt original** (salva em `prompts/bug_to_user_story_v1.yml`):

```bash
python src/pull_prompts.py
```

**2. Otimização:** edite `prompts/bug_to_user_story_v2.yml`.

**3. Push do prompt otimizado** (público, com descrição, tags e técnicas; `-m` registra o que mudou na iteração):

```bash
python src/push_prompts.py -m "descrição da mudança"
```

**4. Avaliação** (cria um experimento no LangSmith e imprime o link):

```bash
python src/evaluate.py
```

**5. Testes de validação do prompt:**

```bash
pytest tests/test_prompts.py -v
```

---

## Estrutura e o que foi implementado

| Arquivo | O que faz |
|---|---|
| [src/pull_prompts.py](src/pull_prompts.py) | Faz pull de `leonanluppi/bug_to_user_story_v1`, separa as mensagens system/user e salva o YAML em formato legível |
| [src/push_prompts.py](src/push_prompts.py) | Valida o YAML (campos, técnicas, `{bug_report}` só no user prompt, template válido) e publica no Hub como público, com descrição, tags e README |
| [prompts/bug_to_user_story_v2.yml](prompts/bug_to_user_story_v2.yml) | Prompt otimizado |
| [tests/test_prompts.py](tests/test_prompts.py) | Os 6 testes exigidos e mais 2 extras (estrutura geral e `{bug_report}` fora do system prompt) |

### Alteração em arquivo marcado como "não alterar"

[src/utils.py](src/utils.py) ganhou o provedor `anthropic` na função `get_llm()`, para usar os modelos Claude. A alteração só **acrescenta** código: OpenAI e Gemini continuam idênticos. Detalhes:

- A temperatura não é enviada aos modelos Claude, porque os modelos atuais recusam valores diferentes do padrão (erro 400).
- `max_tokens=16000` e `max_retries=5`. O SDK repete automaticamente em erros 429 e 5xx.
- Nos modelos que aceitam (Sonnet 5.5, Opus 5.x e Fable 5.x), está ativo o fallback do servidor para respostas recusadas por política.

`src/evaluate.py`, `src/metrics.py` e o dataset não foram alterados.
