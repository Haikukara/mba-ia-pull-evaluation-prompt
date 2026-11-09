"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    """Dados do prompt otimizado (v2)."""
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt_data):
    return prompt_data.get("system_prompt") or ""


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' não existe"
        assert prompt_data["system_prompt"].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        persona = re.search(r"Você é (um|uma) [^.\n]+", system_prompt)
        assert persona, "O system_prompt não define uma persona ('Você é um/uma ...')"

        roles = ["product owner", "product manager", "analista", "agile", "scrum"]
        assert any(role in persona.group(0).lower() for role in roles), (
            f"A persona definida não é de produto/agilidade: '{persona.group(0)}'"
        )

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "markdown" in text or "user story" in text, (
            "O prompt não menciona o formato de saída (Markdown ou User Story)"
        )
        # Estrutura padrão de User Story e critérios de aceitação
        for marker in ["Como um", "eu quero", "para que", "Critérios de Aceitação", "Dado que", "Quando", "Então"]:
            assert marker in system_prompt, f"O prompt não exige o elemento de formato: '{marker}'"

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        inputs = re.findall(r"^\s*Entrada:", system_prompt, flags=re.MULTILINE)
        outputs = re.findall(r"^\s*Saída:", system_prompt, flags=re.MULTILINE)
        assert len(inputs) >= 2, f"Few-shot exige ao menos 2 exemplos de entrada, encontrados: {len(inputs)}"
        assert len(inputs) == len(outputs), (
            f"Cada exemplo precisa de entrada e saída (entradas: {len(inputs)}, saídas: {len(outputs)})"
        )

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        full_text = yaml.safe_dump(prompt_data, allow_unicode=True)
        assert "[TODO]" not in full_text, "O prompt ainda contém marcadores [TODO]"
        assert "TODO" not in full_text, "O prompt ainda contém a palavra TODO"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert isinstance(techniques, list), "'techniques_applied' deve ser uma lista"
        assert len(techniques) >= 2, f"Mínimo de 2 técnicas, encontradas: {len(techniques)}"
        assert any("few-shot" in t.lower() for t in techniques), (
            "Few-shot Learning é obrigatório e deve constar em 'techniques_applied'"
        )

    def test_prompt_structure_is_valid(self, prompt_data):
        """Extra: valida a estrutura geral com a função de utils.py."""
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, f"Estrutura inválida: {errors}"

    def test_bug_report_only_in_user_prompt(self, prompt_data):
        """Extra: {bug_report} fica só no user prompt (na v1 estava duplicado)."""
        assert "{bug_report}" in prompt_data.get("user_prompt", ""), "user_prompt sem {bug_report}"
        assert "{bug_report}" not in prompt_data["system_prompt"], "{bug_report} duplicado no system_prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
