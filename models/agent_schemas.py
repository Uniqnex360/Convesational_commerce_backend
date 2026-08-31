from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentIntent(str, Enum):
    shopping_agent = "shopping_agent"
    compare_products = "compare_products"
    why_this_product = "why_this_product"
    check_fit = "check_fit"
    check_compatibility = "check_compatibility"
    find_alternatives = "find_alternatives"
    product_finder = "product_finder"
    product_question = "product_question"
    order = "order"
    delivery = "delivery"
    billing = "billing"
    store = "store"
    feedback = "feedback"


class RequirementSummary(BaseModel):
    category: Optional[str] = None
    quantity: Optional[int] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: Optional[str] = None
    use_case: Optional[str] = None
    hard_constraints: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    product_ids: List[str] = Field(default_factory=list)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    intent: Optional[AgentIntent] = None
    product_id: Optional[str] = None
    product_ids: List[str] = Field(default_factory=list)
    product_context: Optional[Dict[str, Any]] = None


class Evidence(BaseModel):
    claim: str
    source: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ProductCard(BaseModel):
    id: str
    title: str
    price: Optional[float] = None
    currency: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    available: Optional[bool] = None
    score: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    compromises: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class AgentBlock(BaseModel):
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    session_id: str
    intent: str
    message: str
    requirements: Optional[RequirementSummary] = None
    blocks: List[AgentBlock] = Field(default_factory=list)


class ProductSearchRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    requirements: Optional[RequirementSummary] = None
    limit: int = Field(default=10, ge=1, le=50)


class ProductSearchResponse(BaseModel):
    products: List[ProductCard] = Field(default_factory=list)
    total: int
    exact_match: bool = True


class CompareRequest(BaseModel):
    product_ids: List[str] = Field(..., min_length=2, max_length=5)
    requirements: Optional[RequirementSummary] = None


class ExplainRequest(BaseModel):
    requirements: Optional[RequirementSummary] = None


class FitRequest(BaseModel):
    requirements: RequirementSummary


class CompatibilityRequest(BaseModel):
    product_a: str
    product_b: str
