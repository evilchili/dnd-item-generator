import logging
import os

import typer

from rich.logging import RichHandler
from rich.console import Console

from dnd_item.types import Item


app = typer.Typer()


@app.callback()
def main():
    debug = os.getenv("FANITEM_DEBUG", None)
    logging.basicConfig(
        format="%(name)s %(message)s",
        level=logging.DEBUG if debug else logging.INFO,
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_suppress=[typer])],
    )
    logging.getLogger('markdown_it').setLevel(logging.ERROR)


@app.command()
def item(count: int = typer.Option(1, help="The number of items to generate.")):
    console = Console(width=80)
    for _ in range(count):
        console.print(Item())
