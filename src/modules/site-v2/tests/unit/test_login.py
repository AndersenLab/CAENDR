import pytest

from caendr.models.datastore import User
from caendr.services.cloud.secret import get_secret

PASSWORD_PEPPER = get_secret('PASSWORD_PEPPER')


def test_new_user():
    user = User(username='test_user', password='password', salt=PASSWORD_PEPPER, email='test_user@mti.com', roles=['user'])
    assert user.username == 'test_user'
    assert user.email == 'test_user@mti.com'
    assert user.password != 'password'
    assert user.roles == ['user']
   
