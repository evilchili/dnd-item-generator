# D&D Weapon, Item, and Loot Generator

**WIP!**

This package includes a library and CLI for generating randomized weapons, items, and loot for 
Dungeons &amp; Dragons, 5th edition.

## Usage

The `dnd-item` command-line utility supports several comments:

* **item**: Generate a random item (the default)
* **weapon**: Generate a basic, non-magical weapon
* **magical-weapon**: Generate a weapon with an added magical damage type

### Examples:

```shell
% dnd-item weapon
Pike
 * type.category: martial
 * type.damage: Piercing
 * type.die: 1d10
 * type.properties: heavy, reach, two-handed
 * type.range: None
 * type.reload: 
 * type.type: Martial
 * type.value: 500
 * type.weight: 18
```

```shell
% dnd-item magic-weapon
Shortsword Of Thunder
 * magic.adjective: booming
 * magic.die: 1d4
 * magic.noun: thunder
 * type.category: martial
 * type.damage: Piercing
 * type.die: 1d6
 * type.properties: finesse, light
 * type.range: None
 * type.reload: 
 * type.type: Martial
 * type.value: 1000
 * type.weight: 2
```


