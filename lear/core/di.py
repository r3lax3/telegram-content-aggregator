from fastapi import FastAPI
from pydantic import BaseModel

from core.domain import UOW
from core.services import ServicesContainer


class DependencyInjector(BaseModel):
    app: FastAPI
    services: ServicesContainer
    uow: UOW
