import random
from pathlib import Path
from dataclasses import dataclass, field

from random_sets.sets import WeightedSet, DataSourceSet

import rolltable.types


# Create DataSourceSets, which are WeightedSets populated with DataSource
# objects generated from yaml data files. These are used to supply default
# values to item generators; see below.
sources = Path(__file__).parent / Path("sources")
MAGIC_DAMAGE = DataSourceSet(sources / Path('magic_damage_types.yaml'))
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
class Item:
    """
    Item is a data class that constructs its attributes from keyword arguments
    passed to the Item.from_dict() method. Any args that are dicts are
    recursively converted into Item objects, allowing for access to nested
    attribtues using dotted notation. Example:

        >>> orb = Item.from_dict(rarity='rare', name='Orb of Example',
                                extra={'cost_in_gp': 1000})
        >>> orb.rarity
        rare
        >>> orb.name
        Orb of Example
        >>> orb.extra.cost_in_gp
        1000

    String Formatting:

        >>> orb.details
        Orb of Example
        * extra.cost_in_gp: 1000
        * rarity: rare

    Name Templates:

        Item names can be built by overriding the default template, using
        any available attribute:

        >>> orb = Item.from_dict(
          ?     name="orb",
          ?     rarity="rare",
          ?     extra={"cost_in_gp": 1000, "color": "green"},
          ?     template="{rarity} {extra.color} {name} of Example",
          ? )
        >>> orb.name
        Rare Green Orb of Example
    """
    _name: str = None
    _template: str = None
    _attrs: field(default_factory=dict) = None

    @property
    def name(self):
        return self._template.format(name=self._name, **self._attrs).format(**self._attrs).title()

    @property
    def summary(self):
        txt = []
        for k, v in self._attrs['properties']._attrs.items():
            txt.append(v.description.format(
                this=v,
                name=self.name,
                **self._attrs,
            ))
        return "\n\n".join(txt)

    @property
    def details(self):
        """
        Format the item attributes as nested bullet lists.
        """
        return f"{self.name} ({self.rarity.rarity})\n{self.summary}\n--\n{self.properties}"

    @property
    def properties(self):
        def attrs_to_lines(item, prefix: str = ''):
            for (k, v) in item._attrs.items():
                if type(v) is Item:
                    yield from attrs_to_lines(v, prefix=f"{k}.")
                    continue
                yield f" * {prefix}{k}: {v}"
        return "\n".join(["Properties:"] + sorted(list(attrs_to_lines(self))))

    def __getattr__(self, attr):
        """
        Look up attributes in the _attrs dict first, then fall back to the default.
        """
        if attr in self._attrs:
            return self._attrs[attr]
        return self.__getattribute__(attr)

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
        template = kwargs.pop('template') if 'template' in kwargs else '{name}'
        attrs = {}
        for k, v in kwargs.items():
            attrs[k] = Item.from_dict(**v)if type(v) is dict else v
        return cls(_name=name, _template=template, _attrs=attrs)


class Weapon(Item):
    """
    An Item class representing a weapon.
    """


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
        types: WeightedSet,
        rarity: WeightedSet = RARITY,
        properties: WeightedSet = PROPERTIES,
    ):
        self.types = types
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
            'type':  self.types.random(),
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
    """
    An ItemGenerator that generates basic (non-magical) weapons.
    """

    item_class = Weapon

    def __init__(
        self,
        templates: WeightedSet = None,
        types: WeightedSet = WEAPON_TYPES,
        rarity: WeightedSet = RARITY,
        properties: WeightedSet = PROPERTIES,
    ):
        if not templates:
            templates = WeightedSet(('{type.name}', 1.0),)
        super().__init__(types=types, templates=templates, rarity=rarity, properties=properties)


class MagicWeaponGenerator(WeaponGenerator):
    """
    An ItemGenerator that generates weapons imbued with magical effects.
    """
    def __init__(
        self,
        types: WeightedSet = WEAPON_TYPES,
        rarity: WeightedSet = RARITY,
        element: WeightedSet = MAGIC_DAMAGE,
        properties: WeightedSet = PROPERTIES,
    ):
        super().__init__(types=types, templates=None, rarity=rarity, properties=properties)
        self.element = element
        self.property_count_by_rarity = {
            'common': WeightedSet((0, 1.0)),
            'uncommon': WeightedSet((1, 1.0)),
            'rare': WeightedSet((1, 1.0), (2, 0.1)),
            'very rare': WeightedSet((1, 1.0), (2, 1.0)),
            'legendary': WeightedSet((2, 1.0), (3, 1.0)),
        }

    def get_template(self, attrs) -> WeightedSet:
        if not attrs['properties']:
            return '{type.name}'
        options = []
        if attrs['nouns']:
            options.append(('{type.name} of {nouns}', 1.0))
        if attrs['adjectives']:
            options.append(('{adjectives} {type.name}', 1.0))
        if attrs['nouns'] and attrs['adjectives']:
            numprops = len(attrs['properties'].keys())
            if numprops == 1:
                options.append(('{adjectives} {type.name} of {nouns}', 1.0))
            elif len(attrs['properties'].items()) > 1:
                options.append(('{adjectives} {type.name} of {nouns}', 1.0))
                options.append(('{type.name} of {adjectives} {nouns}', 1.0))
        return WeightedSet(*options).random()

    def random_attributes(self) -> dict:
        """
        Select a random magical damage type and add it to our properties.
        """

        # Select a random rarity. This will use the frequency distribution
        # currently selectedon the rarity data source, which in turn will be
        # set by self.random(), controllable by the caller.
        attrs = dict(
            type=self.types.random(),
            rarity=self.rarity.random(),
            properties=dict(),
        )
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
            if prop['name'] == 'element':
                attrs['element'] = self.element.random()
                attrs['element']['adjectives'] = random.choice(attrs['element']['adjectives'].split(',')).strip()
                attrs['element']['nouns'] = random.choice(attrs['element']['nouns'].split(',')).strip()

        attrs['template'] = self.get_template(attrs)
        attrs['adjectives'] = ' '.join(attrs['adjectives'])
        attrs['nouns'] = ' '.join(attrs['nouns'])
        return attrs


@dataclass
class GeneratorSource:
    generator: ItemGenerator
    cr: int

    def random_values(self, count: int = 1) -> list:
        return [
            [item.name, item.rarity.rarity, item.summary]
            for item in self.generator.random(count=count, challenge_rating=self.cr)
        ]


class RollTable(rolltable.types.RollTable):
    def __init__(
        self,
        sources: list,
        die: int = 20,
        hide_rolls: bool = False,
        challenge_rating: int = 0
    ):
        self._cr = challenge_rating
        super().__init__(
            sources=sources,
            frequency='default',
            die=die,
            hide_rolls=hide_rolls
        )

    def _config(self):
        self._data = []
        for src in self._sources:
            self._data.append(GeneratorSource(generator=src(), cr=self._cr))

        self._headers = [
            'Name',
            'Rarity',
            'Description',
        ]
        self._header_excludes = []

    @property
    def _values(self) -> list:
        if not self._generated_values:
            ds_values = [t.random_values(self.die) for t in self._data]
            self._generated_values = []
            for face in range(self._die):
                value = []
                for index, ds in enumerate(ds_values):
                    value += ds_values[index][face]
                self._generated_values.append(value)
        return self._generated_values
