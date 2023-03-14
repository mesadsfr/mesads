from django.forms.widgets import NullBooleanSelect


class BooleanSelect(NullBooleanSelect):
    """By default, BooleanField with null=True use the widget NullBooleanSelect,
    which displays a select with three options: "Unknown", "Yes" and "No".

    This widget can be used to render a select with only two options: "Yes" and
    "No".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = [(name, label) for name, label in self.choices if name != 'unknown']
