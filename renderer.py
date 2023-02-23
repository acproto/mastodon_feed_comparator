from __future__ import annotations

from jinja2 import Environment, FileSystemLoader


def render(context: dict, theme: str = "default") -> None:
    environment = Environment(
        loader=FileSystemLoader([
            f"templates/themes/{theme}", "templates/common", "templates/styles", "templates/scripts"])
    )
    template = environment.get_template("index.html.jinja")
    return template.render(context)
