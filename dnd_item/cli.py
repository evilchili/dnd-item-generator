import logging
import os

from pathlib import Path

import typer

from rich.logging import RichHandler
from rich.console import Console

from dnd_item.types import WeaponGenerator, MagicWeaponGenerator
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
def weapon(count: int = typer.Option(1, help="The number of weapons to generate.")):
    console = Console()
    for weapon in WeaponGenerator().random(count):
        console.print(weapon.details)


@app.command()
def magic_weapon(count: int = typer.Option(1, help="The number of weapons to generate.")):
    console = Console()
    for weapon in MagicWeaponGenerator().random(count):
        console.print(weapon.details)


@app.command()
def convert():
    src = five_e.weapons()
    print(src.as_yaml)
