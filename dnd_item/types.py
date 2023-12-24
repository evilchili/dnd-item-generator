import random

from pathlib import Path
from dataclasses import dataclass, field

from random_sets.sets import WeightedSet, DataSourceSet


# Create DataSourceSets, which are WeightedSets populated with DataSource
# objects generated from yaml data files. These are used to supply default
# values to item generators; see below.
sources = Path(__file__).parent / Path("sources")
MAGIC_DAMAGE = DataSourceSet(sources / Path('magic_damage_types.yaml'))
WEAPON_TYPES = DataSourceSet(sources / Path('weapons.yaml'))
#  RARITY = DataSourceSet(sources / Path('rarity.yaml'))


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
        return self._template.format(name=self._name, **self._attrs).title()

    @property
    def details(self):
        """
        Format the item attributes as nested bullet lists.
        """
        def attrs_to_lines(item, prefix: str = ''):
            for (k, v) in item._attrs.items():
                if type(v) is Item:
                    yield from attrs_to_lines(v, prefix=f"{k}.")
                    continue
                yield f" * {prefix}{k}: {v}"
        return "\n".join([self.name] + sorted(list(attrs_to_lines(self))))

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
    ):
        self.types = types
        self.templates = templates

    def random_properties(self) -> dict:
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

        # Select one random template string and one item type.
        properties = {
            'template':  self.templates.random(),
            'type':  self.types.random(),
        }
        return properties

    def random(self, count: int = 1) -> list:
        """
        Generate one or more random Item instances by selecting random values
        from the available types and template
        """
        items = []
        for _ in range(count):
            items.append(self.item_class.from_dict(**self.random_properties()))
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
    ):
        if not templates:
            templates = WeightedSet(('{type.name}', 1.0),)
        super().__init__(types=types, templates=templates)


class MagicWeaponGenerator(WeaponGenerator):
    """
    An ItemGenerator that generates weapons imbued with magical effects.
    """
    def __init__(
        self,
        templates: WeightedSet = None,
        types: WeightedSet = WEAPON_TYPES,
        magic: WeightedSet = MAGIC_DAMAGE,
    ):
        self.magic = magic
        if not templates:
            templates = WeightedSet(
                # "Shortsword of Flames"
                ('{type.name} of {magic.noun}', 1.0),
                # "Burning Lance"
                ('{magic.adjective} {type.name}', 1.0),
            )
        super().__init__(types=types, templates=templates)

    def random_properties(self):
        """
        Select a random magical damage type and add it to our properties.
        """
        properties = super().random_properties()
        magic = self.magic.random()
        properties['magic'] = {
            'adjective': random.choice(magic['adjectives'].split(',')).strip(),
            'noun': random.choice(magic['noun'].split(',')).strip(),
            'die': '1d4'
        }
        return properties
