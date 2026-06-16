from contextlib import suppress
from typing import TYPE_CHECKING

from arclet.alconna import (
    ANY,
    Arg,
    Args,
    Empty,
    Option,
    Subcommand,
    TextFormatter,
    command_manager,
)
from arclet.alconna.typing import AllParam, InnerShortcutArgs
from cookit.loguru import warning_suppress
from cookit.pyd import type_validate_python
from nonebot import logger
from nonebot.matcher import MatcherSource

from .models import OptionalPMDataItem, PMDataItem, PMNPluginInfo

if TYPE_CHECKING:
    from arclet.alconna import Alconna
    from arclet.alconna.formatter import Trace

ALCONNA_EXTRA_KEY = "pmn"


def fenced_code(text: str, lang: str = "text") -> str:
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{lang}\n{text.strip()}\n{fence}"


def inline_code(text: object) -> str:
    escaped = str(text).replace("`", "\\`")
    return f"`{escaped}`"


class PMNMarkdownTextFormatter(TextFormatter):
    def format(self, trace: "Trace") -> str:
        parts: list[str] = []
        if description := trace.head.get("description"):
            parts.append(description)

        command = self.command(trace)
        if command:
            parts.extend(("", "**指令**", "", fenced_code(command)))

        if usage := trace.head.get("usage"):
            parts.extend(("", "**用法**", "", fenced_code(usage)))

        if args := self.args(trace.args):
            parts.extend(("", "**参数**", "", args))

        if body := self.body(trace.body):
            parts.extend(("", body))

        if example := trace.head.get("example"):
            parts.extend(("", "**示例**", "", fenced_code(example, "shell")))

        if shortcuts := self.shortcut(trace.shortcuts):
            parts.extend(("", shortcuts))

        return "\n".join(parts).strip()

    def command(self, trace: "Trace") -> str:
        params = self.parameters(trace.args)
        return f"{trace.head['name']}{trace.separators[0]}{params}".strip()

    def param(self, parameter: Arg) -> str:
        name = parameter.name
        if str(parameter.value).strip("'\"") == name or parameter.hidden:
            text = name
        elif parameter.value is AllParam:
            text = f"...{name}"
        else:
            text = name
            if parameter.value is not ANY:
                text += f": {parameter.value}"
            if parameter.field.display is not Empty:
                text += f" = {parameter.field.display}"
        left, right = ("[", "]") if parameter.optional else ("<", ">")
        return f"{left}{text}{right}"

    def parameters(self, args: Args) -> str:
        result = ""
        for arg in args.argument:
            if arg.name.startswith("_key_"):
                continue
            if len(arg.separators) == 1:
                sep = " " if arg.separators[0] == " " else f" {arg.separators[0]!r} "
            else:
                sep = f"[{'|'.join(arg.separators)!r}]"
            result += self.param(arg) + sep
        return result.strip()

    def args(self, args: Args) -> str:
        lines = []
        for arg in args.argument:
            if arg.name.startswith("_key_"):
                continue
            details = []
            if arg.value is not ANY and str(arg.value).strip("'\"") != arg.name:
                details.append(f"类型：{inline_code(arg.value)}")
            details.append("可选" if arg.optional else "必填")
            if arg.field.display is not Empty:
                details.append(f"默认值：{inline_code(arg.field.display)}")
            if arg.notice:
                details.append(arg.notice)
            lines.append(f"- {inline_code(arg.name)}：{'；'.join(details)}")
        return "\n".join(lines)

    def option_signature(self, node: Option | Subcommand, prefix: str = "") -> str:
        aliases = list(dict.fromkeys([node.name, *sorted(node.aliases)]))
        alias_text = " / ".join(aliases)
        params = self.parameters(node.args)
        sep = next(iter(node.separators)) if params else ""
        return f"{prefix}{alias_text}{sep}{params}".strip()

    def format_option(self, node: Option, prefix: str = "") -> str:
        help_text = "无说明" if node.help_text == node.dest else node.help_text
        return f"- {inline_code(self.option_signature(node, prefix))}：{help_text}"

    def format_subcommand(self, node: Subcommand, prefix: str = "") -> list[str]:
        signature = self.option_signature(node, prefix)
        help_text = "无说明" if node.help_text == node.dest else node.help_text
        lines = [f"- {inline_code(signature)}：{help_text}"]
        next_prefix = f"{signature} "
        for child in node.options:
            if isinstance(child, Subcommand):
                lines.extend(self.format_subcommand(child, next_prefix))
            elif isinstance(child, Option) and child.name not in self.ignore_names:
                lines.append(self.format_option(child, next_prefix))
        return lines

    def body(self, parts: list[Option | Subcommand]) -> str:
        subcommands: list[str] = []
        options: list[str] = []
        for node in parts:
            if isinstance(node, Subcommand):
                subcommands.extend(self.format_subcommand(node))
            elif isinstance(node, Option) and node.name not in self.ignore_names:
                options.append(self.format_option(node))

        result = []
        if subcommands:
            result.extend(("**子命令**", "", "\n".join(subcommands)))
        if options:
            if result:
                result.append("")
            result.extend(("**选项**", "", "\n".join(options)))
        return "\n".join(result)

    def shortcut(self, shortcuts: dict[str, object]) -> str:
        if not shortcuts:
            return ""
        lines = []
        for key, shortcut in shortcuts.items():
            if isinstance(shortcut, InnerShortcutArgs):
                display_key = key + (" ...args" if shortcut.fuzzy else "")
                prefix = next((x for x in shortcut.prefixes if isinstance(x, str)), "")
                target = " ".join(str(x) for x in (shortcut.command, *shortcut.args))
                lines.append(
                    f"- {inline_code(f'{prefix}{display_key}')} => "
                    f"{inline_code(f'{prefix}{target}'.strip())}",
                )
            else:
                lines.append(f"- {inline_code(key)} => {inline_code(shortcut)}")
        return "\n".join(("**快捷指令**", "", "\n".join(lines)))


