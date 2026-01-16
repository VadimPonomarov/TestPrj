from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional


@dataclass(slots=True)
class ProductData:
    """Typed payload returned by product parsers."""

    name: str = ""
    color: str = ""
    storage: str = ""
    manufacturer: str = ""
    price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    images: List[str] = field(default_factory=list)
    product_code: str = ""
    review_count: int = 0
    screen_diagonal: str = ""
    display_resolution: str = ""
    characteristics: Dict[str, str] = field(default_factory=dict)
    source_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ProductData":
        return cls(
            name=str(payload.get("name", "")) if payload.get("name") is not None else "",
            color=str(payload.get("color", "")) if payload.get("color") is not None else "",
            storage=str(payload.get("storage", "")) if payload.get("storage") is not None else "",
            manufacturer=str(payload.get("manufacturer", ""))
            if payload.get("manufacturer") is not None
            else "",
            price=_coerce_decimal(payload.get("price")),
            sale_price=_coerce_decimal(payload.get("sale_price")),
            images=list(payload.get("images", ()) or []),
            product_code=str(payload.get("product_code", ""))
            if payload.get("product_code") is not None
            else "",
            review_count=int(payload.get("review_count", 0) or 0),
            screen_diagonal=str(payload.get("screen_diagonal", ""))
            if payload.get("screen_diagonal") is not None
            else "",
            display_resolution=str(payload.get("display_resolution", ""))
            if payload.get("display_resolution") is not None
            else "",
            characteristics=dict(payload.get("characteristics", {}) or {}),
            source_url=str(payload.get("source_url", ""))
            if payload.get("source_url") is not None
            else "",
            metadata=dict(payload.get("metadata", {}) or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "storage": self.storage,
            "manufacturer": self.manufacturer,
            "price": self.price,
            "sale_price": self.sale_price,
            "images": list(self.images),
            "product_code": self.product_code,
            "review_count": self.review_count,
            "screen_diagonal": self.screen_diagonal,
            "display_resolution": self.display_resolution,
            "characteristics": dict(self.characteristics),
            "source_url": self.source_url,
            "metadata": dict(self.metadata),
        }

    def to_model_payload(self) -> Dict[str, Any]:
        payload = self.to_dict()
        return {
            key: value
            for key, value in payload.items()
            if value not in (None, "") or key in {"price", "sale_price", "review_count"}
        }


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
