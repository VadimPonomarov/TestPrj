from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass
class Product:
    name: str
    color: str
    storage: str
    manufacturer: str
    price: Optional[Decimal]
    sale_price: Optional[Decimal]
    images: List[str] = field(default_factory=list)
    product_code: str = ""
    review_count: int = 0
    screen_diagonal: str = ""
    display_resolution: str = ""
    characteristics: Dict[str, str] = field(default_factory=dict)
    source_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
