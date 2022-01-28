from django.contrib.contenttypes.models import ContentType

from mesads.fradm.forms import FrenchAdministrationForm

from .models import ADSManager


class ADSManagerForm(FrenchAdministrationForm):
    """Form to retrieve an ADSManager.

    The base class displays three fields to select either an EPCI, a Commune or
    a Prefecture, and allows to select only one of them.
    """
    def clean(self):
        # super() method ensures only one field is set
        super().clean()

        obj = list({k: v for k, v in self.cleaned_data.items() if v}.values())[0]

        content_type = ContentType.objects.get_for_model(obj)
        manager = ADSManager.objects.get(
            content_type=content_type,
            object_id=obj.id
        )

        self.cleaned_data['ads_manager'] = manager
