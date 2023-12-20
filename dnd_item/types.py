from rolltable import tables
from pathlib import Path

sources = Path(__file__).parent / Path("sources")


class Item:
    pass


def random_item(count=1):
    types = (sources / Path('types.yaml')).read_text()
    enchantments = (sources / Path('enchantments.yaml')).read_text()
    items = []
    for _ in range(count):
        rt = tables.RollTable([types, enchantments], die=1, hide_rolls=True)
        item = dict(zip(rt.rows[0], rt.rows[1]))
        item['Enchantment Damage'] = '1d4'
        items.append(item)

    return items
