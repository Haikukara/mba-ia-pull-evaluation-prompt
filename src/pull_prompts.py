"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv
from langsmith import Client
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _str_presenter(dumper, value):
    """Grava textos com várias linhas no estilo bloco (|), mais legível no YAML."""
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


# Vale para o yaml.dump usado por save_yaml (utils.py)
yaml.add_representer(str, _str_presenter)

# Prompt semente do desafio e onde ele será salvo localmente
SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "prompts" / "bug_to_user_story_v1.yml"


def extract_messages(prompt) -> dict:
    """
    Separa o template de cada mensagem do ChatPromptTemplate por papel.

    Retorna um dicionário com as chaves "system_prompt" e "user_prompt".
    Se houver mais de uma mensagem do mesmo papel, os textos são concatenados.
    """
    role_to_field = {"system": "system_prompt", "human": "user_prompt"}
    fields = {"system_prompt": [], "user_prompt": []}

    for message in prompt.messages:
        template = getattr(getattr(message, "prompt", None), "template", None)
        if template is None:
            # Ex.: MessagesPlaceholder não tem template de texto
            continue

        # SystemMessagePromptTemplate -> "system", HumanMessagePromptTemplate -> "human"
        role = type(message).__name__.replace("MessagePromptTemplate", "").lower()
        field = role_to_field.get(role)
        if field:
            fields[field].append(template)

    return {field: "\n\n".join(parts) for field, parts in fields.items()}


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt semente no LangSmith Hub e o converte para o formato YAML
    usado no projeto.

    Returns:
        Dicionário pronto para ser salvo com save_yaml, ou None em caso de erro.
    """
    client = Client()

    print(f"Fazendo pull de: {SOURCE_PROMPT}")
    try:
        prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    except Exception as e:
        print(f"❌ Erro ao fazer pull do prompt: {e}")
        print("\nVerifique LANGSMITH_API_KEY no .env e sua conexão com a internet.")
        return None

    messages = extract_messages(prompt)
    if not messages["system_prompt"]:
        print("❌ O prompt baixado não contém mensagem de sistema.")
        return None

    print(f"   ✓ Prompt carregado ({len(prompt.messages)} mensagens)")
    print(f"   ✓ Variáveis de entrada: {', '.join(prompt.input_variables)}")

    hub_metadata = prompt.metadata or {}
    prompt_name = SOURCE_PROMPT.split("/")[-1]

    return {
        prompt_name: {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": messages["system_prompt"],
            "user_prompt": messages["user_prompt"],
            "version": "v1",
            "source": SOURCE_PROMPT,
            "commit_hash": hub_metadata.get("lc_hub_commit_hash", ""),
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    data = pull_prompts_from_langsmith()
    if data is None:
        return 1

    if not save_yaml(data, str(OUTPUT_PATH)):
        return 1

    print(f"   ✓ Salvo em: {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    print("\n✅ Pull concluído com sucesso!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
