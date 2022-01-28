from django.db.models import Q

from dal import autocomplete

from .models import Commune, EPCI, Prefecture


class CommuneAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Commune.objects.none()

        qs = Commune.objects.all()

        if self.q:
            qs = qs.filter(
                Q(libelle__icontains=self.q) | Q(departement__icontains=self.q)
            )

        return qs.order_by('id')


class EPCIAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return EPCI.objects.none()

        qs = EPCI.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs.order_by('id')


class PrefectureAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Prefecture.objects.none()

        qs = Prefecture.objects.all()

        if self.q:
            qs = qs.filter(
                Q(libelle__icontains=self.q) | Q(numero__icontains=self.q)
            )

        return qs.order_by('id')
