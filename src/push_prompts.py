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
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPT_NAME = "bug_to_user_story_v2"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_NAME}.yml"

# Variável de entrada usada pelo dataset de avaliação
REQUIRED_INPUT_VARIABLES = {"bug_report"}


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """Monta o ChatPromptTemplate (system + user) a partir dos dados do YAML."""
    return ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])


def build_readme(prompt_data: dict) -> str:
    """Gera o README exibido na página do prompt no Hub."""
    techniques = "\n".join(f"- {t}" for t in prompt_data.get("techniques_applied", []))
    return (
        f"# {PROMPT_NAME}\n\n"
        f"{prompt_data.get('description', '')}\n\n"
        f"**Versão:** {prompt_data.get('version', '')}\n\n"
        f"## Técnicas aplicadas\n\n{techniques}\n\n"
        f"## Entrada\n\n- `bug_report`: relato de bug em texto livre\n"
    )


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_identifier = f"{username}/{prompt_name}"

    techniques = prompt_data.get("techniques_applied", [])
    # Tags do Hub: tags do YAML + técnicas aplicadas (normalizadas) + versão
    tags = list(dict.fromkeys(
        list(prompt_data.get("tags", []))
        + [t.lower().replace(" ", "-") for t in techniques]
        + [prompt_data.get("version", "")]
    ))
    tags = [t for t in tags if t]

    try:
        prompt = build_chat_prompt(prompt_data)
        print(f"Fazendo push: {prompt_identifier}")

        url = Client().push_prompt(
            prompt_identifier,
            object=prompt,
            is_public=True,
            description=prompt_data.get("description", ""),
            readme=build_readme(prompt_data),
            tags=tags,
            commit_description=prompt_data.get("changelog", f"Versão {prompt_data.get('version', '')}"),
        )

        print(f"   ✓ Push concluído (público)")
        print(f"   ✓ Tags: {', '.join(tags)}")
        print(f"   ✓ {url}")
        return True

    except Exception as e:
        message = str(e)
        print(f"❌ Erro ao fazer push de '{prompt_identifier}': {message}")
        if "nothing to commit" in message.lower() or "409" in message:
            print("   (O conteúdo do prompt não mudou desde o último commit.)")
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)

    if not str(prompt_data.get("user_prompt", "")).strip():
        errors.append("user_prompt está vazio")

    if errors:
        return False, errors

    # Garante que o template compila e expõe exatamente a variável do dataset
    try:
        input_variables = set(build_chat_prompt(prompt_data).input_variables)
    except Exception as e:
        return False, [f"Template inválido: {e}"]

    if input_variables != REQUIRED_INPUT_VARIABLES:
        errors.append(
            f"Variáveis do template devem ser {sorted(REQUIRED_INPUT_VARIABLES)}, "
            f"encontradas: {sorted(input_variables)} "
            "(chaves literais precisam ser escapadas como {{ }})"
        )

    return (len(errors) == 0, errors)


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(str(PROMPT_PATH))
    if not data or PROMPT_NAME not in data:
        print(f"❌ Prompt '{PROMPT_NAME}' não encontrado em {PROMPT_PATH}")
        return 1

    prompt_data = data[PROMPT_NAME]

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("   ✓ Prompt validado")

    return 0 if push_prompt_to_langsmith(PROMPT_NAME, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
