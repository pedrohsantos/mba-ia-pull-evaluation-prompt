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
from datetime import date
from pathlib import Path
import yaml
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()


def _str_representer(dumper, value):
    """Grava textos com várias linhas no estilo bloco (|) para manter o YAML legível."""
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


yaml.add_representer(str, _str_representer)

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
PROMPT_KEY = "bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).parent.parent / "prompts" / f"{PROMPT_KEY}.yml"


def prompt_to_dict(prompt: ChatPromptTemplate) -> dict:
    """Converte o ChatPromptTemplate no formato de dicionário usado nos YAMLs."""
    system_prompt = ""
    user_prompt = ""

    for message in prompt.messages:
        if isinstance(message, SystemMessagePromptTemplate):
            system_prompt = message.prompt.template
        elif isinstance(message, HumanMessagePromptTemplate):
            user_prompt = message.prompt.template

    return {
        "description": "Prompt para converter relatos de bugs em User Stories",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "input_variables": list(prompt.input_variables),
        # Metadados
        "version": "v1",
        "source": SOURCE_PROMPT,
        "pulled_at": date.today().isoformat(),
        "tags": ["bug-analysis", "user-story", "product-management"],
    }


def pull_prompts_from_langsmith() -> bool:
    """Faz pull do prompt semente e o salva em prompts/bug_to_user_story_v1.yml."""
    client = Client()

    print(f"Puxando prompt: {SOURCE_PROMPT}")
    prompt = client.pull_prompt(SOURCE_PROMPT, dangerously_pull_public_prompt=True)
    print(f"   ✓ Prompt carregado ({len(prompt.messages)} mensagens, "
          f"variáveis: {', '.join(prompt.input_variables)})")

    if not save_yaml({PROMPT_KEY: prompt_to_dict(prompt)}, str(OUTPUT_PATH)):
        return False

    print(f"   ✓ Salvo em prompts/{OUTPUT_PATH.name}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    try:
        return 0 if pull_prompts_from_langsmith() else 1
    except Exception as e:
        print(f"❌ Erro ao fazer pull de '{SOURCE_PROMPT}': {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
