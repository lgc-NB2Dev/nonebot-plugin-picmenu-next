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
from arclet.alconna.formatter import Trace
from arclet.alconna.typing import AllParam, InnerShortcutArgs
from cookit.loguru import warning_suppress
from cookit.pyd import type_validate_python
from nonebot import logger
from nonebot.matcher import MatcherSource

from .models import OptionalPMDataItem, PMDataItem, PMNPluginInfo

if TYPE_CHECKING:
    from arclet.alconna import Alconna

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
        return self.format_trace(trace, [])

    def format_node(self, parts: list | None = None):
        return "\n".join(
            self.format_trace(v, [])
            if not (normalized_parts := self.normalize_parts(v, parts))
            else self.format_subcommand_node(v, normalized_parts)
            for v in self.data.values()
        )

    def normalize_parts(self, trace: "Trace", parts: list | None = None) -> list[str]:
        cache = trace.body
        normalized_parts: list[str] = []
        for part in (str(x) for x in (parts or []) if str(x)):
            node = self.find_subcommand(cache, [part])
            if node is None:
                continue
            matched, _ = node
            normalized_parts.append(part)
            cache = matched.options
        return normalized_parts

    def format_subcommand_node(self, trace: "Trace", parts: list[str]) -> str:
        found = self.find_subcommand(trace.body, parts)
        if found is None:
            return self.format_trace(trace, [])
        node, alias_parts = found
        primary_prefix = parts
        alias_prefix = alias_parts
        if alias_prefix == primary_prefix:
            alias_prefix = None
        return self.format_trace(
            Trace(
                {
                    "name": trace.head["name"],
                    "description": (
                        "" if node.help_text == node.dest else node.help_text
                    ),
                    "usage": None,
                    "example": None,
                },
                node.args,
                trace.separators,
                node.options,
                {},
            ),
            primary_prefix,
            alias_prefix,
        )

    def find_subcommand(
        self,
        nodes: list[Option | Subcommand],
        parts: list[str],
    ) -> tuple[Subcommand, list[str]] | None:
        if not parts:
            return None
        current, *remaining = parts
        for node in nodes:
            if not isinstance(node, Subcommand) or current not in node.aliases:
                continue
            alias = self.subcommand_alias(node)
            if not remaining:
                return node, [alias]
            if found := self.find_subcommand(node.options, remaining):
                child, child_aliases = found
                return child, [alias, *child_aliases]
        return None

    def format_trace(
        self,
        trace: "Trace",
        path_prefix: list[str],
        alias_prefix: list[str] | None = None,
    ) -> str:
        parts: list[str] = []

        command = self.command(trace, path_prefix)
        if command:
            # parts.extend(("", "**指令**", "", fenced_code(command)))
            parts.append(fenced_code(command))

        if description := trace.head.get("description"):
            parts.extend(("", description))

        if usage := trace.head.get("usage"):
            parts.extend(("", "**用法**", "", fenced_code(usage)))

        if args := self.args(trace.args):
            parts.extend(("", "**参数**", "", args))

        if body := self.body(trace.body, path_prefix, alias_prefix):
            parts.extend(("", body))

        if example := trace.head.get("example"):
            parts.extend(("", "**示例**", "", fenced_code(example, "shell")))

        if shortcuts := self.shortcut(trace.shortcuts):
            parts.extend(("", shortcuts))

        return "\n".join(parts).strip()

    def command(self, trace: "Trace", path_prefix: list[str] | None = None) -> str:
        params = self.parameters(trace.args)
        name = " ".join((trace.head["name"], *(path_prefix or [])))
        return f"{name}{trace.separators[0]}{params}".strip()

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
            main_details = []
            extra_details = []
            if arg.value is not ANY and str(arg.value).strip("'\"") != arg.name:
                main_details.append(f"类型 {inline_code(arg.value)}")
            if arg.optional:
                main_details.append("可选")
            if arg.field.display is not Empty:
                extra_details.append(f"默认值 {inline_code(arg.field.display)}")
            if arg.notice:
                extra_details.append(arg.notice)
            details = "，".join(main_details)
            if extra_details:
                details = "；".join(x for x in (details, *extra_details) if x)
            lines.append(f"- {inline_code(arg.name)}：{details}")
        return "\n".join(lines)

    def option_signature(self, node: Option) -> str:
        aliases = [node.name, *[x for x in sorted(node.aliases) if x != node.name]]
        alias_text = "│".join(inline_code(x) for x in aliases)
        params = self.parameters(node.args)
        return f"{alias_text} {inline_code(params)}" if params else alias_text

    def format_option(self, node: Option, indent: int = 0) -> str:
        help_text = "无说明" if node.help_text == node.dest else node.help_text
        prefix = "  " * indent
        if help_text == "无说明":
            return f"{prefix}- {self.option_signature(node)}"
        return f"{prefix}- {self.option_signature(node)}：{help_text}"

    def subcommand_signature(self, name: str, node: Subcommand) -> str:
        params = self.parameters(node.args)
        sep = next(iter(node.separators)) if params else ""
        return f"{name}{sep}{params}".strip()

    def subcommand_params(self, node: Subcommand) -> str:
        params = self.parameters(node.args)
        return f" {inline_code(params)}" if params else ""

    def subcommand_aliases(self, node: Subcommand) -> list[str]:
        return [x for x in sorted(node.aliases) if x != node.name]

    def subcommand_alias(self, node: Subcommand) -> str:
        return next(iter(self.subcommand_aliases(node)), node.name)

    def subcommand_names_text(self, node: Subcommand) -> str:
        names = [node.name, *self.subcommand_aliases(node)]
        return "│".join(inline_code(x) for x in names)

    def format_subcommand(
        self,
        node: Subcommand,
        primary_prefix: list[str] | None = None,
        alias_prefix: list[str] | None = None,
        indent: int = 0,
        expand: bool = True,
        inline_description: bool | None = None,
    ) -> list[str]:
        del primary_prefix, alias_prefix
        help_text = "无说明" if node.help_text == node.dest else node.help_text
        prefix = "  " * indent
        inline_description = (
            expand if inline_description is None else inline_description
        )
        nested_subcommands: list[str] = []
        nested_options: list[str] = []
        if expand:
            for child in node.options:
                if isinstance(child, Subcommand):
                    nested_subcommands.extend(
                        self.format_subcommand(
                            child,
                            None,
                            None,
                            indent + 1,
                            expand=False,
                            inline_description=False,
                        ),
                    )
                elif isinstance(child, Option) and child.name not in self.ignore_names:
                    nested_options.append(self.format_option(child, indent + 1))

        signature = f"{self.subcommand_names_text(node)}{self.subcommand_params(node)}"
        has_nested_items = bool(nested_subcommands or nested_options)
        if inline_description or has_nested_items:
            lines = [
                f"{prefix}- {signature}：{help_text}{'  ' if has_nested_items else ''}",
            ]
        else:
            lines = [
                f"{prefix}- {signature}  ",
                f"{prefix}  {help_text}{'  ' if has_nested_items else ''}",
            ]
        if not expand:
            return lines

        nested_prefix = "  " * (indent + 1)
        if nested_subcommands:
            lines.append(f"{nested_prefix}该命令下可用的子命令有：")
            lines.extend(nested_subcommands)
        if nested_options:
            lines.append(f"{nested_prefix}该命令下可用的选项有：  ")
            lines.extend(nested_options)
        return lines

    def body(
        self,
        parts: list[Option | Subcommand],
        path_prefix: list[str] | None = None,
        alias_prefix: list[str] | None = None,
    ) -> str:
        subcommands: list[str] = []
        options: list[str] = []
        for node in parts:
            if isinstance(node, Subcommand):
                subcommands.extend(
                    self.format_subcommand(
                        node,
                        path_prefix,
                        alias_prefix or path_prefix,
                        inline_description=not path_prefix,
                    ),
                )
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


def format_alconna_help_text(
    command: "Alconna",
    markdown: bool = False,
    parts: list[str] | None = None,
) -> str:
    if markdown and type(command.formatter) is TextFormatter:
        return PMNMarkdownTextFormatter().add(command).format_node(parts)
    if parts:
        return command.formatter.format_node(parts)
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
