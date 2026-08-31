from typing import Optional

from fastapi import APIRouter, Header

from models.agent_schemas import (
    AgentChatRequest,
    AgentChatResponse,
    CompatibilityRequest,
    CompareRequest,
    ExplainRequest,
    FitRequest,
    ProductSearchRequest,
    ProductSearchResponse,
    RequirementSummary,
)

from services.auth import check_rate_limit, verify_api_key
from services.shopnexai.orchestrator import ShopNexAIOrchestrator


router = APIRouter()

shopnexai = ShopNexAIOrchestrator()


def _authenticate(x_api_key: str):
    config = verify_api_key(x_api_key)

    check_rate_limit(
        x_api_key,
        config.get("rate_limit", 100),
    )

    return config


@router.post(
    "/agent/chat",
    response_model=AgentChatResponse,
)
async def agent_chat(
    request: AgentChatRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return await shopnexai.process_chat(
        message=request.message,
        session_id=request.session_id,
        forced_intent=request.intent,
        product_id=request.product_id,
        product_ids=request.product_ids,
        product_context=request.product_context,
        api_key=x_api_key,
    )


@router.post(
    "/products/search",
    response_model=ProductSearchResponse,
)
async def agent_product_search(
    request: ProductSearchRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return await shopnexai.search_products(
        query=request.query,
        requirements=request.requirements,
        limit=request.limit,
    )


@router.post("/products/compare")
async def compare_products(
    request: CompareRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return await shopnexai.compare_products(
        request.product_ids,
        request.requirements,
    )


@router.post(
    "/products/{product_id}/explain",
    response_model=AgentChatResponse,
)
async def explain_product(
    product_id: str,
    request: Optional[ExplainRequest] = None,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return await shopnexai.explain_product(
        product_id,
        request.requirements if request else None,
    )


@router.post("/products/{product_id}/fit")
async def fit_product(
    product_id: str,
    request: FitRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return shopnexai.fit_product(
        product_id,
        request.requirements,
    )


@router.post("/compatibility/check")
async def check_compatibility(
    request: CompatibilityRequest,
    x_api_key: str = Header(
        ...,
        alias="X-API-Key",
    ),
):
    _authenticate(x_api_key)

    return shopnexai.check_compatibility(
        request.product_a,
        request.product_b,
    )