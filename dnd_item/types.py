import re
import logging

from pathlib import Path
from collections.abc import Mapping
from dataclasses import dataclass, field

from random_sets.sets import WeightedSet, DataSourceSet

import rolltable.types


# Create DataSourceSets, which are WeightedSets populated with DataSource
# objects generated from yaml data files. These are used to supply default
# values to item generators; see below.
sources = Path(__file__).parent / Path("sources")
ENCHANTMENT = DataSourceSet(sources / Path('magic_damage_types.yaml'))
WEAPON_TYPES = DataSourceSet(sources / Path('weapons.yaml'))
RARITY = DataSourceSet(sources / Path('rarity.yaml'))
PROPERTIES_BY_RARITY = {
    'base': DataSourceSet(sources / Path('properties_base.yaml')),
    'common': DataSourceSet(sources / Path('properties_common.yaml')),
    'uncommon': DataSourceSet(sources / Path('properties_uncommon.yaml')),
    'rare': DataSourceSet(sources / Path('properties_rare.yaml')),
    'very rare': DataSourceSet(sources / Path('properties_very_rare.yaml')),
    'legendary': DataSourceSet(sources / Path('properties_legendary.yaml')),
}


@dataclass
class AttributeDict(Mapping):
    attributes: field(default_factory=dict)

    def __getattr__(self, attr):
        """
        Look up attributes in the _attrs dict first, then fall back to the default.
        """
        if attr in self.attributes:
            return self.attributes[attr]
        return self.__getattribute__(attr)

    def __len__(self):
        return len(self.attributes)

    def __getitem__(self, key):
        return self.attributes[key]

    def __iter__(self):
        return iter(self.attributes)

    @classmethod
    def from_dict(cls, kwargs: dict):
        """
        Create a new AttributeDict object using keyword arguments. Dicts are
        recursively converted to AttributeDict objects; everything else is
        passed as-is.
        """
        attrs = {}
        for k, v in sorted(kwargs.items()):
            attrs[k] = AttributeDict.from_dict(v)if type(v) is dict else v
        return cls(attributes=attrs)


@dataclass
class Item(AttributeDict):
    """
    """
    _name: str = None

    @property
    def name(self) -> str:
        """
        The item's name. This is a handy property for subclassers to override.
        """
        return self._name

    @property
    def description(self):
        desc = "\n".join([k.title() + ". " + v.description for k, v in self.get('properties', {}).items()])
        return desc.format(**self)

    @classmethod
    def from_dict(cls, attrs: dict):
        """
        Create a new Item object using keyword arguments. Dicts are recursively
        converted to Item objects; everything else is passed as-is.
        """

        # delay processing the 'properties' attribute until after the other
        # attributes, because they may contain references to those attributes.
        properties = attrs.pop('properties', None)

        attributes = dict()

        # recursively locate and populate template strings
        def _format(obj, this=None):

            # enables use of the 'this' keyword to refer to the current context
            # in a template. Refer to the enchantment sources for an example.
            if this:
                this = AttributeDict.from_dict(this)

            # dicts and lists are descended into
            if type(obj) is dict:
                return AttributeDict.from_dict(dict(
                    (key, _format(val, this=obj)) for key, val in obj.items()
                ))
            if type(obj) is list:
                return [_format(o, this=this) for o in obj]

            # Strings are formatted wth values from attributes and this. Using
            # attributes is important here, so that values containing template
            # strings are processed before they are referenced.
            if type(obj) is str:
                return obj.format(**attributes, this=this)

            # Any type other than dict, list, and string is returned unaltered.
            return obj

        # step through the supplied attributes and format each member.
        for k, v in attrs.items():
            if type(v) is dict:
                attributes[k] = AttributeDict.from_dict(_format(v))
            else:
                attributes[k] = _format(v)
        if properties:
            attributes['properties'] = AttributeDict.from_dict(_format(properties))
            for prop in attributes['properties'].values():
                overrides = [k for k in prop.attributes.keys() if k.startswith('override_')]
                for o in overrides:
                    if prop.attributes[o]:
                        attributes[o.replace('override_', '')] = prop.attributes[o]

        # store the item name as the _name attribute; it is accessable directly, or
        # via the name property. This makes overriding the name convenient for subclassers,
        # which may require naming semantics that cannot be resolved at instantiation time.
        _name = attributes['name']
        del attributes['name']

        # At this point, attributes is a dictionary with members of multiple
        # types, but every dict member has been converted to an AttributeDict,
        # and all template strings in the object have been formatted. Return an
        # instance of the Item class using these formatted attributes.
        return cls(
            _name=_name,
            attributes=attributes
        )


