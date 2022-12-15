import re

from logzero import logger

from caendr.models.error import InternalError



class WormbaseVersion():

    def __init__(self, value):

        if value is None:
            self._value = None

        # Copy value of another Wormbase Version object
        elif isinstance(value, WormbaseVersion):
            self._value = value._value

        # Filter out types other than str
        elif not isinstance(value, str):
            logger.warning(f'Cannot set WormBase Version with object of type {type(value)} (expected str)')
            raise InternalError()

        # Validate desired new value matches expected format
        elif not WormbaseVersion.validate(value):
            logger.warning(f'Invalid WormBase Version String: "{value}"')
            raise InternalError()

        # If all checks passed, use uppercase string value
        else:
            self._value = value.upper()


    def __repr__(self):
        return f'<WB Ver "{self._value}">'

    def __str__(self):
        return self._value

    def __eq__(self, other):
        return self._value == other._value

    def __bool__(self):
        return self._value is not None


    @classmethod
    def validate(cls, value):

        # Return None as-is
        if value is None:
            return None

        # Validate value field of WormbaseVersion class
        elif isinstance(value, WormbaseVersion):
            return WormbaseVersion.validate(value._value)

        # Check string value against RegEx 'WS###', e.g. 'WS276'
        return isinstance(value, str) and bool(re.match(r'^WS[0-9]+$', value, flags=re.IGNORECASE))



class WormbaseProjectNumber():

    def __init__(self, value):

        if value is None:
            self._value = None

        # Copy value of another Wormbase Project Number object
        elif isinstance(value, WormbaseProjectNumber):
            self._value = value._value

        # Filter out types other than str
        elif not isinstance(value, str):
            logger.warning(f'Cannot set WormBase Project Number with object of type {type(value)} (expected str)')
            raise InternalError()

        # Validate desired new value matches expected format
        elif not WormbaseProjectNumber.validate(value):
            logger.warning(f'Invalid WormBase Project Number String: "{value}"')
            raise InternalError()

        # If all checks passed, use uppercase string value
        else:
            self._value = value.upper()


    def __repr__(self):
        return f'<WB Proj Num "{self._value}">'

    def __str__(self):
        return self._value

    def __eq__(self, other):
        return self._value == other._value

    def __bool__(self):
        return self._value is not None


    @classmethod
    def validate(cls, value):

        # Return None as-is
        if value is None:
            return None

        # Validate value field of WormbaseProjectNumber class
        elif isinstance(value, WormbaseProjectNumber):
            return WormbaseProjectNumber.validate(value._value)

        # Check string value against RegEx
        return isinstance(value, str) and bool(re.match(r'^PRJNA[0-9]+$', value, flags=re.IGNORECASE))


# Test code
"""
    valid_1 = WormbaseVersion('WS123')
    valid_2 = WormbaseVersion(valid_1)
    print(valid_1, valid_2, valid_1 == valid_2)    # True

    none_val = WormbaseVersion(None)
    print(none_val, valid_1 == none_val)           # False

    print(WormbaseVersion.validate(valid_1))       # True
    print(WormbaseVersion.validate(baz))           # None

    print(WormbaseVersion.validate('WS456'))       # True
    print(WormbaseVersion.validate('456'))         # False
    print(WormbaseVersion.validate(456))           # False
    print(WormbaseVersion.validate(None))          # None


    try:
        invalid_1 = WormbaseVersion(456)
    except Exception as e:
        pass

    try:
        invalid_2 = WormbaseVersion('456')
    except Exception as e:
        pass
"""