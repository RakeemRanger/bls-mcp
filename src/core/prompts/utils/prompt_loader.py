from pathlib import Path

from configs.CONSTANTS import (
    PROMPT_RELATIVE_PATH
)

class PromptLoader:
    """
    Prompt Templates Loader
    """
    def __init__(self, ):
        self.prompts_path = prompt_absolute_path = str(Path(PROMPT_RELATIVE_PATH).resolve())
    
    def load_all_templates(self, ) -> None:
        pass


