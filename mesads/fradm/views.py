from dal import autocomplete
from django.contrib.postgres.lookups import Unaccent
from django.db.models.functions import Lower

from .models import EPCI, Commune, Prefecture


class CommuneAutocompleteView(autocomplete.Select2QuerySetView):
    """This view is called by routes /commune/autocomplete and
    /commune/<departement>/autocomplete, so kwargs['departement'] is optional.
    """

    def get_queryset(self):
        departement = self.kwargs.get("departement", "").lower()

        if self.q:
            # For the row with departement=35 and libelle=Melesse, the query
            # below returns the row for the following inputs:
            # * "Melesse"
            # * "35"
            # * "35 - melesse"
            # * "35 - mele"

            departement_filter = ""
            if departement:
                departement_filter = f"AND LOWER(departement) = '{departement}'"

            sql = (
                f"SELECT * FROM {Commune.objects.model._meta.db_table} "
                "WHERE "
                "REGEXP_REPLACE(UNACCENT(departement || libelle), '[^\\w]', '', 'g') "
                "ILIKE '%%' || REGEXP_REPLACE(UNACCENT(%s), '[^\\w]', '', 'g') || '%%'"
                f"{departement_filter} ORDER BY id"
            )
            qs = Commune.objects.raw(
                sql,
                [self.q],
            )
            return qs

        qs = Commune.objects
        if departement:
            qs = qs.annotate(departement_lower=Lower("departement"))
            qs = qs.filter(departement_lower=departement)

        return qs.order_by("id")


class EPCIAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = EPCI.objects.annotate(unaccent_name=Unaccent("name")).all()

        departement = self.kwargs.get("departement", "").lower()

        if departement:
            qs = qs.annotate(departement_lower=Lower("departement"))
            qs = qs.filter(departement_lower=departement)

        if self.q:
            qs = qs.filter(unaccent_name__icontains=self.q)

        return qs.order_by("id")


class PrefectureAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if self.q:
            qs = Prefecture.objects.raw(
                """
                SELECT * FROM """
                + Prefecture.objects.model._meta.db_table
                + """
                WHERE REGEXP_REPLACE(UNACCENT(numero || libelle), '[^\\w]', '', 'g')
                ILIKE '%%' || REGEXP_REPLACE(UNACCENT(%s), '[^\\w]', '', 'g') || '%%'
                ORDER BY id
            """,
                (self.q,),
            )
            return qs

        qs = Prefecture.objects.all()
        return qs.order_by("id")
