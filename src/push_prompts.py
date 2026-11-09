"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_FILE = PROJECT_ROOT / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"

# Variável de entrada usada pelo dataset de avaliação
REQUIRED_VARIABLE = "{bug_report}"


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate com a mensagem de sistema e a do usuário."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict, commit_message: str = "") -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt
        commit_message: Descrição opcional do commit (ex.: o que mudou nesta iteração)

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    identifier = f"{username}/{prompt_name}"
    techniques = prompt_data.get("techniques_applied", [])

    # Tags do prompt: as do YAML + a versão + as técnicas (em formato de slug)
    technique_tags = [t.lower().replace(" ", "-") for t in techniques]
    tags = list(dict.fromkeys(
        prompt_data.get("tags", []) + [prompt_data.get("version", "")] + technique_tags
    ))
    tags = [t for t in tags if t]

    readme = "\n".join([
        f"# {prompt_name}",
        "",
        prompt_data.get("description", "").strip(),
        "",
        "## Técnicas aplicadas",
        *[f"- {t}" for t in techniques],
        "",
        f"Versão: {prompt_data.get('version', '')}",
    ])

    client = Client()
    prompt = build_chat_prompt(prompt_data)

    print(f"Fazendo push de: {identifier}")
    try:
        url = client.push_prompt(
            identifier,
            object=prompt,
            is_public=True,
            description=prompt_data.get("description", "").strip(),
            readme=readme,
            tags=tags,
            commit_description=commit_message or None,
        )
    except Exception as e:
        # O Hub recusa um commit idêntico ao anterior; o prompt publicado já é o atual
        if "nothing to commit" in str(e).lower():
            print("   ✓ Nenhuma mudança no prompt desde o último push (Hub já atualizado)")
            return True

        print(f"❌ Erro ao fazer push: {e}")
        if "handle" in str(e).lower() or "403" in str(e) or "404" in str(e):
            print("\nConfira se USERNAME_LANGSMITH_HUB é o seu handle público do Hub.")
        return False

    print(f"   ✓ Push concluído (público)")
    print(f"   ✓ Tags: {', '.join(tags)}")
    print(f"   ✓ {url}")
    return True


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    # Regras gerais: campos obrigatórios, TODOs e mínimo de 2 técnicas
    _, errors = validate_prompt_structure(prompt_data)

    user_prompt = (prompt_data.get("user_prompt") or "").strip()
    system_prompt = (prompt_data.get("system_prompt") or "").strip()

    if not user_prompt:
        errors.append("user_prompt está vazio")
    if REQUIRED_VARIABLE not in user_prompt:
        errors.append(f"user_prompt precisa conter a variável {REQUIRED_VARIABLE}")
    if REQUIRED_VARIABLE in system_prompt:
        errors.append(f"{REQUIRED_VARIABLE} deve ficar só no user_prompt, não no system_prompt")

    # Garante que o template é válido (ex.: chaves { } soltas quebrariam a formatação)
    if not errors:
        try:
            variables = build_chat_prompt(prompt_data).input_variables
            if variables != ["bug_report"]:
                errors.append(f"Variáveis inesperadas no template: {variables}")
        except Exception as e:
            errors.append(f"Template inválido: {e}")

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Push do prompt otimizado ao LangSmith Hub")
    parser.add_argument(
        "-m", "--message", default="",
        help="Descrição do commit no Hub (ex.: o que mudou nesta iteração)",
    )
    args = parser.parse_args()

    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_FILE))
    if data is None:
        return 1

    prompt_data = data.get(PROMPT_KEY)
    if not prompt_data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}")
        return 1

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    if not push_prompt_to_langsmith(PROMPT_KEY, prompt_data, args.message):
        return 1

    print("\n✅ Push concluído com sucesso!")
    print("Próximo passo: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
