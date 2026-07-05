from dataclasses import dataclass


@dataclass
class ScanResult:
    ticker: str
    price: float

    mode: str              # SWING / POSITION / IDLE
    trend: str

    rsi: float

    confidence: int = 0

    sector: str = ""

    action: str = ""

    sell_strike: int | None = None
    buy_strike: int | None = None