from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from core.domain import UOW
from core.services import ServicesContainer, create_services
from core.db import SessionLocal


class DependencyInjector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    app: Optional[FastAPI] = None
    services: ServicesContainer
    uow: UOW


_di_container: Optional[DependencyInjector] = None


def initialize_di_container(app: Optional[FastAPI] = None) -> DependencyInjector:
    """
    Initialize and return the DI container singleton.

    Args:
        app: Optional FastAPI application instance

    Returns:
        DependencyInjector instance with all dependencies configured
    """
    global _di_container

    if _di_container is not None:
        return _di_container

    services = create_services()
    uow = UOW(session_factory=SessionLocal)

    _di_container = DependencyInjector(
        app=app,
        services=services,
        uow=uow,
    )

    return _di_container


def get_di_container() -> DependencyInjector:
    """
    Get the current DI container instance.

    Returns:
        DependencyInjector instance

    Raises:
        RuntimeError: If container has not been initialized
    """
    if _di_container is None:
        raise RuntimeError(
            "DI container not initialized. Call initialize_di_container() first."
        )
    return _di_container
