from typing import Any, Dict, Mapping, Sequence


_MAX_STR_LEN = 200
_MAX_LIST_ITEMS = 10
_MAX_DICT_ITEMS = 20


def _format_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        value = " ".join(value.splitlines())
        if len(value) > _MAX_STR_LEN:
            return value[: _MAX_STR_LEN - 3] + "..."
        return value
    return str(value)


def _format_value(value: Any, *, indent: str) -> str:
    if isinstance(value, Mapping):
        items = list(value.items())
        shown = items[:_MAX_DICT_ITEMS]
        lines = []
        for k, v in shown:
            if isinstance(v, (Mapping, Sequence)) and not isinstance(v, (str, bytes, bytearray)):
                lines.append(f"{indent}{k}:")
                lines.append(_format_value(v, indent=indent + "  "))
            else:
                lines.append(f"{indent}{k}: {_format_scalar(v)}")
        if len(items) > _MAX_DICT_ITEMS:
            lines.append(f"{indent}... ({len(items) - _MAX_DICT_ITEMS} more)")
        return "\n".join(lines) if lines else f"{indent}{{}}"

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(value)
        shown = items[:_MAX_LIST_ITEMS]
        lines = []
        for item in shown:
            if isinstance(item, (Mapping, Sequence)) and not isinstance(item, (str, bytes, bytearray)):
                lines.append(f"{indent}-")
                lines.append(_format_value(item, indent=indent + "  "))
            else:
                lines.append(f"{indent}- {_format_scalar(item)}")
        if len(items) > _MAX_LIST_ITEMS:
            lines.append(f"{indent}... ({len(items) - _MAX_LIST_ITEMS} more)")
        return "\n".join(lines) if lines else f"{indent}[]"

    return f"{indent}{_format_scalar(value)}"


def print_mapping(mapping: Dict[str, Any]) -> None:
    for idx, (key, value) in enumerate(mapping.items()):
        if idx:
            print()

        if isinstance(value, (Mapping, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
            print(f"{key}:")
            print(_format_value(value, indent="  "))
        else:
            print(f"{key}: {_format_scalar(value)}")
