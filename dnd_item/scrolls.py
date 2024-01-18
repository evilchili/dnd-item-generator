from dnd_item import types
from rolltable.tables import spells


class Scroll(types.Item):
    """
    A magic scroll.
    """

    @property
    def name(self):
        return 'Scroll of {spell.name}'.format(**self).title()

    @property
    def summary(self):
        if self.spell.level == 'cantrip':
            return f"{self.name} ({self.spell.school} {self.spell.level})"
        else:
            return f"{self.name} ({self.spell.level} level {self.spell.school})"

    details = summary


class ScrollGenerator(types.ItemGenerator):
    item_class = Scroll

    def random_properties(self, rarity: str = '') -> dict:
        """
        Every scroll must have a randomly-selected spell.
        """
        item = super().random_properties(rarity)

        # maps maximum spell level to a rarity level (0=common...)
        frequencies = {
            'common': 'first',
            'uncommon': 'third',
            'rare': 'fifth',
            'very rare': 'seventh',
            'legendary': 'ninth'
        }

        # Create a rolltable of spells at an appropriate level with one row
        spells.reset()
        spells.die = 1
        spells.datasources[0].set_frequency(frequencies[item['rarity']['rarity']])

        # add the spell to the item as a dictionary
        keys = [h.lower().replace(' ', '_') for h in spells.headers]
        item['spell'] = dict(zip(*[keys, spells.rows[1][1:]]))

        return item
