from collections.abc import Mapping


class WaterologyError(RuntimeError):
    code = "waterology_error"

    def __init__(self, message: str, details: Mapping[str, object] | None = None) -> None:
        self.details = dict(details or {})
        super().__init__(message)

    def payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "details": self.details,
            "message": str(self),
        }


class InvalidInputError(WaterologyError):
    code = "invalid_input"
