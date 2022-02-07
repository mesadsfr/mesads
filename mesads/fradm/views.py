from dal import autocomplete

from .models import Commune, EPCI, Prefecture


class CommuneAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Commune.objects.none()

        if self.q:
            # For the row with departement=35 and libelle=Melesse, the query
            # below returns the row for the following inputs:
            # * "Melesse"
            # * "35"
            # * "35 - melesse"
            # * "35 - mele"
            qs = Commune.objects.raw('''
                SELECT * FROM ''' + Commune.objects.model._meta.db_table + '''
                WHERE REGEXP_REPLACE(departement || libelle, '[^\\w]', '', 'g')
                ILIKE '%%' || REGEXP_REPLACE(%s, '[^\\w]', '', 'g') || '%%'
                ORDER BY id
            ''', [self.q])
            return qs

        qs = Commune.objects.all()
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

        if self.q:
            qs = Prefecture.objects.raw('''
                SELECT * FROM ''' + Prefecture.objects.model._meta.db_table + '''
                WHERE REGEXP_REPLACE(numero || libelle, '[^\\w]', '', 'g')
                ILIKE '%%' || REGEXP_REPLACE(%s, '[^\\w]', '', 'g') || '%%'
                ORDER BY id
            ''', (self.q,))
            return qs

        qs = Prefecture.objects.all()
        return qs.order_by('id')
