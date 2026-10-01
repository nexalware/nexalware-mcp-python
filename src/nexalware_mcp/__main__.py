from __future__ import annotations

import functools
import os
import sys
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from nexalware import NexalwareApiError, NexalwareClient, make_tools

from . import __version__


def _translate_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """MCPServer shows a raised ToolError's message to the model, but
    scrubs any other exception down to "Error executing tool <name>" by
    design, to avoid leaking internals by default. A NexalwareApiError is
    exactly the "anticipated failure" case that message is meant for
    (a 403 with no grant, a 404 for a bad deviceId, etc.), so translate it
    instead of letting it get swallowed. functools.wraps preserves the
    original signature/docstring via __wrapped__, which is what
    MCPServer's schema builder actually introspects.
    """

    @functools.wraps(fn)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except NexalwareApiError as err:
            raise ToolError(f"{err.error}: {err.message}" if err.message else err.error) from err

    return wrapped


def main() -> None:
    api_key = os.environ.get("NEXALWARE_API_KEY")
    if not api_key:
        print(
            "NEXALWARE_API_KEY is not set. Create a key on the Nexalware dashboard "
            "(Settings -> API Keys), scope it to the device(s) this agent should "
            "control, and pass it as this environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = NexalwareClient(
        api_key=api_key,
        base_url=os.environ.get("NEXALWARE_API_URL", "https://api.nexalware.com"),
    )

    server = MCPServer(name="nexalware", version=__version__)

    for tool_fn in make_tools(client):
        server.add_tool(_translate_errors(tool_fn))

    server.run("stdio")


if __name__ == "__main__":
    main()
