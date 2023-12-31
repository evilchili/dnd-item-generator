import base64
import hashlib
import random
from functools import cached_property

from random_sets.sets import WeightedSet, equal_weights

from dnd_item import types


def random_from_csv(csv: str) -> str:
    """
    Split a comma-separated value string into a list and return a random value.
    """
    return random.choice(csv.split(",")).strip()


class Weapon(types.Item):
    """
    An Item subclass representing weapons, both magical and mundane.

    Much of this subclass is devoted to generating descriptive and entertaining
    weapon names. It also implements a number of handy properties for presentation.
    """

    def _descriptors(self) -> tuple:
        """
        Collect the 'nouns' and 'adjectives' properties from the Item's
        'properties' attribute. This is used by _random_descriptors to choose a
        set of random nouns and adjectives to apply to a weapon name.
        """
        nouns = dict()
        adjectives = dict()
        if not hasattr(self, "properties"):
            return (nouns, adjectives)
        for prop_name, prop in self.properties.items():
            if hasattr(prop, "nouns"):
                nouns[prop_name] = equal_weights(prop.nouns.split(","), blank=False)
            if hasattr(prop, "adjectives"):
                adjectives[prop_name] = equal_weights(prop.adjectives.split(","), blank=False)
        return (nouns, adjectives)

    def _name_template(self, with_adjectives: bool, with_nouns: bool) -> str:
        """
        Generate a WeightedSet of potential name template strings and pick one.

        The possible templates are determined by whether we have selected
        nouns, adjectives, or both to describe the item; we can't use a
        template that includes {adjectives} if no adjectives are defined in the
        Item's properties, for example.

        The weighted distribution is tuned so that we mostly get names of the
        typical form ("Venomous Shortsowrd", "Dagger of Shocks"). Occasionally
        we will select templates resulting in very long names ("Frosty +3 Mace
        of Mighty Striking") or repeitive descriptions ("Flaming Spear of
        Flames"), but not so often as to make all generated items too silly.
        """
        num_properties = len(self.properties)
        options = []
        if with_nouns and not with_adjectives:
            options.append(("{name} of {nouns}", 0.5))
        if with_adjectives and not with_nouns:
            options.append(("{adjectives} {name}", 0.5))
        if with_nouns and with_adjectives:
            if num_properties == 1:
                options.append(("{adjectives} {name} of {nouns}", 1.0))
            elif num_properties > 1:
                options.extend(
                    [
                        ("{adjectives} {name} of {nouns}", 1.0),
                        ("{name} of {adjectives} {nouns}", 0.5),
                    ]
                )
        return WeightedSet(*options).random()

    def _random_descriptors(self):
        """
        Select random nouns and adjectives from the available descriptors in
        the properties attribute.

        This method ensures that if a property adding fire damage to the wepaon
        is chosen, 'Flames' or 'Flaming' or 'Fire' (or whatever is defined on
        that enchantement) is used when naming the Item.

        The randomly-selected set of nouns and/or adjectives will then govern
        the naming template selected; see _random_template() above.
        """
        random_nouns = []
        random_adjectives = []

        (nouns, adjectives) = self._descriptors()
        if not (nouns or adjectives):
            return (random_nouns, random_adjectives)

        def add_word(key, obj, source):
            obj.append(source[key].random().strip())

        seen_nouns = dict()
        for prop_name in set(list(nouns.keys()) + list(adjectives.keys())):

            if prop_name in nouns and prop_name not in adjectives:
                if prop_name not in seen_nouns:
                    # Ensure we only add one noun for each property so taht we
                    # don't end up with Items named like "Mace of Venomous
                    # Venom Poison".
                    add_word(prop_name, random_nouns, nouns)
                    seen_nouns[prop_name] = True

            elif prop_name in adjectives and prop_name not in nouns:
                add_word(prop_name, random_adjectives, adjectives)

            if prop_name in nouns and prop_name in adjectives:
                # if the property has both nouns and adjectives, select one
                # or the other or both, for the weapon name. Both leads to
                # spurious names like 'thundering dagger of thunder', so we
                # we reduce the likelihood of this eventuality so it is an
                # occasionl bit of silliness, not consistently silly.
                val = random.random()
                if val <= 0.4 and prop_name not in seen_nouns:
                    add_word(prop_name, random_nouns, nouns)
                    seen_nouns[prop_name] = True
                elif val <= 0.8:
                    add_word(prop_name, random_adjectives, adjectives)
                else:
                    add_word(prop_name, random_nouns, nouns)
                    add_word(prop_name, random_adjectives, adjectives)

        # Join multiple nouns together, so that instead of "Staff of Strikes
        # Cold" we get "Staff of Strikes and Cold." Adjectives we just join
        # together ("Staff of Frosty Striking")
        random_nouns = " and ".join(random_nouns)
        random_adjectives = " ".join(random_adjectives)
        return (random_nouns, random_adjectives)

    @cached_property
    def name(self) -> str:
        """
        Generate and cache a random name for the Weapon based on its properties.

        This method selects a subset of random nouns and adjectives from the
        Weapon's properties, a random name string template compatible with
        those descriptors, and returns a formatted title string. The return
        value is cached because there are multiple possisble names for a Weapon
        with the same set of properties, and we don't want multiple references
        to self.name to return different values on the same instance.
        """
        base_name = super().name
        (nouns, adjectives) = self._random_descriptors()
        if not (nouns or adjectives):
            return base_name

        template = self._name_template(
            with_adjectives=True if adjectives else False,
            with_nouns=True if nouns else False,
        )
        return template.format(**self, adjectives=adjectives, nouns=nouns, name=base_name).title()

    @property
    def to_hit(self):
        """
        Return a string summarizing the total bonus to hit from this weapon and its properties. This
        could be either a single number (+2), a die roll (1d6), or a combination of both (1d6+2).
        """
        bonus_val = 0
        bonus_dice = ""
        if not hasattr(self, "properties"):
            return ""
        for prop in self.properties.values():
            mod = getattr(prop, "to_hit", None)
            if not mod:
                continue
            if type(mod) is int:
                bonus_val += mod
            elif type(mod) is str:
                bonus_dice += f"+{mod}"
        return f"+{bonus_val}{bonus_dice}"

    @property
    def damage_dice(self):
        """
        Return a string summarizing the damage done by a hit with this weapon
        by combining all the damage types and dice from the Weapon's
        properties. Examples:
            - 5 Bludgeoning
            - 1d6 Piercing
            - 1d8+1 Thunder
            - 1d6+1 Slashing + 1d4 Thunder + 3 Poison
        """
        if not hasattr(self, "properties"):
            return ""
        dmg = {self.damage_type: str(self.damage) or ""}

        for prop in self.properties.values():
            mod = getattr(prop, "damage", None)
            if not mod:
                continue
            key = str(prop.damage_type)
            this_damage = dmg.get(key, "")
            if this_damage:
                dmg[key] = f"{this_damage}+{mod}"
            else:
                dmg[key] = mod

        return " + ".join([f"{v} {k}" for k, v in dmg.items()])

    @property
    def summary(self):
        """
        Return a one-line summary of the Weapon's attack. For example:

            +2 to hit, 5 ft., 1 tgts. 1d6+2 Piercing + 1d6 Fire
        """
        return f"{self.to_hit} to hit, {self.range} ft., {self.targets} tgts. {self.damage_dice}"

    @property
    def details(self):
        """
        Return details of the Weapon as a multi-line string.
        """
        props = ", ".join(self.get("properties", dict()).keys())
        return "\n".join(
            [
                f"{self.name}",
                f" * {self.rarity.rarity} {self.category} weapon ({props})",
                f" * {self.summary}",
                f"\n{self.description}\n",
            ]
        )

    @cached_property
    def id(self):
        """
        Generate a unique ID for this weapon. Unlike self.name, which may have
        any of several possisble generated values based on the Weapon's
        properties, this property will generate the same ID every for every
        instance with the same properties.

        This is useful for asserting equality between instances, which may
        be helpful when (for example) generating weapon look-up tables,
        web pages, item cards, and so on.
        """
        sha1bytes = hashlib.sha1(
            "".join(
                [
                    self._name,
                    self.to_hit,
                    self.damage_dice,
                ]
            ).encode()
        )

        # Only use the first ten characteres of the encoded value. This
        # increases the likelihood of hash collisions, but 10 characters is far
        # more than is necessary to encode all possible weapons generated by
        # this package, and 10 is friendlier for user-facing use casees, such
        # as stub URLs.
        return base64.urlsafe_b64encode(sha1bytes.digest()).decode("ascii")[:10]


class WeaponGenerator(types.ItemGenerator):
    """
    A subclass of ItemGenerator that generates Weapon instances.
    """
    item_class = Weapon

    def __init__(
        self,
        bases: WeightedSet = types.WEAPON_TYPES,
        rarity: WeightedSet = types.RARITY,
        properties_by_rarity: dict = types.PROPERTIES_BY_RARITY,
    ):
        super().__init__(bases=bases, rarity=rarity, properties_by_rarity=properties_by_rarity)

    def random_properties(self) -> dict:
        # add missing base weapon defaults
        # TODO: update the sources then  delete this method
        item = super().random_properties()
        item["targets"] = 1
        if item["category"] == "Martial":
            if not item["range"]:
                item["range"] = ""
        return item

    def get_enchantment(self, **attrs) -> dict:
        """
        PROPERTIES_BY_RARITY includes references to enchamentments, so make
        sure we know how to generate a random enchantment when it is referenced
        by a template string.
        """
        prop = types.ENCHANTMENT.random()
        prop["adjectives"] = random_from_csv(prop["adjectives"])
        prop["nouns"] = random_from_csv(prop["nouns"])
        return prop
