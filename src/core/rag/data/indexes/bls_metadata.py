from typing import Annotated
from dataclasses import field, dataclass

from semantic_kernel.data.vector import (
    vectorstoremodel,
    VectorStoreField,
)


@vectorstoremodel
@dataclass
class BLSSeriesMetadata:
    """
    Metadata index for BLS series definitions, descriptions, and reference data.
    Used for series discovery and query understanding.
    """
    seriesId: Annotated[str, VectorStoreField('key')] = field(default="")
    
    # Core metadata
    name: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    description: Annotated[str, VectorStoreField('data')] = field(default="")
    category: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")  # unemployment, employment, wage, etc.
    level: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")  # national, state, county
    
    # Geographic info (for state/county)
    fips: Annotated[str, VectorStoreField('data')] = field(default="")
    state: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    county: Annotated[str, VectorStoreField('data')] = field(default="")
    
    # Additional details
    seasonal_adjustment: Annotated[str, VectorStoreField('data')] = field(default="")
    measure_type: Annotated[str, VectorStoreField('data')] = field(default="")  # rate, level, index
    frequency: Annotated[str, VectorStoreField('data')] = field(default="monthly")
    
    # Searchable text for semantic matching
    searchable_text: Annotated[str, VectorStoreField('data')] = field(default="")


@vectorstoremodel
@dataclass
class BLSSeriesPattern:
    """
    Pattern definitions for constructing series IDs dynamically.
    """
    patternId: Annotated[str, VectorStoreField('key')] = field(default="")
    category: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    level: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    pattern: Annotated[str, VectorStoreField('data')] = field(default="")
    description: Annotated[str, VectorStoreField('data')] = field(default="")
    example: Annotated[str, VectorStoreField('data')] = field(default="")
