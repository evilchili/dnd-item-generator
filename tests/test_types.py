from dnd_item import types


def test_item_attributes():
    item = types.Item.from_dict(
        foo='bar',
        baz={
            'qaz': True
        }
    )
    assert item.baz.qaz is True