class ItemGenerator:
    """
    """
    item_class = Item

    def __init__(self, bases: WeightedSet, rarity: WeightedSet, properties_by_rarity: dict):
        self.bases = bases
        self.rarity = rarity
        self.properties_by_rarity = properties_by_rarity

    def _property_count_by_rarity(self, rarity: str) -> int:
        property_count_by_rarity = {
            'common': WeightedSet((1, 0.1), (0, 1.0)),
            'uncommon': WeightedSet((1, 1.0)),
            'rare': WeightedSet((1, 1.0), (2, 0.5)),
            'very rare': WeightedSet((1, 0.5), (2, 1.0)),
            'legendary': WeightedSet((2, 1.0), (3, 1.0)),
        }
        return min(
            property_count_by_rarity[rarity].random(),
            len(self.properties_by_rarity[rarity].members)
        )

    def get_requirements(self, item) -> set:
        pat = re.compile(r'{([^\.\}]+)')

        def getreqs(obj):
            if type(obj) is dict:
                for val in obj.values():
                    yield from getreqs(val)
            elif type(obj) is list:
                yield from [getreqs(o) for o in obj]
            elif type(obj) is str:
                matches = pat.findall(obj)
                if matches:
                    yield from matches

        return set(getreqs(item))

    def random_properties(self) -> dict:
        item = self.bases.random()
        item['rarity'] = self.rarity.random()

        properties = {}
        num_properties = self._property_count_by_rarity(item['rarity']['rarity'])
        while len(properties) != num_properties:
            thisprop = self.properties_by_rarity[item['rarity']['rarity']].random()
            properties[thisprop['name']] = thisprop

        # add properties from the base item (versatile, thrown, artifact..)
        for name in item.pop('properties', '').split(','):
            name = name.strip()
            if name:
                properties[name] = self.properties_by_rarity['base'].source.as_dict()[name]

        item['properties'] = properties

        # look for template strings that reference item attributes which do not yet exist.
        # Add anything that is missing via a callback.
        predefined = list(item.keys()) + ['this', '_name']
        for requirement in [r for r in self.get_requirements(item) if r not in predefined]:
            try:
                item[requirement] = getattr(self, f'get_{requirement}')(**item)
            except AttributeError:
                logging.error("{item['name']} requires {self.__class__.__name__} to have a get_{requirement}() method.")
                raise

        return item

    def random(self, count: int = 1, challenge_rating: int = 0) -> list:
        """
        Generate one or more random Item instances by selecting random values
        from the available types and template
        """

        # select the appropriate frequency distributionnb ased on the specified
        # challenge rating. By default, all rarities are weighted equally.
        if challenge_rating in range(1, 5):
            frequency = '1-4'
        elif challenge_rating in range(5, 11):
            frequency = '5-10'
        elif challenge_rating in range(11, 17):
            frequency = '11-16'
        elif challenge_rating >= 17:
            frequency = '17'
        else:
            frequency = 'default'
        self.rarity.set_frequency(frequency)

        items = []
        for _ in range(count):
            items.append(self.item_class.from_dict(self.random_properties()))
        return items


@dataclass
class GeneratorSource:
    generator: ItemGenerator
    cr: int

    def random_values(self, count: int = 1) -> list:
        vals = sorted(
            (
                item.rarity['sort_order'],
                [
                    item.name,
                    item.rarity['rarity'],
                    item.summary,
                    ', '.join(item.get('properties', [])),
                    item.id
                ]
            )
            for item in self.generator.random(count=count, challenge_rating=self.cr)
        )
        return [v[1] for v in vals]


class RollTable(rolltable.types.RollTable):
    def __init__(
        self,
        sources: list,
        die: int = 20,
        hide_rolls: bool = False,
        challenge_rating: int = 0,
    ):
        self._cr = challenge_rating
        super().__init__(
            sources=sources,
            frequency='default',
            die=die,
            hide_rolls=hide_rolls,
        )

    def _config(self):
        self._data = []
        for src in self._sources:
            self._data.append(GeneratorSource(generator=src(), cr=self._cr))

        self._headers = [
            'Name',
            'Rarity',
            'Summary',
            'Properties',
            'ID',
        ]
        self._header_excludes = []
