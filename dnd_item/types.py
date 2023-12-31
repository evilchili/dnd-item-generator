import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import rolltable.types
from random_sets.sets import DataSourceSet, WeightedSet

# Create DataSourceSets, which are WeightedSets populated with DataSource
# objects generated from yaml data files. These are used to supply default
# values to item generators; see below.
sources = Path(__file__).parent / Path("sources")
ENCHANTMENT = DataSourceSet(sources / Path("magic_damage_types.yaml"))
WEAPON_TYPES = DataSourceSet(sources / Path("weapons.yaml"))
RARITY = DataSourceSet(sources / Path("rarity.yaml"))
PROPERTIES_BY_RARITY = {
    "base": DataSourceSet(sources / Path("properties_base.yaml")),
    "common": DataSourceSet(sources / Path("properties_common.yaml")),
    "uncommon": DataSourceSet(sources / Path("properties_uncommon.yaml")),
    "rare": DataSourceSet(sources / Path("properties_rare.yaml")),
    "very rare": DataSourceSet(sources / Path("properties_very_rare.yaml")),
    "legendary": DataSourceSet(sources / Path("properties_legendary.yaml")),
}


@dataclass
class AttributeMap(Mapping):
    """
    AttributeMap is a data class that is also a mapping, converting a dict
    into an object with attributes. Example:

        >>> amap = AttributeMap(attributes={'foo': True, 'bar': False})
        >>> amap.foo
        True
        >>> amap.bar
        False

    Instantiating an AttributeMap using the from_dict() class method will
    recursively transform dictionary members sinto AttributeMaps:

        >>> nested_dict = {'foo': {'bar': {'baz': True}, 'boz': False}}
        >>> amap = AttributeMap.from_dict(nested_dict)
        >>> amap.foo.bar.baz
        True
        >>> amap.foo.boz
        False

    The dictionary can be accessed directly via 'attributes':

        >>> amap = AttributeMap(attributes={'foo': True, 'bar': False})
        >>> list(amap.attributes.keys()):
        >>>['foo', 'bar']

    Because AttributeMap is a mapping, you can use it anywhere you would use
    a regular mapping, like a dict:

        >>> amap = AttributeMap(attributes={'foo': True, 'bar': False})
        >>> 'foo' in amap
        True
        >>> "{foo}, {bar}".format(**amap)
        True, False


    """
    attributes: field(default_factory=dict)

    def __getattr__(self, attr):
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
        Create a new AttributeMap object using keyword arguments. Dicts are
        recursively converted to AttributeMap objects; everything else is
        passed as-is.
        """
        attrs = {}
        for k, v in sorted(kwargs.items()):
            attrs[k] = AttributeMap.from_dict(v) if type(v) is dict else v
        return cls(attributes=attrs)


@dataclass
class Item(AttributeMap):
    """
    Item is the base class for items, weapons, and spells, and is intended to
    be subclassed to define those things. Item extends AttributeMap to provide
    some helper methods, including the name and description properties.

    Creating Items

    To create an Item, call Item.from_dict() with a dictionary as you would an
    AttributeMap. But unlike the base method, Item.from_dict() processes the
    values of the dictionary and formats any template strings it encounters,
    including templates which reference its own attributes. A simple example:

        >>> properties = dict(
          ?     name='{length}ft. pole',
          ?     weight='7lbs.',
          ?     value=5,
          ?     length=10
          ? )
        >>> ten_foot_pole = Item.from_dict(properties)
        >>> ten_foot_pole.name
        10ft. Pole

    Note that the name value includes a template that refers to the length
    property. This reference is resolved when the Item instance is created.


    Properties Are Special

    The 'properties' attribute has special meaning for Items; it is the mapping
    of the item's in-game properties. For weapons, this includes standard
    properties such as 'light', 'finesse', 'thrown', and so on, but they can be
    anything you like. Item.properties is also unique in that its members'
    templates can contain references to other attributes of the Item. For
    example:

        >>> properties = dict(
          ?     name='{length}ft. pole',
          ?     length=10,
          ?     properties=dict(
          ?         'engraved'=dict(
          ?             description='"Property of {info.owner}!"'
          ?         ),
          ?     ),
          ?     info=dict(
          ?         owner='Jules Ultardottir',
          ?     )
          ? )
        >>> ten_foot_pole = Item.from_dict(properties)
        >>> ten_foot_pole.description
        Engraved. "Property of Jules Ultardottir!"

    Overriding Attributes with Properties

    Properties can also override existing item attributes. Any key in the
    properties dict of the form 'override_<attribute>' will replace the value
    of <attribute> on the item:

        >>> properties = dict(
          ?     name='{length}ft. pole',
          ?     length=10,
          ?     properties=dict(
          ?         'broken'=dict(
          ?             description="The end of this 10ft. pole has been snapped off.",
          ?             override_length=7
          ?         ),
          ?     )
          ? )
        >>> ten_foot_pole = Item.from_dict(properties)
        >>> ten_foot_pole.name
        7ft. Pole
        >>> ten_foot_pole.description
        Broken. The end of this 10ft. pole has been snapped off.

    This is useful when generating randomized Items, as random properties can
    be added to base objects, modifying their attribute; the WeaponGenerator
    (see below) uses overrides to create low-level magic weapons that change
    the basic bludgeoning/piercing/slashing damage to fire, ice, poison...
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
        """
        Summarize the properties of the item, as defined by Item.properties.
        """
        desc = "\n".join([
            k.title() + ". " + v.get('description', '')
            for k, v in self.get("properties", {}).items()
        ])
        return desc.format(**self)

    @classmethod
    def from_dict(cls, attrs: dict):
        """
        Create a new Item object using keyword arguments. Dicts are recursively
        converted to Item objects; everything else is passed as-is.
        """

        attributes = dict()

        # recursively locate and populate template strings
        def _format(obj, this=None):
            # enables use of the 'this' keyword to refer to the current context
            # in a template. Refer to the enchantment sources for an example.
            if this:
                this = AttributeMap.from_dict(this)

            # dicts and lists are descended into
            if type(obj) is dict:
                return AttributeMap.from_dict(
                    dict(
                        (_format(key, this=obj), _format(val, this=obj))
                        for key, val in obj.items()
                    )
                )

            if type(obj) is list:
                return [_format(o, this=this) for o in obj]

            # Strings are formatted wth values from attributes and this. Using
            # attributes is important here, so that values containing template
            # strings are processed before they are referenced.
            if type(obj) is str:
                return obj.format(**attributes, this=this)

            # Any type other than dict, list, and string is returned unaltered.
            return obj

        properties = attrs.pop("properties", {})

        # apply property overrides overrides before anything else
        for prop in properties.values():
            overrides = [k for k in prop.keys() if k.startswith("override_")]
            for o in overrides:
                if prop[o]:
                    attrs[o.replace("override_", "")] = prop[o]

        # step through the supplied attributes and format each member.
        for k, v in sorted(attrs.items(), key=lambda i: '{' in f"{i[0]}{i[1]}"):
            if type(v) is dict:
                attributes[k] = AttributeMap.from_dict(_format(v))
            else:
                attributes[k] = _format(v)

        # process properties now that we have preprocessed everything else
        if properties:
            attributes["properties"] = AttributeMap.from_dict(_format(properties))

        # store the item name as the _name attribute; it is accessable directly, or
        # via the name property. This makes overriding the name convenient for subclassers,
        # which may require naming semantics that cannot be resolved at instantiation time.
        _name = attributes["name"]
        del attributes["name"]

        # At this point, attributes is a dictionary with members of multiple
        # types, but every dict member has been converted to an AttributeMap,
        # and all template strings in the object have been formatted. Return an
        # instance of the Item class using these formatted attributes.
        return cls(_name=_name, attributes=attributes)


