import random
from pathlib import Path
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
PROPERTIES = {
    'common': DataSourceSet(sources / Path('properties_common.yaml')),
    'uncommon': DataSourceSet(sources / Path('properties_uncommon.yaml')),
    'rare': DataSourceSet(sources / Path('properties_rare.yaml')),
    'very rare': DataSourceSet(sources / Path('properties_very_rare.yaml')),
    'legendary': DataSourceSet(sources / Path('properties_legendary.yaml')),
}


@dataclass
class AttributeDict:
    _attrs: field(default_factory=dict) = None

    def __getattr__(self, attr):
        """
        Look up attributes in the _attrs dict first, then fall back to the default.
        """
        if attr in self._attrs:
            return self._attrs[attr]
        return self.__getattribute__(attr)

    def __str__(self):
        return self._flatten(self)

    def __repr__(self):
        return str(self)

    def _flatten(self, obj, prefix=None):
        if prefix == '':
            prefix = f"{self.__class__.__name__}."
        else:
            prefix = ''

        lines = []
        for (k, v) in obj._attrs.items():
            if type(v) is AttributeDict:
                lines.append(self._flatten(v, prefix=f"{prefix}{k}"))
            else:
                lines.append(f"{prefix}{k} = {v}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, **kwargs: dict):
        """
        Create a new AttributeDict object using keyword arguments. Dicts are
        recursively converted to AttributeDict objects; everything else is
        passed as-is.
        """
        attrs = {}
        for k, v in sorted(kwargs.items()):
            attrs[k] = AttributeDict.from_dict(**v)if type(v) is dict else v
        return cls(_attrs=attrs)


@dataclass
class Item(AttributeDict):
    """
    """
    _name: str = None
    rarity: str = None
    _template: str = None

    @property
    def name(self):
        return self._template.format(name=self._name, **self._attrs).format(**self._attrs).title()

    @property
    def properties(self):
        return self._attrs['properties']._attrs

    @property
    def description(self):
        txt = []
        for k, v in self.properties.items():
            txt.append(k.title() + ". " + v.description.format(
                this=v,
                name=self.name,
                **self._attrs,
            ).format(name=self.name, **self._attrs))
        return "\n".join(txt)

    @property
    def details(self):
        """
        Format the item attributes as nested bullet lists.
        """
        return "\n".join([
            f"{self.name} ({self.rarity['rarity']}):",
            self.description,
            "",
            self._flatten(self.base, prefix=None)
        ])

    @property
    def _properties_as_text(self):
        def attrs_to_lines(item, prefix: str = ''):
            for (k, v) in item._attrs.items():
                if type(v) is AttributeDict:
                    yield from attrs_to_lines(v, prefix=f"{k}.")
                    continue
                yield f" * {prefix}{k}: {v}"
        return "\n".join(["Properties:"] + sorted(list(attrs_to_lines(self))))

    @classmethod
    def from_dict(cls, **kwargs: dict):
        """
        Create a new Item object using keyword arguments. Dicts are recursively
        converted to Item objects; everything else is passed as-is.

        The "name" and "template" arguments, if supplied, are removed from the
        keyword arguments and used to populate those attributes directly; all
        other attributes will be added to the _attrs dict so they can be
        accessed directly through dotted attribute notation.
        """
        name = kwargs.pop('name') if 'name' in kwargs else '(unnamed)'
        rarity = kwargs.pop('rarity') if 'rarity' in kwargs else 'common'
        template = kwargs.pop('template') if 'template' in kwargs else '{name}'
        attrs = {}
        for k, v in kwargs.items():
            attrs[k] = AttributeDict.from_dict(**v)if type(v) is dict else v
        return cls(_name=name, rarity=rarity, _template=template, _attrs=attrs)

    def __repr__(self):
        return str(self)


class Weapon(Item):
    """
    An Item class representing a weapon with the following attributes:
    """

    @property
    def to_hit(self):
        bonus_val = 0
        bonus_dice = ''
        for prop in self.properties.values():
            mod = getattr(prop, 'to_hit', None)
            if not mod:
                continue
            if type(mod) is int:
                bonus_val += mod
            elif type(mod) is str:
                bonus_dice += f"+{mod}"
        return f"+{bonus_val}{bonus_dice}"

    @property
    def damage_dice(self):
        dmg = dict()
        dmg[self.base.damage_type] = self.base.damage or ''
        for prop in self.properties.values():
            mod = getattr(prop, 'damage', None)
            if not mod:
                continue
            key = str(prop.damage_type).format(**self._attrs).title()
            if key not in dmg:
                dmg[key] = str(mod)
            else:
                dmg[key] += f"+{mod}"

        return ' + '.join([f"{v} {k}" for k, v in dmg.items()])

    @property
    def summary(self):
        return f"{self.to_hit} to hit, {self.base.range} ft., {self.base.targets} targets. {self.damage_dice}"

    @property
    def details(self):
        """
        Format the item attributes as nested bullet lists.
        """
        return "\n".join([
            f"{self.name}",
            f" * {self.rarity['rarity']} {self.base.category} weapon ({self.base.properties})",
            f" * {self.summary}",
            f"\n{self.description}\n" if self.description else "",
            "----",
            self._flatten(self.base, prefix=None)
        ])


class ItemGenerator:
    """
    Generate randomized instances of Item objects.

    The main interfaces is the random() method, which will generate one or
    more random Item instances by selecting random values from the supplied
    WeightedSets. This allows for fully-controllable frequency distributions.

    You probably want to subclass this class, in order to provide sensible
    defaults, and control what attributes are available; refer to the
    subclasses elsewhere in this module.

    The class requires two arguments to instantiate:
        * templates - a WeightedSet of format strings for item names; and
        * types - a WeightedSet of item types to be selected from at random.

    Example:

        >>> ig = ItemGenerator(
          ?     templates=WeightedSet("{type.name}", 1.0),
          ?     types=WeightedSet(
          ?         ({'name': 'ring'}, 1.0),
          ?         ({'name': 'hat'}, 1.0),
          ?     ),
          ? )
        >>> ig.random(3).name
        ['hat', 'hat', 'ring']
    """

    # Create instances of this class. Subclasses may wish to override this.
    item_class = Item

    def __init__(
        self,
        templates: WeightedSet,
        bases: WeightedSet,
        rarity: WeightedSet = RARITY,
        properties: WeightedSet = PROPERTIES,
    ):
        self.bases = bases
        self.templates = templates
        self.rarity = rarity
        self.properties = properties

    def random_attributes(self) -> dict:
        """
        Select random values from the available attributes. These values will
        be passed as arguments to the Item constructor.

        If you subclass this class and override this method, be sure that
        whatever attributes are referenced in your template strings are
        available as properties here. For example, if you have a subclass with
        the template:

            WeightedSet("{this.color} {that.thing}", 1.0)

        This method must return a dict that includes both this and that, and
        each of them must be either Item instances or dictionaries.
        """
        return {
            'template':  self.templates.random(),
            'base':  self.bases.random(),
            'rarity': self.rarity.random(),
            'properties': self.properties.random(),
        }

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
            items.append(self.item_class.from_dict(**self.random_attributes()))
        return items


class WeaponGenerator(ItemGenerator):
    item_class = Weapon

    def __init__(
        self,
        templates: WeightedSet = WeightedSet(('{base.name}', 1.0),),
        bases: WeightedSet = WEAPON_TYPES,
        rarity: WeightedSet = RARITY,
        enchanted: WeightedSet = ENCHANTMENT,
        properties: WeightedSet = PROPERTIES,
    ):
        super().__init__(bases=bases, templates=None, rarity=rarity, properties=properties)
        self.enchanted = enchanted
        self.property_count_by_rarity = {
            'common': WeightedSet((0, 1.0)),
            'uncommon': WeightedSet((1, 1.0)),
            'rare': WeightedSet((1, 1.0), (2, 0.1)),
            'very rare': WeightedSet((1, 1.0), (2, 1.0)),
            'legendary': WeightedSet((2, 1.0), (3, 1.0)),
        }

    def get_template(self, attrs) -> WeightedSet:
        if not attrs['properties']:
            return '{base.name}'
        options = []
        if attrs['nouns']:
            options.append(('{base.name} of {nouns}', 1.0))
        if attrs['adjectives']:
            options.append(('{adjectives} {base.name}', 1.0))
        if attrs['nouns'] and attrs['adjectives']:
            numprops = len(attrs['properties'].keys())
            if numprops == 1:
                options.append(('{adjectives} {base.name} of {nouns}', 0.1))
            elif len(attrs['properties'].items()) > 1:
                options.append(('{adjectives} {base.name} of {nouns}', 1.0))
                options.append(('{base.name} of {adjectives} {nouns}', 1.0))
        return WeightedSet(*options).random()

    def random_attributes(self) -> dict:
        """
        Select a random magical damage type and add it to our properties.
        """

        # Select a random rarity. This will use the frequency distribution
        # currently selectedon the rarity data source, which in turn will be
        # set by self.random(), controllable by the caller.
        attrs = dict(
            base=self.bases.random(),
            rarity=self.rarity.random(),
            properties=dict(),
        )
        attrs['base']['targets'] = 1

        if attrs['base']['category'] == 'Martial':
            if not attrs['base']['range']:
                attrs['base']['range'] = '5'

        rarity = attrs['rarity']['rarity']

        numprops = min(
            self.property_count_by_rarity[rarity].random(),
            len(self.properties[rarity].members)
        )

        while len(attrs['properties']) != numprops:
            prop = self.properties[rarity].random()
            if prop['name'] in attrs['properties']:
                continue
            attrs['properties'][prop['name']] = prop

        # combine multiple property template arguments  together
        attrs['adjectives'] = []
        attrs['nouns'] = []
        for prop_name, prop in attrs['properties'].items():
            attrs['adjectives'].append(prop['adjectives'])
            attrs['nouns'].append(prop['nouns'])
            if prop['name'] == 'enchanted':
                attrs['enchanted'] = self.enchanted.random()
                attrs['enchanted']['adjectives'] = random.choice(attrs['enchanted']['adjectives'].split(',')).strip()
                attrs['enchanted']['nouns'] = random.choice(attrs['enchanted']['nouns'].split(',')).strip()

        attrs['template'] = self.get_template(attrs)
        attrs['adjectives'] = ' '.join(attrs['adjectives'])
        attrs['nouns'] = ' '.join(attrs['nouns'])
        return attrs


@dataclass
class GeneratorSource:
    generator: ItemGenerator
    cr: int

    def random_values(self, count: int = 1) -> list:
        vals = sorted(
            (item.rarity['sort_order'], [item.name, item.rarity['rarity'], item.summary, item.base.properties])
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
            'Properties'
        ]
        self._header_excludes = []
