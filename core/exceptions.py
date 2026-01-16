
class ParserError(RuntimeError):
    """Base exception for all parser-related errors."""


class ParserConfigurationError(ParserError):
    """Raised when the parser is misconfigured."""


class ParserExecutionError(ParserError):
    """Raised when the parser fails during execution."""
