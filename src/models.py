from pydantic import BaseModel, Field
from typing import Optional


class Trade(BaseModel):
    symbol: str = Field(..., description="Trading pair, e.g. BTCUSDT")
    order_id: str = Field(..., description="Unique order ID from Bybit")
    exec_id: str = Field(..., description="Unique execution ID from Bybit")
    side: str = Field(..., description="Buy or Sell")
    order_type: str = Field(..., description="Market or Limit")
    exec_price: str = Field(..., description="Execution price")
    exec_qty: str = Field(..., description="Execution quantity")
    exec_value: str = Field(..., description="Execution value in quote currency")
    exec_fee: str = Field(..., description="Execution fee")
    fee_currency: str = Field(..., description="Fee currency")
    exec_time: str = Field(..., description="Execution timestamp in ms")
    order_link_id: Optional[str] = Field(None, description="Custom order link ID")
    stop_order_type: Optional[str] = Field(None, description="Stop order type if applicable")
    category: str = Field(default="spot", description="Product category: spot, linear, inverse")


class SyncResult(BaseModel):
    success: bool
    new_trades: int
    total_fetched: int
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
