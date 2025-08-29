from django.db.models import Func, IntegerField


class SplitPart(Func):
    """The SPLIT_PART PostgreSQL function is not available in Django. Create a
    custom function to use it."""

    function = "SPLIT_PART"
    output_field = IntegerField()
