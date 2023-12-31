from dnd_item import types


def test_AttributeMap():
    assert types.AttributeMap(attributes={'foo': True, 'bar': False}).foo is True


def test_AttributeMap_nested():
    nested_dict = {'foo': {'bar': {'baz': True}, 'boz': False}}
    amap = types.AttributeMap.from_dict(nested_dict)
    assert amap.foo.bar.baz is True
    assert amap.foo.boz is False


def test_AttributeMap_list():
    amap = types.AttributeMap(attributes={'foo': True, 'bar': False})
    assert list(amap.attributes.keys()) == ['foo', 'bar']


def test_AttributeMap_mapping():
    amap = types.AttributeMap(attributes={'foo': True, 'bar': False})
    assert 'foo' in amap
    assert '{foo}, {bar}'.format(**amap) == 'True, False'


def test_Item_attributes():
    assert types.Item.from_dict(dict(
        name='{length}ft. Pole',
        weight='7lbs.',
        value=5,
        length=10
    )).name == '10ft. Pole'


def test_Item_nested_attributes():
    assert types.Item.from_dict(dict(
        name='{length}ft. Pole',
        length=10,
        properties=dict(
            engraved=dict(
                description='"Property of {info.owner}!"'
            ),
        ),
        info=dict(
            owner='Jules Ultardottir',
        )
    )).description == 'Engraved. "Property of Jules Ultardottir!"'


def test_Item_overrides():
    attrs = dict(
        name='{length}ft. Pole',
        length=10,
        properties=dict(
            broken=dict(
                description="The end of this 10ft. pole has been snapped off.",
                override_length=7
            ),
        )
    )
    ten_foot_pole = types.Item.from_dict(attrs)
    assert ten_foot_pole.name == '7ft. Pole'
    assert ten_foot_pole.description == 'Broken. The end of this 10ft. pole has been snapped off.'


def test_ItemGenerator_subclass():

    class SharpStickGenerator(types.ItemGenerator):
        def __init__(self):
            super().__init__(
                bases=types.WeightedSet(
                    (dict(name='{type} stick', type='wooden'), 0.3),
                    (dict(name='{type} stick', type='lead'), 1.0),
                    (dict(name='{type} stick', type='silver'), 0.5),
                    (dict(name='{type} stick', type='glass'), 0.1),
                ),
                rarity=types.RARITY,
                properties_by_rarity=types.PROPERTIES_BY_RARITY,
            )

    stick = SharpStickGenerator().random(count=1, rarity='common')
    assert stick[0].name in [
        'wooden stick',
        'lead stick',
        'silver stick',
        'glass stick',
    ]
    assert stick[0].rarity.rarity == 'common'
