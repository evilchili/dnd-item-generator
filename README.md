# D&D Weapon, Item, and Loot Generator

**WIP!**

This package includes a library and CLI for generating randomized weapons, items, and loot for Dungeons &amp; Dragons, 5th edition.

## Usage

The `dnd-item` command-line utility supports several comments:

* **weapon**: Generate weapons 
* **roll-table**: Generate roll tables of random items

### Examples:

```shell
% dnd-item weapon
**Freezing +3 Longbow Of Mighty Strikes**
 * very rare martial weapon (ammunition, enchanted, heavy, magical, two-handed)
 * +3 to hit, 150/600 ft., 1 tgts. 1d8+3 Piercing + 1d8 cold

**Ammunition.** You can use a weapon that has the ammunition property to make a ranged attack only if you have ammunition to fire from the weapon. Each time you attack with the weapon, you expend one piece of ammunition.
Drawing the ammunition from a quiver, case, or other container is part of the attack (you need a free hand to load a one-handed weapon).
**Enchanted.** Attacks made with this magical weapon do an extra 1d8 cold damage.
**Heavy.** Small creatures have disadvantage on attack rolls with heavy weapons. A heavy weapon’s size and bulk make it too large for a Small creature to use effectively.
**Magical.** This magical weapon grants +3 to attack and damage rolls.
**Two-Handed.** This weapon requires two hands when you attack with it.

```
