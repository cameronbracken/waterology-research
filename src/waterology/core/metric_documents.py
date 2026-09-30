"""Read declared application metrics without changing Waterology's archive format."""

import json
from pathlib import Path
from typing import Literal

import yaml


class _UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError("Duplicate YAML metric key")
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def read_metric_value(path: Path, field: str, format: Literal["json", "yaml"] = "json") -> object:
    """Select a dotted mapping field; YAML tags cannot construct Python objects."""
    text = path.read_text(encoding="utf-8")
    if format == "json":
        value = json.loads(text)
    elif format == "yaml":
        try:
            value = yaml.load(text, Loader=_UniqueSafeLoader)
        except (yaml.YAMLError, RecursionError) as error:
            raise ValueError("Invalid YAML metric document") from error
    else:
        raise ValueError("Unsupported metric document format")
    for component in field.split("."):
        if not isinstance(value, dict) or component not in value:
            raise KeyError(component)
        value = value[component]
    if format == "yaml":
        # A selected YAML timestamp, set or recursive alias cannot enter the JSON
        # archive. Unrelated YAML metadata need not be JSON serializable.
        try:
            json.dumps(value, sort_keys=True)
        except RecursionError as error:
            raise ValueError("YAML metric exceeds supported nesting") from error
    return value
