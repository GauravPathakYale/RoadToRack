"""API router aggregator."""

from fastapi import APIRouter

from app.api.v1 import simulation, configuration, metrics, websocket

api_router = APIRouter()

api_router.include_router(simulation.router)
api_router.include_router(configuration.router)
api_router.include_router(metrics.router)
api_router.include_router(websocket.router)
