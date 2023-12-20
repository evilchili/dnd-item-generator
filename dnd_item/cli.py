import logging
import os

from pathlib import Path

import typer

from rich.logging import RichHandler
from rich.console import Console
# from rich.table import Table

from dnd_item.types import random_item
from dnd_item import five_e

app = typer.Typer()
app_state = {}


@app.callback()
def main():
    debug = os.getenv("FANITEM_DEBUG", None)
    logging.basicConfig(
        format="%(name)s %(message)s",
        level=logging.DEBUG if debug else logging.INFO,
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_suppress=[typer])],
    )
    logging.getLogger('markdown_it').setLevel(logging.ERROR)

    app_state['data'] = Path(__file__).parent / Path("sources")


@app.command()
def item(count: int = typer.Option(1, help="The number of items to generate.")):
    items = random_item(count)
    console = Console()
    for item in items:
        console.print(f"{item['Name']} of {item['Enchantment Noun']} "
                      f"({item['Damage Dice']} {item['Damage Type']} + "
                      f"{item['Enchantment Damage']} {item['Enchantment Type']})")


@app.command()
def convert():
    src = five_e.weapons()
    print(src.as_yaml)