class ItemGenerator:
    """
    The base class for random item generators.

    This class is intended to be subclassed, by individual subclasses for each
    type (weapon, item, wand...). An ItemGenerator is instantiated with
    DataSourceSets for base item definitions and rarity, and a dictionary of
    property definitions organized by rarity ('common', 'uncommon'...). This
    module provides a set of pre-defined DataSourceSets (WEAPON_TYPES, RARITY,
    PROPERTIES_BY_RARITY) for this purpose, but subclasses generally provide
    sensible defaults specific to their use.

    A simple subclassing example:

        class SharpStickGenerator(types.ItemGenerator):
            def __init__(self):
                super().__init__(
                    bases=WeightedSet(
                        (dict(name='{type} stick', type='wooden', ...), 0.3),
                        (dict(name='{type} stick', type='lead', ...), 1.0),
                        (dict(name='{type} stick', type='silver', ...), 0.5),
                        (dict(name='{type} stick', type='glass', ...), 0.1),
                    ),
                    raritytypes.RARITY,
                    properties_by_rarity=types.PROPERTIES_BY_RARITY,
                )

    Generating Random Items

    Given an ItemGenerator class, use the ItemGenerator.random() method to
    create randomized tiems. To do this, random() will:

        1. Select a random base
        2. Select a random rarity appropriate for the challenge rating
        3. Select properties appropriate for legendary items

    Example:

        >>> stick = SharpStickGenerator().random(count=1, challenge_rating=17)
        >>> stick[0].name
        Silver Stick
        >>> stick[0].rarity
        legendary
        >>> stick[0].description
        Magical. This magical weapon grants +3 to attack and damage rolls.

    For more complete examples, refer to the various modules in dnd_item.
    """

    # random() will generate instances of this class. Subclassers should
    # override this with a subclass of Item.
    item_class = Item

    def __init__(self, bases: WeightedSet, rarity: WeightedSet, properties_by_rarity: dict):
        self.bases = bases
        self.rarity = rarity
        self.properties_by_rarity = properties_by_rarity

    def _property_count_by_rarity(self, rarity: str) -> int:
        """
        Return a number of properties to add to an item of some rarity. Common items
        have a 10% chance of hanving one property; Legendary items will have either
        2 or 3 properties. This is the primary method by which Items of greater
        rarity become more valuable and wondrous, justifying their rarity.
        """
        property_count_by_rarity = {
            "common": WeightedSet((1, 0.1), (0, 1.0)),
            "uncommon": WeightedSet((1, 1.0)),
            "rare": WeightedSet((1, 1.0), (2, 0.5)),
            "very rare": WeightedSet((1, 0.5), (2, 1.0)),
            "legendary": WeightedSet((2, 1.0), (3, 1.0)),
        }

        # don't try to apply more unique properties to the item than exist in
        # the look-up tables.
        return min(
            property_count_by_rarity[rarity].random(),
            len(self.properties_by_rarity[rarity].members)
        )

    def get_requirements(self, item) -> set:
        """
        Step through all attributes of an object looking for template strings,
        and return the unique set of attributes referenced in those template
        strings.

            >>> props = dict(foo="{one}", bar=dict(baz="{one}", boz="{two.three}"))
            >>> ItemGenerator().get_requirements(props)
            {'one', 'two'}
        """

        # Given "{foo.bar.baz}", capture "foo"
        pat = re.compile(r"{([^\.\}]+)")

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
        """
        Create a dictionary of item attributes appropriate for a given rarity.
        Dictionaries generated by this method are used as arguments to the
        ItemGenerator.from_dict() method.

        Properties From Callbacks

        Property definitions are loaded from ItemGenerator.properties_by_rarity,
        but additional properties can be defined by adding callbacks to the
        ItemGenerator subclass. For example, given the template string:

            {extras.owner}

        if 'extras' does not exist in self.properties_by_rarity,
        random_properties() will invoke the method self.get_extras with the
        properties generated thus far, and add the return value to the item:

            def get_extras(self, **item):
                return dict(
                    'owner': 'Jules Utandottir',
                )

        This will result in:

                >>> item['extras']['owner']
                Jules Ultandottir
        """

        # select a random base
        item = self.bases.random()

        # select a random rarity
        item["rarity"] = self.rarity.random()

        # select a number of properties appropriate to the rarity
        num_properties = self._property_count_by_rarity(item["rarity"]["rarity"])

        # generate the selected number of properties
        properties = {}
        while len(properties) != num_properties:
            thisprop = self.properties_by_rarity[item["rarity"]["rarity"]].random()
            properties[thisprop["name"]] = thisprop

        # Base items might have properties already; weapons have things like
        # 'versatile' and 'two-handed', for example. We'll add these to the
        # properties dict by looking them up properties_by_rarity dict so the
        # item we generate will have information about those base proprities.
        for name in item.pop("properties", "").split(","):
            name = name.strip()
            if name:
                properties[name] = self.properties_by_rarity["base"].source.as_dict()[name]

        item["properties"] = properties

        # Look for template strings that reference item attributes which do not yet exist.
        # Add anything that is missing via a callback.
        predefined = list(item.keys()) + ["this", "_name"]
        for requirement in [r for r in self.get_requirements(item) if r not in predefined]:
            try:
                item[requirement] = getattr(self, f"get_{requirement}")(**item)
            except AttributeError:
                logging.error("{item['name']} requires {self.__class__.__name__} to have a get_{requirement}() method.")
                raise

        return item

    def random(self, count: int = 1, challenge_rating: int = 0) -> list:
        """
        Generate one or more random Item instances by selecting random values
        from the available data sources, appropriate to the specified challenge
        rating.

        Items generated will be appropriate for a challenge rating representing
        an encounter for an adventuring party of four. This will prevent
        lower-level encounters from generating legendary weapons and so on. If
        challenge_rating is 0, a rarity is chosen at random.
        """
        if challenge_rating in range(1, 5):
            frequency = "1-4"
        elif challenge_rating in range(5, 11):
            frequency = "5-10"
        elif challenge_rating in range(11, 17):
            frequency = "11-16"
        elif challenge_rating >= 17:
            frequency = "17"
        else:
            frequency = "default"
        self.rarity.set_frequency(frequency)

        items = []
        for _ in range(count):
            items.append(self.item_class.from_dict(self.random_properties()))
        return items


@dataclass
class GeneratorSource:
    """
    A source for a RollTable instance that uses an ItemGenrator to generate
    random data instead of loading data from a static file source.
    """
    generator: ItemGenerator
    cr: int

    def random_values(self, count: int = 1) -> list:
        vals = sorted(
            (
                item.rarity["sort_order"],
                [item.name, item.rarity["rarity"], item.summary, ", ".join(item.get("properties", [])), item.id],
            )
            for item in self.generator.random(count=count, challenge_rating=self.cr)
        )
        return [v[1] for v in vals]


class RollTable(rolltable.types.RollTable):
    """
    A subclass of RollTable that uses ItemGenerator clsases to create table rows.
    Instantiate it by supplying one or more ItemGenerator sources:

        >>> rt = RollTable(sources[WeaponGenerator])

    For a complete example, refer to th dnd_item.cli.table.
    """
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
            frequency="default",
            die=die,
            hide_rolls=hide_rolls,
        )

    def _config(self):
        self._data = []
        for src in self._sources:
            self._data.append(GeneratorSource(generator=src(), cr=self._cr))

        self._headers = [
            "Name",
            "Rarity",
            "Summary",
            "Properties",
            "ID",
        ]
        self._header_excludes = []
