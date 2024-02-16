from django.core.exceptions import ValidationError
from django.forms.fields import BooleanField


class NullBooleanField(BooleanField):
    """NullBooleanField allows the following:

    >>> from mesads.app.widgets import BooleanSelect

    >>> class MyModel(models.Model):
    ...     myfield = models.BooleanField(blank=False, null=False)

    >>> class MyForm(forms.ModelForm):
    ...     class Meta:
    ...         model = MyModel
    ...             fields = ['myfield']
    ...     myfield = NullBooleanField(widget=BooleanSelect)

    If BooleanField was used instead of NullBooleanField, and the the HTML form
    submits an empty value (because the first default option submitted is
    `<option disabled selected value>Select an option</option>`), the form would
    return an error because the field is required (because `blank=False`), but
    also when the "false" option is selected.

    NullBooleanField makes the distinction between the "false" option and the
    empty value.
    """

    def to_python(self, value):
        """Override the behavior of the base class which converts None to False."""
        if value is None:
            return None
        return super().to_python(value)

    def validate(self, value):
        """Override the behavior of the base class which triggers an error when value is False."""
        if value is None and self.required:
            raise ValidationError(self.error_messages["required"], code="required")
