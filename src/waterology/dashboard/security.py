import ipaddress
import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

from starlette.exceptions import HTTPException
from starlette.requests import Request

from waterology.core.errors import WaterologyError


class DashboardSecurityError(WaterologyError):
    code = "dashboard_security_error"


@dataclass(frozen=True)
class DashboardAccess:
    host: str
    remote: bool
    access_token: str | None


def dashboard_access(
    host: str,
    *,
    allow_remote: bool,
    access_token: str | None,
) -> DashboardAccess:
    remote = not _is_loopback(host)
    if remote and not allow_remote:
        raise DashboardSecurityError("A non-loopback host requires explicit remote access")
    token = access_token.strip() if access_token else None
    if remote and not token:
        raise DashboardSecurityError("Remote dashboard access requires an access token")
    return DashboardAccess(host=host, remote=remote, access_token=token)


async def require_action(
    request: Request,
    *,
    action_token: str,
    confirmation: str,
) -> dict[str, str]:
    origin = request.headers.get("origin")
    expected = str(request.base_url).rstrip("/")
    if origin is None or not secrets.compare_digest(origin.rstrip("/"), expected):
        raise HTTPException(403, "Dashboard actions require a matching origin")
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        raise HTTPException(415, "Dashboard actions require URL encoded forms")
    body = await request.body()
    if len(body) > 65_536:
        raise HTTPException(413, "Dashboard action form is too large")
    try:
        values = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(400, "Dashboard action form is invalid") from error
    form = {name: items[-1] for name, items in values.items()}
    supplied_token = form.get("action_token", "")
    if not secrets.compare_digest(supplied_token, action_token):
        raise HTTPException(403, "Dashboard action token is invalid")
    if form.get("confirm") != confirmation:
        raise HTTPException(400, f"Dashboard action requires confirmation: {confirmation}")
    return form


def token_matches(supplied: str | None, expected: str) -> bool:
    return supplied is not None and secrets.compare_digest(supplied, expected)


def request_host_allowed(host_header: str | None, configured_host: str) -> bool:
    if not host_header or any(character.isspace() for character in host_header):
        return False
    try:
        parsed = urlsplit(f"//{host_header}")
        request_host = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False
    if request_host is None or parsed.username or parsed.password or parsed.path:
        return False
    if configured_host in {"0.0.0.0", "::"}:
        try:
            ipaddress.ip_address(request_host)
        except ValueError:
            return False
        return True
    if _is_loopback(configured_host):
        return _is_loopback(request_host)
    return secrets.compare_digest(request_host.casefold(), configured_host.casefold())


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
