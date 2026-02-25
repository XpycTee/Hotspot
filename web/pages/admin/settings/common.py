from collections.abc import Callable, Mapping

from flask import render_template

from web.structures import ViewItem


def build_view_items(
    source: Mapping[str, dict],
    item_builder: Callable[[dict], ViewItem],
) -> dict[str, ViewItem]:
    return {item_id: item_builder(data) for item_id, data in source.items()}


def render_settings_page(
    template_name: str,
    source: Mapping[str, dict],
    item_builder: Callable[[dict], ViewItem],
    empty_item: ViewItem,
    actions: list[str] | None = None,
) -> str:
    return render_template(
        template_name,
        data=build_view_items(source, item_builder),
        actions=actions or ['add'],
        empty_item=empty_item,
    )
