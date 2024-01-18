import json
import re
from collections import defaultdict
from pathlib import Path

import yaml
from random_sets.datasources import DataSource

sources = Path(__file__).parent / Path("sources")

RARITY = {"unknown": "common", "none": "common", "": ""}

TYPE = {"M": "martial", "R": "ranged", "": ""}

DAMAGE = {"S": "Slashing", "P": "Piercing", "B": "Bludgeoning", "": ""}

PROPERTIES = {
    "F": "finesse",
    "AF": "firearm",
    "A": "ammmunition",
    "T": "thrown",
    "L": "light",
    "2H": "two-handed",
    "V": "versatile",
    "RLD": "reload",
    "LD": "loading",
    "S": "special",
    "H": "heavy",
    "R": "reach",
}

LEVEL = [
    'cantrip',
    'first',
    'second',
    'third',
    'fourth',
    'fifth',
    'sixth',
    'seventh',
    'eighth',
    'ninth',
]

SCHOOL = {
    'A': 'Abjuration',
    'C': 'Conjuration',
    'D': 'Divination',
    'E': 'Enchantment',
    'I': 'Illusion',
    'N': 'Necromancy',
    'T': 'Transmutation',
    'V': 'Evocation',
}


class Weapons(DataSource):
    """
    A rolltables data source backed by a 5e.tools json data file. used to
    convert the 5e.tools data to the yaml format consumed by dnd-rolltables.
    """

    def read_source(self) -> None:
        src = json.load(self.source)["baseitem"]
        self.data = defaultdict(list)
        headers = [
            "Rarity",
            "Name",
            "Category",
            "Type",
            "Weight",
            "Damage Type",
            "Damage Dice",
            "Range",
            "Reload",
            "Value",
            "Properties",
        ]

        for item in src:
            if not item.get("weapon", False):
                continue
            if item.get("age", False):
                continue
            rarity = RARITY.get(item["rarity"], "Common").capitalize()
            itype = TYPE.get(item["type"], "_unknown").capitalize()
            properties = ", ".join([PROPERTIES[p] for p in item.get("property", [])])

            self.data[rarity].append(
                {
                    item["name"].capitalize(): [
                        item["weaponCategory"],
                        itype,
                        str(item.get("weight", 0)),
                        DAMAGE.get(item.get("dmgType", "")),
                        item.get("dmg1", None),
                        item.get("range", None),
                        str(item.get("reload", "")),
                        str(item.get("value", "")),
                        properties,
                    ]
                }
            )
        self.metadata = {"headers": headers}

    @property
    def as_yaml(self) -> str:
        return yaml.dump({"metadata": self.metadata}) + yaml.dump(dict(self.data))


class Spells(DataSource):

    def read_source(self) -> None:
        src = json.load(self.source)['spell']
        self.data = defaultdict(list)

        headers = [
            "Level",
            "Name",
            "School",
            "Range",
            "Duration",
            "Damage Die",
            "Damage Type",
            "Material Cost",
        ]

        dmg_die = re.compile(r'\d+d\d+')

        for spell in sorted(src, key=lambda x: int(x['level'])):
            distance = ""
            if spell["range"]["type"] == "special":
                distance = "special"
            elif "amount" in spell["range"]["distance"]:
                distance = f"{spell['range']['distance']['amount']} {spell['range']['distance']['type']}"
            else:
                distance = spell["range"]["distance"]["type"]

            dmgdice = ""
            dmgtype = ""
            if 'damageInflict' in spell:
                try:
                    dmgdice = dmg_die.findall(str(spell["entries"]))[0]
                except IndexError:
                    pass
                dmgtype = ','.join(spell['damageInflict'])

            duration = ""
            dur = spell["duration"][0]
            if dur["type"] == "timed":
                s_or_blank = 's' if dur['duration']['amount'] > 1 else ''
                duration = f"{dur['duration']['amount']} {dur['duration']['type']}{s_or_blank}"
            else:
                duration = dur["type"]

            cost = ""
            try:
                cost = spell['components']['m']['text']
            except (KeyError, TypeError):
                cost = ""

            self.data[LEVEL[spell["level"]]].append(
                {
                    spell["name"].title(): [
                        SCHOOL[spell["school"]],
                        str(distance),
                        str(duration),
                        dmgdice,
                        dmgtype,
                        cost
                    ]
                }
            )
        self.metadata = {"headers": headers}

    @property
    def as_yaml(self) -> str:
        return yaml.dump({"metadata": self.metadata}) + yaml.dump(dict(self.data))


def weapons(source_path: str = "items-base.json") -> dict:
    with open(sources / Path(source_path)) as filehandle:
        ds = Weapons(source=filehandle)
        return ds


def spells() -> dict:
    spells = []
    for source in ['phb', 'ftd', 'scc', 'xge', 'tce']:
        source_path = sources / Path(f"spells-{source}.json")
        with open(source_path) as filehandle:
            spells.append(Spells(source=filehandle))
    for i in range(1, len(spells)):
        for level, spell_list in spells[i].data.items():
            spells[0].data[level] += spell_list
    return spells[0]
