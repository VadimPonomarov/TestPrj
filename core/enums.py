from enum import Enum


class ParserType(Enum):
    """Supported parser backends."""

    BS4 = "bs4"
    SELENIUM = "selenium"
    PLAYWRIGHT = "playwright"

    @classmethod
    def from_string(cls, value: str) -> "ParserType":
        try:
            return cls(value.lower())
        except ValueError as exc:  # pragma: no cover - defensive
            allowed = ", ".join(member.value for member in cls)
            raise ValueError(f"Unknown parser type '{value}'. Allowed values: {allowed}.") from exc
