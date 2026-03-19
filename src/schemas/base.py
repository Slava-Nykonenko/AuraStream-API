from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    total_items: int
    total_pages: int
    prev_page: Optional[str] = None
    next_page: Optional[str] = None
    items: List[T]
