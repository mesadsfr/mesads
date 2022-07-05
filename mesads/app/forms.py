from django.contrib.contenttypes.models import ContentType
from django.forms import BaseInlineFormSet, inlineformset_factory

from mesads.fradm.forms import FrenchAdministrationForm

from .models import ADS, ADSManager, ADSUser


class ADSManagerForm(FrenchAdministrationForm):
    """Form to retrieve an ADSManager.

    The base class FrenchAdministrationForm displays three fields to select
    either an EPCI, a Commune or a Prefecture, and allows to select only one of
    them.

    This class sets the field ads_manager to the selected choice.
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


class AutoDeleteADSUserFormSet(BaseInlineFormSet):
    """By default, to remove an entry from a formset, you need to render a
    checkbox "DELETE" that needs to be checked to remove the entry.

    Here, we override the private method _should_delete_form to ask to remove
    the entry if all the fields are empty.
    """
    def _should_delete_form(self, form):
        for key in set(form.fields.keys()) - set(['ads', 'id', 'DELETE']):
            if form.cleaned_data.get(key):
                return super()._should_delete_form(form)
        return True


ADSUserFormSet = inlineformset_factory(
    ADS, ADSUser, fields=('status', 'name', 'siret'),
    can_delete=True, extra=10, max_num=10,
    formset=AutoDeleteADSUserFormSet
)
