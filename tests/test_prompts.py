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
def prompt():
    data = load_prompts(PROMPT_FILE)
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_FILE.name}"
    return data[PROMPT_KEY]


@pytest.fixture(scope="module")
def system_prompt(prompt):
    return prompt.get("system_prompt", "")


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt
        assert isinstance(prompt["system_prompt"], str)
        assert prompt["system_prompt"].strip()

    def test_prompt_has_role_definition(self, system_prompt):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        assert re.search(r"Você é (um|uma) [^.\n]{3,}", system_prompt), \
            "O system_prompt deve definir uma persona com 'Você é um/uma ...'"
        assert "product manager" in system_prompt.lower()

    def test_prompt_mentions_format(self, system_prompt):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        text = system_prompt.lower()
        assert "como um" in text and "eu quero" in text and "para que" in text, \
            "O prompt deve exigir o formato 'Como um..., eu quero..., para que...'"
        assert "critérios de aceitação" in text
        assert all(step in text for step in ("dado que", "quando", "então"))

    def test_prompt_has_few_shot_examples(self, system_prompt):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        examples = re.findall(r"## Exemplo \d+", system_prompt)
        assert len(examples) >= 2, "São necessários pelo menos 2 exemplos few-shot"
        assert system_prompt.count("Relato de bug:") >= len(examples), "Cada exemplo precisa de uma entrada"
        assert system_prompt.count("Resposta:") >= len(examples), "Cada exemplo precisa de uma saída"

    def test_prompt_no_todos(self, prompt):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        full_text = yaml.safe_dump(prompt, allow_unicode=True)
        assert "[TODO]" not in full_text
        # \b evita falso positivo com palavras como "TODOS"
        assert not re.search(r"\bTODO\b", full_text)

    def test_minimum_techniques(self, prompt):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt.get("techniques_applied", [])
        assert isinstance(techniques, list)
        assert len(techniques) >= 2
        assert any("few-shot" in t.lower() for t in techniques), "Few-shot Learning é obrigatório"

    def test_prompt_structure_is_valid(self, prompt):
        """Valida a estrutura com a função auxiliar de utils.py."""
        is_valid, errors = validate_prompt_structure(prompt)
        assert is_valid, errors

    def test_user_prompt_uses_bug_report_variable(self, prompt):
        """O user_prompt deve receber o relato via {bug_report}, e o system_prompt não."""
        assert "{bug_report}" in prompt.get("user_prompt", "")
        assert "{bug_report}" not in prompt["system_prompt"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
