from time import sleep
import pytest
from caendr.models.datastore import DatabaseOperation

def sum(a,b):
    return a + b


def test_sum():
    """ It returns the sum of two numbers """
    name = "test_123"
    a = DatabaseOperation(name)
    a.save()
    old_created_on = a.created_on
    print("Sleeping...")
    sleep(2)
    a.save()
    new_created_on = a.created_on
    print(f"old_created_on: {old_created_on} new_created_on: {new_created_on}")
    assert old_created_on == new_created_on