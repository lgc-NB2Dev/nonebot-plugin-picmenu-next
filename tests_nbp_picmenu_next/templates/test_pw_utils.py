"""Tests for templates.pw_utils."""

from pathlib import Path
from typing import Any, cast


def test_local_file_route_transformer_quotes_full_resource_path(
    picmenu_plugin: object,
    tmp_path: Path,
) -> None:
    """The local-file renderer receives an encoded absolute resource path."""
    from nonebot_plugin_picmenu_next.templates.pw_utils import (
        local_file_route_prp_transformer,
    )

    result = local_file_route_prp_transformer(
        "asset with space.png",
        tmp_path,
        cast("Any", object()),
        cast("Any", object()),
    )

    assert result.startswith("/local-file?path=")
    assert "%20" in result


async def test_base_routes_serve_html_and_resolve_local_file_paths(
    picmenu_plugin: object,
    tmp_path: Path,
) -> None:
    """The base router fulfils the shell document and an existing local file."""
    from nonebot_plugin_picmenu_next.templates import pw_utils
    from yarl import URL

    class FakeRoute:
        def __init__(self) -> None:
            self.fulfill_calls: list[dict[str, object]] = []

        async def fulfill(self, **kwargs: object) -> None:
            self.fulfill_calls.append(kwargs)

    async def call_route(index: int, url: URL) -> FakeRoute:
        router = pw_utils.base_routers.routers[index]
        route = FakeRoute()
        await router.func(
            route=cast("Any", route),
            request=cast("Any", object()),
            info=router,
            url=url,
            matched=None,
        )
        return route

    asset = tmp_path / "asset.txt"
    asset.write_text("asset", encoding="utf-8")
    root = await call_route(0, URL(f"{pw_utils.ROUTE_BASE_URL}/"))
    local_file = await call_route(
        1,
        URL(f"{pw_utils.ROUTE_BASE_URL}/local-file?path={asset.as_posix()}"),
    )

    assert root.fulfill_calls == [
        {"content_type": "text/html", "body": "<html></html>"}
    ]
    assert local_file.fulfill_calls == [{"path": asset.resolve()}]
