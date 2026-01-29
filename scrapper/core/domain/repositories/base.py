from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar


T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    def add(self, *args, **kwargs) -> T:
        ...

    @abstractmethod
    def get_one(self, id: int, **kwargs) -> Optional[T]:
        ...

    @abstractmethod
    def get_many(self, **kwargs) -> List[T]:
        ...

    @abstractmethod
    def update(self, id: int, **kwargs) -> None:
        ...

    @abstractmethod
    def delete(self, id: int) -> None:
        ...


class ChannelBaseRepository(ABC, Generic[T]):
    """
    Channel pk is not id, but username(str), created another ABC class
    """
    @abstractmethod
    def add(self, *args, **kwargs) -> T:
        ...

    @abstractmethod
    def get_one(self, username: str, **kwargs) -> Optional[T]:
        ...

    @abstractmethod
    def get_many(self, **kwargs) -> List[T]:
        ...

    @abstractmethod
    def update(self, username: str, **kwargs) -> None:
        ...

    @abstractmethod
    def delete(self, username: str) -> None:
        ...


class PostBaseRepository(ABC, Generic[T]):
    """
    Post have compound pk, created another ABC class
    """
    @abstractmethod
    def add(self, *args, **kwargs) -> T:
        ...

    @abstractmethod
    def get_one(self, id: int, channel_username: str, **kwargs) -> Optional[T]:
        ...

    @abstractmethod
    def get_many(self, **kwargs) -> List[T]:
        ...

    @abstractmethod
    def get_many_with_params(
        self,
        channel_username: str,
        limit: Optional[int] = None,
        order: str = "desc",
        marked: Optional[str] = None
    ):
        ...

    @abstractmethod
    def update(self, id: int, channel_username: str, **kwargs) -> None:
        ...

    @abstractmethod
    def delete(self, id: int, channel_username: str) -> None:
        ...