def get_alconna_plugin_id(command: "Alconna") -> str | None:
    source: MatcherSource | None = command.meta.extra.get("matcher.source")
    return getattr(source, "plugin_id", None) if source else None


def format_alconna_help_text(command: "Alconna", markdown: bool = False) -> str:
    if markdown and type(command.formatter) is TextFormatter:
        return PMNMarkdownTextFormatter().add(command).format_node()
    return command.get_help()


def format_alconna_trigger_method(
    command: "Alconna",
    markdown: bool = False,
) -> str:
    command_name = str(command.command)
    prefix = next((x for x in command.prefixes if isinstance(x, str)), "")
    triggers = [f"{prefix}{command_name}"]
    with suppress(ValueError):
        for key, shortcut in command_manager.get_shortcut(command).items():
            if isinstance(shortcut, InnerShortcutArgs) and shortcut.prefixes:
                prefix = next(
                    (x for x in shortcut.prefixes if isinstance(x, str)),
                    "",
                )
                triggers.append(f"{prefix}{key}")
            else:
                triggers.append(key)
    triggers = list(dict.fromkeys(x for x in triggers if x))
    if markdown:
        triggers = [f"`{x}`" for x in triggers]
    return "│".join(triggers)


def get_alconna_menu_overrides(command: "Alconna") -> OptionalPMDataItem:
    with warning_suppress(
        f"Failed to parse PicMenu Alconna command extra of {command.path}",
    ):
        return type_validate_python(
            OptionalPMDataItem,
            command.meta.extra.get(ALCONNA_EXTRA_KEY) or {},
        )
    return OptionalPMDataItem()


def generate_alconna_menu_item(
    command: "Alconna",
    markdown: bool = False,
) -> PMDataItem:
    description = command.meta.description
    overrides = get_alconna_menu_overrides(command)
    item = PMDataItem(
        func=overrides.func or str(command.command),
        trigger_method=(
            overrides.trigger_method or format_alconna_trigger_method(command, markdown)
        ),
        trigger_condition=overrides.trigger_condition or "指令",
        brief_des=overrides.brief_des or description,
        detail_des=(
            overrides.detail_des
            or format_alconna_help_text(command, markdown)
            or (f"用法：\n{u}" if (u := command.meta.usage) else None)
            or "暂无"
        ),
        pmn_hidden=(
            overrides.hidden if overrides.hidden is not None else command.meta.hide
        ),
        pmn_template=overrides.template,
    )
    item._alc_cmd_id = command.path  # noqa: SLF001
    return item


def collect_alconna_menu_data(
    plugin_ids: set[str],
    markdown_plugin_ids: set[str],
) -> dict[str, list[PMDataItem]]:
    result: dict[str, list[PMDataItem]] = {}
    for command in command_manager.get_commands():
        if command_manager.is_disable(command) or not (
            plugin_id := get_alconna_plugin_id(command)
        ):
            continue
        if plugin_id not in plugin_ids:
            continue
        result.setdefault(plugin_id, []).append(
            generate_alconna_menu_item(command, plugin_id in markdown_plugin_ids),
        )
    return result


def apply_alconna_command_infos(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
    plugin_ids = {
        info.plugin_id
        for info in infos
        if info.plugin_id and (info.pm_data is None or info.pmn.alc_force_enable_detect)
    }
    if not plugin_ids:
        return infos

    markdown_plugin_ids = {
        info.plugin_id
        for info in infos
        if info.plugin_id in plugin_ids and info.pmn.markdown
    }
    alconna_menu_data = collect_alconna_menu_data(plugin_ids, markdown_plugin_ids)
    for info in infos:
        if not info.plugin_id or not (pm_data := alconna_menu_data.get(info.plugin_id)):
            continue
        if info.pmn.alc_force_enable_detect:
            info.pm_data = [*pm_data, *(info.pm_data or [])]
            logger.debug(
                f"Prepended {len(pm_data)} Alconna menu items for {info.plugin_id}",
            )
            continue
        if info.pm_data is not None:
            continue
        info.pm_data = pm_data
        logger.debug(f"Added {len(pm_data)} Alconna menu items for {info.plugin_id}")

    return infos
