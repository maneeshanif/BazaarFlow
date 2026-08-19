"""Prompt loading utilities for LLM agents."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent

def load_prompt(category: str, filename: str = "system_prompt.md") -> str:
    """Load a prompt markdown file from app/prompts/<category>/<filename>."""
    prompt_path = PROMPTS_DIR / category / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
