"""Schemas for transaction summary endpoint"""

from pydantic import BaseModel


class TopProduct(BaseModel):
    product: str
    count: int


class TransactionSummaryResponse(BaseModel):
    total_transactions: int
    total_products: int
    avg_products_per_purchase: float
    top_products: list[TopProduct]


class TransactionBasket(BaseModel):
    transaction_id: str
    products: list[str]


class TransactionBasketsResponse(BaseModel):
    baskets: list[TransactionBasket]
    total: int
