# Data Sources

This directory contains a series of data source files for item generators. The
format is used by the
[random_sets](https://github.com/evilchili/random-sets/tree/main) package to
create DataSource objects that make it easy to generate and combine randomized
sets with tunable frequency distributions.

* `magic_damage_types.yaml`: types of magical damage that can be applied to weapons
* `properties_base.yaml`: The base properties of mundane items ("light", "thrown," etc)
* `rarity.yaml`: The levels of rarity in D&D, with frequency distributions by challenge rating
* `weapons.yaml`: The basic weapon types (maul, shortsword, halbred, etc)

Besides `properties_base.yaml`, there are several files named `properties_[rarity].yaml`; these
sources define what properties can be applied to items of each rarity. For example, in `properties_rare.yaml` you will find a definition for +2 weapons, but +3 weapons are only in `properties_very_rare.yaml`.

## Data Source File Schema

Let's look at a simple example, from `rarity.yaml`:

```yaml
metadata:
    headers:
      - rarity
      - sort_order
    frequencies:
      default:
        common: 1.0
        uncommon: 1.0
        rare: 1.0
        very rare: 1.0
        legendary: 1.0
common:
  - 0
uncommon:
  - 1
rare:
  - 2
very rare:
  - 3
legendary:
  - 4
```

The first block of the DataSource, `metadata`, contains information about the data. It may have two members, `headers` and `frequencies`. Everything after the `metadata` block is the *data set*. 

### Headers

Headers are applied sequentially to the members of the data when the data set is interpreted as a
table, a list of dictionaries, and so on. A DataSource instance populated with this example would yield the following data structure:

```python
[
    {'rarity': 'common', 'sort_order': 0}},
    {'rarity': 'uncommon, 'sort_order': 1}},
    {'rarity': 'rare, 'sort_order': 2}},
    {'rarity': 'very rare, 'sort_order': 3}},
    {'rarity': 'legendary, 'sort_order': 4}},
]
```

Note that each member of the data set creates its own entry in the list.

This mapping is recursive, such that a member in the data set may contain an arbitrarily-deep structure of arrays and collections; they will be flattened into a serial list and headers applied to each, although this level of complexity is not generally needed for Item properties in this package.

### Frequencies

The frequencies collection defines one or more mappings of frequency distrubitions, from 0.0 to 1.0, for each member in the data set. The `default` data set in our example applies an equal weighting to all members in the set, meaning that by default all rarities defined here are equally likely to be
chosen when a random item is generated.

The full `rarity.yaml` defines several distrubtions organized by challenge rating, making it
impossible to generate legendary items for low-level parties; at higher levels, common items become paradoxically rare.

### Data Set

Everything after the metadata block is the data set; each collection represents a single entry in the set of possible selections. When `DataSource.random()` is called, the return value will be one of these collections, mediated by the specified frequencey distribution.

## Template Strings

Members of the data set can include python-style template strings. These strings are processed when
an item is generated, and can refer to other properties on the item, the base item properties, or even
the member's own properies. Here's an example, from `properties_rare.yaml`:

```yaml
enchanted:
  - '{enchantment.nouns}'
  - '{enchantment.adjectives}'
  - 'Attacks made with this magical weapon do an extra {this.damage} {this.damage_type} damage.'
  - '{enchantment.damage_type}'
  - 1d6
  - 0
  - weapon
```

The `enchanted` property adds magical damage to a weapon. Enchantments are not defined in this file,
though; they are defined in `magic_damage_types.yaml` and look like this:

```yaml
fire:
  - 'flames, fire'
  - 'flaming, burning'
```

When an item is assigned the `enchanted` property, an `enchantment` property is added automatically. The template strings in the data are then resolved using the values from that property. So the nouns and adjectives of the `enchanted` property may resolve to `"flames, fire"` and '`"flames, burning"`, respectively.

Remember that the keyword attributes in the template strings are defined by the headers of the data source; this all works because `magic_damage_types.yaml` defines includes the "nouns" and "adjectives" headeres.

### Base Properties

A template string without a dotted attribute will refer to an item's basic properties. These basic properties are defined by each ItemGenerator class; for Weapons, basic properties are defined in `weapons.yaml` and include *name*, *category*, *type*, *weight*, *damage_type*, *damage*, *range*, *reload*, *value*, and *properties*. Here's an excerpt:

```yaml
metadata:
  headers:
  - name
  - category
  - type
  - weight
  - damage_type
  - damage
  - range
  - reload
  - value
  - properties
Battleaxe:
  - martial
  - Martial
  - '4'
  - Slashing
  - 1d8
  - 5
  - ''
  - '1000'
  - versatile
```

Thus, `{damage_type}` will resolve to "Slashing" in any template string on any property of a Battleaxe.

### The "this" Keyword

The `enchanted` member also uses the keyword `this`. When this property is applied to an item, `this` 
will refer to members of the `enchanted` collection. so `{this.damage}` becomes `1d6`.

`this` can also reference other template strings! In our example, `{this.damage_type}` will resolve first to `{enchantment.damage_type}`, which will in turn resolve to `fire` (because `magic_damage_types.yaml` defines the "damage_type" header).

Putting it all together, a full substitution of values will yield a data set member that looks like this:

```yaml
enchanted:
  - 'flames, fire'
  - 'flaming, burning'
  - 'Attacks made with this magical weapon do an extra 1d6 fire damage.'
  - 'fire'
  - 1d6
  - 0
  - weapon
```


### Reserved Keywords

The following keywords are reserved:

`this`: Refers to the current data set member
`enchantment`: Refers to a random member of the `magic_damage_types.yaml` data set
