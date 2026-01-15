from dataclasses import dataclass
from datetime import datetime
from typing import Literal

LiquidityType = Literal["BUY", "SELL"]

@dataclass
class LiquidityLevel:
    price: float
    type: LiquidityType
    timestamp: datetime
    mitigated: bool = False
