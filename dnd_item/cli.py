import logging
import os

from enum import Enum
from pathlib import Path

import typer

from rich import print
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table

from dnd_item.types import RollTable
from dnd_item.weapons import WeaponGenerator
from dnd_item import five_e

app = typer.Typer()
app_state = {}


class OUTPUT_FORMATS(Enum):
    text = 'text'
    yaml = 'yaml'
    markdown = 'markdown'


@app.callback()
def main(
    cr: int = typer.Option(default=None, help='The Challenge Rating to use when determining rarity.'),
):
    debug = os.getenv("FANITEM_DEBUG", None)
    logging.basicConfig(
        format="%(name)s %(message)s",
        level=logging.DEBUG if debug else logging.INFO,
        handlers=[RichHandler(rich_tracebacks=True, tracebacks_suppress=[typer])],
    )
    logging.getLogger('markdown_it').setLevel(logging.ERROR)

    app_state['cr'] = cr or 0
    app_state['data'] = Path(__file__).parent / Path("sources")


@app.command()
def weapon(count: int = typer.Option(1, help="The number of weapons to generate.")):
    console = Console()
    for weapon in WeaponGenerator().random(count=count, challenge_rating=app_state['cr']):
        console.print(weapon.details)


@app.command("roll-table")
def table(
    die: int = typer.Option(
        20,
        help='The size of the die for which to create a table'),
    hide_rolls: bool = typer.Option(
        False,
        help='If True, do not show the Roll column.',
    ),
    collapsed: bool = typer.Option(
        True,
        help='If True, collapse multiple die values with the same option.'),
    width: int = typer.Option(
        180,
        help='Width of the table.'),
    output: OUTPUT_FORMATS = typer.Option(
        'text',
        help='The output format to use.',
    )
):
    """
    CLI for creating roll tables of randomly-generated items.
    """
    rt = RollTable(
        sources=[WeaponGenerator],
        die=die,
        hide_rolls=hide_rolls,
        challenge_rating=app_state['cr'],
    )

    if output == OUTPUT_FORMATS.yaml:
        print(rt.as_yaml())
    elif output == OUTPUT_FORMATS.markdown:
        print(rt.as_markdown)
    else:
        rows = rt.rows if collapsed else rt.expanded_rows
        table = Table(*rows[0], width=width)
        for row in rows[1:]:
            table.add_row(*row)
        print(table)


@app.command()
def convert():
    src = five_e.weapons()
    print(src.as_yaml)
