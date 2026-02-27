from pathlib import Path

from rag.retrieval.retrieval import RetrievalManager
from rag.augmented.aug import AugmentationManager
from rag.generation.gen import GenerationManager
from configs.CONSTANTS import (
    PROMPT_RELATIVE_PATH
)

prompt_absolute_path = str(Path(PROMPT_RELATIVE_PATH).resolve())

class RagResults:
    """
    Returns RAG results
    """
    pass