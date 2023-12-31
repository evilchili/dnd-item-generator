from dnd_item import types


def test_Item_attributes():
    assert types.Item.from_dict(dict(
        name='{length}ft. Pole',
        weight='7lbs.',
        value=5,
        length=10
    )).name == '10ft. Pole'


def test_item_nested_attributes():
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
