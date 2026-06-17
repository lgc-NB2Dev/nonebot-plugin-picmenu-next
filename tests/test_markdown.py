from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo
    from nonebot_plugin_picmenu_next.markdown import (
        PluginResPathProcessor,
        PluginResPathProcessPluginEnv,
    )


def _make_info():
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    return PMNPluginInfo(name="TestPlugin", plugin_id="test_plugin")


def _make_prp_processor() -> "PluginResPathProcessor":
    def _prp(info: "PMNPluginInfo", path: str) -> str:  # noqa: ARG001
        return path.replace("plugin:self,", "/resolved/").replace(
            "plugin:other,",
            "/resolved-other/",
        )

    return _prp


def _env(
    info: "PMNPluginInfo",
    prp: "PluginResPathProcessor",
) -> "PluginResPathProcessPluginEnv":
    return cast("PluginResPathProcessPluginEnv", {"info": info, "prp_processor": prp})


def _render(md_text: str, *args: Any, **kwargs: Any) -> str:
    from nonebot_plugin_picmenu_next.markdown import md

    return md.render(md_text, *args, **kwargs)


# === image token ===


def test_image_src_with_plugin_self(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "![alt](plugin:self,img/foo.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/img/foo.png"' in result


def test_image_src_with_plugin_other(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "![alt](plugin:other,img/bar.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved-other/img/bar.png"' in result


def test_image_src_without_plugin_prefix_unchanged(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "![alt](https://example.com/img.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="https://example.com/img.png"' in result


def test_image_src_without_env_unchanged(picmenu_plugin: object):  # noqa: ARG001
    result = _render("![alt](plugin:self,img/foo.png)")
    assert 'src="plugin:self,img/foo.png"' in result


# === link token ===


def test_link_href_with_plugin_self(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "[download](plugin:self,file.zip)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'href="/resolved/file.zip"' in result


def test_link_href_with_plugin_other(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "[data](plugin:other,data.json)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'href="/resolved-other/data.json"' in result


def test_link_href_without_plugin_prefix_unchanged(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "[google](https://google.com)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'href="https://google.com"' in result


# === html_block token ===


def test_html_block_img_src_with_plugin(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        '<img src="plugin:self,img/logo.png">',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/img/logo.png"' in result


def test_html_block_a_href_with_plugin(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        '<a href="plugin:self,page/about">About</a>',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'href="/resolved/page/about"' in result


def test_html_block_video_src_and_poster_with_plugin(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        '<video src="plugin:self,video/demo.mp4" poster="plugin:self,img/cover.jpg"></video>',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/video/demo.mp4"' in result
    assert 'poster="/resolved/img/cover.jpg"' in result


def test_html_block_without_env_unchanged(picmenu_plugin: object):  # noqa: ARG001
    result = _render('<img src="plugin:self,img/foo.png">')
    assert 'src="plugin:self,img/foo.png"' in result


def test_html_block_non_plugin_attrs_unchanged(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        '<img src="https://example.com/img.png" alt="pic">',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="https://example.com/img.png"' in result
    assert 'alt="pic"' in result


# === html_inline token ===


def test_html_inline_img_src_with_plugin(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        'text <img src="plugin:self,img/icon.png"> more text',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/img/icon.png"' in result


def test_html_inline_a_href_with_plugin(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        'text <a href="plugin:self,page/help">help</a> more',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'href="/resolved/page/help"' in result


# === mixed scenarios ===


def test_mixed_image_and_link(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        "![img](plugin:self,a.png) and [link](plugin:self,b.zip)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/a.png"' in result
    assert 'href="/resolved/b.zip"' in result


def test_mixed_html_block_and_inline(picmenu_plugin: object):  # noqa: ARG001
    result = _render(
        '<img src="plugin:self,block.png">\n\ntext <img src="plugin:self,inline.png"> more',
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/block.png"' in result
    assert 'src="/resolved/inline.png"' in result
