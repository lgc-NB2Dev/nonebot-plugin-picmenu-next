"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, ClassVar, cast

from arclet.alconna import Alconna, CommandMeta, command_manager
from nonebot.adapters import Bot, Event

if TYPE_CHECKING:
    import pytest


def teardown_function() -> None:
    for command in command_manager.get_commands():
        if "-picmenu" in command.path:
            command_manager.delete(command)


def _owned_command(name: str, plugin_id: str) -> Alconna:
    command = Alconna(name, meta=CommandMeta(description=f"{name} description"))
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id=plugin_id)
    return command


async def _inject_context(_dependent: object) -> Bot:
    return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))


async def test_command_handler_finishes_each_user_facing_terminal_path(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """The Help matcher terminates with its dedicated image, message, and text views."""
    import pytest
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    class FinishedError(Exception):
        pass

    class FakeUniMessage:
        messages: ClassVar[list[str]] = []

        @classmethod
        def image(cls, **_kwargs: object) -> "FakeUniMessage":
            cls.messages.append("image")
            return cls()

        @classmethod
        def text(cls, text: str) -> "FakeUniMessage":
            cls.messages.append(text)
            return cls()

        async def finish(self, **_kwargs: object) -> None:
            raise FinishedError

    class FakeMessage:
        async def finish(self) -> None:
            raise FinishedError

    def query(*, value: object) -> object:
        return SimpleNamespace(result=value)

    async def denied(_bot: object, _event: object) -> bool:
        return False

    async def no_result(*_args: object, **_kwargs: object) -> object:
        return None, None, None

    monkeypatch.setattr(main, "UniMessage", FakeUniMessage)
    monkeypatch.setattr(main.config, "only_superuser_see_hidden", True)
    monkeypatch.setattr(main, "SUPERUSER", denied)
    monkeypatch.setattr(main, "render_menu", no_result)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value=None),
            query(value=None),
            query(value=True),
        )
    assert FakeUniMessage.messages == ["image", "不是主人不给看"]

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", False)
    FakeUniMessage.messages.clear()
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value=None),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages == ["当前貌似没有任何可用的插件信息呢……"]

    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="missing"),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages[-1] == "好像没有找到对应插件呢……"

    item = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="brief",
        detail_des="detail",
    )
    info = PMNPluginInfo(name="plugin", pm_data=[item])

    async def missing_function(*_args: object, **_kwargs: object) -> object:
        return None, info, None

    monkeypatch.setattr(main, "render_menu", missing_function)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value="missing"),
            query(value=False),
        )
    assert "对应功能" in FakeUniMessage.messages[-1]

    async def no_detail(*_args: object, **_kwargs: object) -> object:
        return None, PMNPluginInfo(name="plugin"), None

    monkeypatch.setattr(main, "render_menu", no_detail)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages[-1] == "插件 `plugin` 没有详细功能介绍哦"

    async def rendered(*_args: object, **_kwargs: object) -> object:
        return FakeMessage(), PMNPluginInfo(name="plugin"), item

    monkeypatch.setattr(main, "render_menu", rendered)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value="function"),
            query(value=False),
        )
