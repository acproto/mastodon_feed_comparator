from __future__ import annotations

from jinja2 import Environment, FileSystemLoader


def render(context: dict, theme: str = None, template: str = "index.html.jinja") -> str:
    environment_folders = ["templates/common", "templates/styles", "templates/scripts", "templates/pages"]
    if theme:
        environment_folders.append(f"templates/themes/{theme}")
    environment = Environment(
        loader=FileSystemLoader(environment_folders)
    )
    template = environment.get_template(template)
    return template.render(context)
