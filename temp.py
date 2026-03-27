
from typing import Optional, List, Tuple, TypeVar, Generic, Any, Protocol, runtime_checkable
from collections import deque

T_NEXT = TypeVar("T")

@runtime_checkable
class HasNext(Protocol):
    next: Optional[Any]
    val: Any
