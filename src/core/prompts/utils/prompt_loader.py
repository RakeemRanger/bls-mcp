from pathlib import Path

from configs.CONSTANTS import (
    RAG_PROMPTS_RELATIVE_PATH
)

class PromptLoader:
    """
    Prompt Templates Loader
    """
    def __init__(self):
        self.prompts_path = str(Path(RAG_PROMPTS_RELATIVE_PATH).resolve())
    
    def load_all_templates(self) -> None:
        pass


