from pathlib import Path

import click

from .core import Renderer

@click.group()
def cli():
    pass

@cli.command(help="Render START_PAGE.j2 to OUT_DIR, and all pages it references")
@click.argument("start_page", type=Path, required=True)
@click.argument("out_dir", type=Path, required=True)
def render(start_page, out_dir):
    if start_page.suffix != ".j2":
        raise Exception("START_PAGE should be a .j2 file")
    renderer = Renderer(start_page.parent, out_dir)
    renderer.render_pages(start_page.stem)


if __name__ == "__main__":
    cli()
