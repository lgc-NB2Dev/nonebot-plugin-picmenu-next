"""Tests for templates.default."""

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pytest


async def test_default_template_render_uses_page_and_screenshot_pipeline(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Default rendering applies routes, visits the base page, and returns its image."""
    from nonebot_plugin_picmenu_next.templates import default

    events: list[tuple[str, object]] = []

    class FakePage:
        async def goto(self, url: str) -> None:
            events.append(("goto", url))

    class FakePageContext:
        async def __aenter__(self) -> FakePage:
            events.append(("enter", None))
            return FakePage()

        async def __aexit__(self, *_args: object) -> None:
            events.append(("exit", None))

    class FakeRouters:
        async def apply(self, page: FakePage) -> None:
            events.append(("apply", page))

    class FakeTemplate:
        async def render_async(self, **kwargs: object) -> str:
            events.append(("template", kwargs["cfg"]))
            return "<main>rendered</main>"

    async def fake_screenshot(
        page: FakePage,
        html: str,
        **kwargs: object,
    ) -> bytes:
        events.append(("screenshot", (page, html, kwargs)))
        return b"image"

    monkeypatch.setattr(default.jj_env, "get_template", lambda _name: FakeTemplate())
    monkeypatch.setattr(default, "get_new_page", lambda **_kwargs: FakePageContext())
    monkeypatch.setattr(default, "screenshot_html", fake_screenshot)

    msg = await default.render("fake.html.jinja", cast("Any", FakeRouters()))

    assert events[0][0] == "template"
    assert [event[0] for event in events] == [
        "template",
        "enter",
        "apply",
        "goto",
        "screenshot",
        "exit",
    ]
    assert msg


async def test_default_template_entry_points_forward_view_arguments(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Index, detail, and function detail entry points select their expected templates."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNPluginInfo,
    )
    from nonebot_plugin_picmenu_next.templates import default

    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_render(
        template: str, _routers: object, **kwargs: object
    ) -> UniMessage:
        calls.append((template, kwargs))
        return UniMessage("rendered")

    info = PMNPluginInfo(name="plugin")
    func = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="function",
        detail_des="function",
    )
    monkeypatch.setattr(default, "render", fake_render)

    await default.render_index(
        infos=[info],
        showing_hidden=False,
        user_can_see_hidden=None,
    )
    await default.render_detail(
        info=info,
        info_index=0,
        showing_hidden=True,
        user_can_see_hidden=True,
    )
    await default.render_func_detail(
        info=info,
        info_index=0,
        func=func,
        func_index=None,
        showing_hidden=True,
        user_can_see_hidden=True,
    )

    assert [template for template, _kwargs in calls] == [
        "index.html.jinja",
        "detail.html.jinja",
        "detail.html.jinja",
    ]
    assert calls[0][1]["infos"] == [info]
    assert calls[1][1]["info_index"] == 0
    assert calls[2][1]["func"] is func


async def test_default_template_routes_resolve_katex_and_static_resource_paths(
    picmenu_plugin: object,
) -> None:
    """The default template route table resolves Markdown and bundled resources."""
    from nonebot_plugin_picmenu_next.templates import default
    from nonebot_plugin_picmenu_next.templates.pw_utils import ROUTE_BASE_URL
    from yarl import URL

    class FakeRoute:
        def __init__(self) -> None:
            self.fulfill_calls: list[dict[str, object]] = []

        async def fulfill(self, **kwargs: object) -> None:
            self.fulfill_calls.append(kwargs)

    async def call_route(pattern: str, path: str) -> FakeRoute:
        router = next(
            item for item in default.base_routers.routers if item.pattern == pattern
        )
        route = FakeRoute()
        await router.func(
            route=cast("Any", route),
            request=cast("Any", object()),
            info=router,
            url=URL(f"{ROUTE_BASE_URL}{path}"),
            matched=None,
        )
        return route

    markdown_route = await call_route(f"{ROUTE_BASE_URL}/markdown/**/*", "/markdown/x")
    static_route = await call_route(f"{ROUTE_BASE_URL}/**/*", "/res/x")

    assert markdown_route.fulfill_calls
    assert static_route.fulfill_calls


def test_default_template_config_uses_the_first_command_start_as_its_prefix(
    picmenu_plugin: object,
) -> None:
    """Template configuration exposes a command prefix for builtin examples."""
    from nonebot_plugin_picmenu_next.templates.default import TemplateConfigModel

    assert TemplateConfigModel(command_start={"!"}).pfx == "!"
