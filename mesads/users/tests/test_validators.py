import pytest
from django.core.exceptions import ValidationError

from mesads.users.validators import (
    DigitValidator,
    LowercaseValidator,
    UppercaseValidator,
)


def test_get_help_text_uppercase_validator():
    validator = UppercaseValidator()
    assert (
        validator.get_help_text()
        == "Votre mot de passe doit contenir au moins une lettre majuscule."
    )


def test_uppercase_validator_exception():
    validator = UppercaseValidator()
    with pytest.raises(ValidationError) as excinfo:
        validator.validate("azertyuiop")

    assert (
        excinfo.value.message
        == "Le mot de passe doit contenir au moins une lettre majuscule."
    )


def test_get_help_text_lowercase_validator():
    validator = LowercaseValidator()
    assert (
        validator.get_help_text()
        == "Votre mot de passe doit contenir au moins une lettre minuscule."
    )


def test_lowercase_validator_exception():
    validator = LowercaseValidator()
    with pytest.raises(ValidationError) as excinfo:
        validator.validate("AZERTYUIOP")

    assert (
        excinfo.value.message
        == "Le mot de passe doit contenir au moins une lettre minuscule."
    )


def test_get_help_text_digit_validator():
    validator = DigitValidator()
    assert (
        validator.get_help_text()
        == "Votre mot de passe doit contenir au moins un chiffre."
    )


def test_digit_validator_exception():
    validator = DigitValidator()
    with pytest.raises(ValidationError) as excinfo:
        validator.validate("AZERTYuiop")

    assert excinfo.value.message == "Le mot de passe doit contenir au moins un chiffre."
