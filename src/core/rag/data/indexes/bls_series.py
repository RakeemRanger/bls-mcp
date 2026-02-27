from typing import Annotated
from dataclasses import field, dataclass
from uuid import uuid4

from semantic_kernel.data.vector import (
    DistanceFunction,
    vectorstoremodel,
    VectorStoreField,
    IndexKind
)


@vectorstoremodel
@dataclass
class BLSSeriesIndex:
    """
    Generic BLS Series Index for storing any BLS time series data.
    """
    seriesId: Annotated[str, VectorStoreField('key')] = field(default="")
    seriesType: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    displayName: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    timeStamp: Annotated[str, VectorStoreField('data')] = field(default="")
    seriesTitle: Annotated[str, VectorStoreField('data')] = field(default="")
    value: Annotated[str, VectorStoreField('data')] = field(default="")
    year: Annotated[str, VectorStoreField('data', is_indexed=True)] = field(default="")
    period: Annotated[str, VectorStoreField('data')] = field(default="")
    periodName: Annotated[str, VectorStoreField('data')] = field(default="")
    footnotes: Annotated[str, VectorStoreField('data')] = field(default="")