import random
import base64
import hashlib

from functools import cached_property

from dnd_item import types
from random_sets.sets import WeightedSet, equal_weights


def random_from_csv(csv: str) -> str:
    return random.choice(csv.split(',')).strip()


class Weapon(types.Item):
    """
    """

    def _descriptors(self) -> tuple:
        """
        Collect the nouns and adjectives from the properties of this item.
        """
        nouns = dict()
        adjectives = dict()
        if not hasattr(self, 'properties'):
            return (nouns, adjectives)
        for prop_name, prop in self.properties.items():
            if hasattr(prop, 'nouns'):
                nouns[prop_name] = equal_weights(prop.nouns.split(','), blank=False)
            if hasattr(prop, 'adjectives'):
                adjectives[prop_name] = equal_weights(prop.adjectives.split(','), blank=False)
        return (nouns, adjectives)

    def _name_template(self, with_adjectives: bool, with_nouns: bool) -> str:
        num_properties = len(self.properties)
        options = []
        if with_nouns and not with_adjectives:
            options.append(('{name} of {nouns}', 0.5))
        if with_adjectives and not with_nouns:
            options.append(('{adjectives} {name}', 0.5))
        if with_nouns and with_adjectives:
            if num_properties == 1:
                options.append(('{adjectives} {name} of {nouns}', 1.0))
            elif num_properties > 1:
                options.extend([
                    ('{adjectives} {name} of {nouns}', 1.0),
                    ('{name} of {adjectives} {nouns}', 0.5),
                ])
        return WeightedSet(*options).random()

    def _random_descriptors(self):
        """
        Select random nouns and adjectives from the object
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

        random_nouns = ' and '.join(random_nouns)
        random_adjectives = ' '.join(random_adjectives)
        return (random_nouns, random_adjectives)

    @cached_property
    def name(self) -> str:
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
        bonus_val = 0
        bonus_dice = ''
        if not hasattr(self, 'properties'):
            return ''
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
        if not hasattr(self, 'properties'):
            return ''
        dmg = {
            self.damage_type: str(self.damage) or ''
        }

        for prop in self.properties.values():
            mod = getattr(prop, 'damage', None)
            if not mod:
                continue
            key = str(prop.damage_type)
            this_damage = dmg.get(key, '')
            if this_damage:
                dmg[key] = f"{this_damage}+{mod}"
            else:
                dmg[key] = mod

        return ' + '.join([f"{v} {k}" for k, v in dmg.items()])

    @property
    def summary(self):
        return f"{self.to_hit} to hit, {self.range} ft., {self.targets} tgts. {self.damage_dice}"

    @property
    def details(self):
        """
        Format the item properties as nested bullet lists.
        """
        props = ', '.join(self.get('properties', dict()).keys())
        return "\n".join([
            f"{self.name}",
            f" * {self.rarity.rarity} {self.category} weapon ({props})",
            f" * {self.summary}",
            f"\n{self.description}\n"
        ])

    @property
    def id(self):
        sha1bytes = hashlib.sha1(''.join([
            self._name, self.to_hit, self.damage_dice,
        ]).encode())
        return base64.urlsafe_b64encode(sha1bytes.digest()).decode('ascii')[:10]


class WeaponGenerator(types.ItemGenerator):
    item_class = Weapon

    def __init__(
        self,
        bases: WeightedSet = types.WEAPON_TYPES,
        rarity: WeightedSet = types.RARITY,
        properties_by_rarity: dict = types.PROPERTIES_BY_RARITY,
    ):
        super().__init__(bases=bases, rarity=rarity, properties_by_rarity=properties_by_rarity)

    def random_properties(self) -> dict:
        # add missing base weapon defaults (TODO: update the sources)
        item = super().random_properties()
        item['targets'] = 1
        if item['category'] == 'Martial':
            if not item['range']:
                item['range'] = ''
        return item

    # handlers for extra properties

    def get_enchantment(self, **attrs) -> dict:
        prop = types.ENCHANTMENT.random()
        prop['adjectives'] = random_from_csv(prop['adjectives'])
        prop['nouns'] = random_from_csv(prop['nouns'])
        return prop
