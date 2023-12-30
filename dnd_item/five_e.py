import json
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


def weapons(source_path: str = "items-base.json") -> dict:
    with open(sources / Path(source_path)) as filehandle:
        ds = Weapons(source=filehandle)
        return ds
