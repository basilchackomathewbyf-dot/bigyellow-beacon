"""Edge AI gateway seam."""

from app.ai.gateway import AIGateway, FakeAIGateway, OllamaGateway, get_gateway, reset_gateway_cache

__all__ = [
    "AIGateway",
    "FakeAIGateway",
    "OllamaGateway",
    "get_gateway",
    "reset_gateway_cache",
]
