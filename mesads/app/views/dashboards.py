from datetime import timedelta
import collections

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView

from ..models import (
    ADS,
    ADSManager,
    ADSManagerAdministrator,
)


class DashboardsView(TemplateView):
    template_name = "pages/ads_register/dashboards_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"], ctx["stats_total"] = self.get_stats()
        ctx["ads_updates_stats"] = self.ads_updates_stats()
        return ctx

    def ads_updates_stats(self):
        """This function uses a raw SQL query to retrieve the list of ADS ids
        that have been updated, grouped by date.

        It is using the reversion_version to identify the updates.

        The query built is the following (pseudo-code)

        1. list all the updates in the ADS table

            subq = SELECT object_id, date_created
            FROM reversion_version JOIN reversion_revision
            WHERE reversion_version.content_type_id = <content type of ADS>

        2. for each object with a foreign key to an ADS (ADSLegalFile, ADSUser),
           also list the updates and append to the previous list

            subq = subq + 'UNION' + SELECT serialized_data->0->'fields'->>'ads', date_created
            FROM reversion_version JOIN reversion_revision
            WHERE reversion_version.content_type_id = <content type of related model>

        3. the list built might contains duplicates (if the model and the
           related model have both been updated at the same time). We group by
           ads id and by date.
        """
        # For each update of an ADS, retrieve the date of the update and the ADS id
        subq = f"""
            SELECT
                reversion_version.object_id AS ads_id,
                reversion_revision.date_created AS "when"
            FROM
                reversion_version
            JOIN reversion_revision
                ON reversion_version.revision_id = reversion_revision.id
            WHERE reversion_version.content_type_id = {ContentType.objects.get_for_model(ADS).id}
        """

        # For each object with a foreign key to an ADS, retrieve the date of the
        # update and the ADS id, and make a union with the previous query.
        for related_object in ADS._meta.related_objects:
            subq += f"""
            UNION

            SELECT
                reversion_version.serialized_data::jsonb->0->'fields'->>'{related_object.field.name}' AS ads_id,
                reversion_revision.date_created AS "when"
            FROM
                reversion_version
            JOIN reversion_revision
                ON reversion_version.revision_id = reversion_revision.id

            WHERE reversion_version.content_type_id = {ContentType.objects.get_for_model(related_object.related_model).id}
            """

        # Group by day, limit to the last 30 days
        query_by_day = f"""
        WITH updates_by_date AS ({subq})
        SELECT
            DATE_TRUNC('day', updates_by_date."when") AS "when",
            ARRAY_AGG(updates_by_date.ads_id) AS "ads_list"
        FROM updates_by_date
        WHERE updates_by_date."when" >= NOW() - INTERVAL '30 day'
        GROUP BY
            DATE_TRUNC('day', updates_by_date."when")
        ORDER BY
            DATE_TRUNC('day', updates_by_date."when")
        ;
        """
        query_by_month = f"""
        WITH updates_by_date AS ({subq})
        SELECT
            DATE_TRUNC('month', updates_by_date."when") AS "when",
            ARRAY_AGG(updates_by_date.ads_id) AS "ads_list"
        FROM updates_by_date
        GROUP BY
            DATE_TRUNC('month', updates_by_date."when")
        ORDER BY
            DATE_TRUNC('month', updates_by_date."when")
        ;
        """
        ret = {}
        with connection.cursor() as cursor:
            cursor.execute(query_by_day)
            ret["by_day"] = ((row[0], row[1]) for row in cursor.fetchall())

            cursor.execute(query_by_month)
            ret["by_month"] = ((row[0], row[1]) for row in cursor.fetchall())
        return ret

    def get_stats(self):
        """This function returns a tuple of two values:

        * stats: a list of dictionaries containing the following keys:
            - obj: the ADSManagerAdministrator instance
            - ads: a dictionary where keys represent the period (now, 3 months
              ago, 6 months ago, 12 months ago), and values are the number of ADS
              for this ADSManagerAdministrator
            - users: a dictionary where keys represent the period (now, 3 months
              ago, 6 months ago, 12 months ago), and values are the number of
              accounts who can create ADS for this ADSManagerAdministrator

        >>> [
        ...      obj: <ADSManagerAdministrator object>
        ...      'ads': {
        ...          'now': <int, number of ADS currently registered>
        ...          '3_months': <number of ADS updated less than 3 months ago>
        ...          '6_months':
        ...          '12_months':
        ...      },
        ...      'users': {
        ...          'now': <int, number of users with permissions to create ADS>
        ...          '3_months': <number of users 3 months ago>
        ...          '6_months':
        ...          '12_months':
        ...       }
        ...  ]

        * stats_total: a dictionary containing the keys 'ads' and 'users', and
          the values are dictionaries where keys represent the period, and
          values are the total number of ADS and users.

        >>> {
        ...     'ads': {
        ...         'now': <int, total number of ADS currently registered>,
        ...         '3_months': <total number of ADS updated less than 3 months ago>,
        ...         '6_months': <total number of ADS updated less than 6 months ago>,
        ...         '12_months': <total number of ADS updated less than 12 months ago>,
        ...     },
        ...     'users': { ... }
        ... }
        """
        now = timezone.now()

        stats = collections.defaultdict(lambda: {"obj": None, "ads": {}, "users": {}})

        stats_total = {
            "ads": {},
            "users": {},
        }

        ads_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .annotate(ads_count=Count("adsmanager__ads"))
            .filter(ads_count__gt=0)
        )

        # All ADSManagerAdministrator, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .annotate(
                ads_count=Count(
                    "adsmanager__ads",
                    filter=~Q(adsmanager__ads__owner_email="")
                    | ~Q(adsmanager__ads__owner_mobile="")
                    | ~Q(adsmanager__ads__owner_phone=""),
                )
            )
            .filter(ads_count__gt=0)
        )

        ads_query_3_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 3))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        ads_query_6_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 6))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        ads_query_12_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__ads__creation_date__lte=now - timedelta(weeks=4 * 12))
            .annotate(ads_count=Count("adsmanager__ads"))
        )

        for label, query in (
            ("now", ads_query_now),
            ("with_info_now", ads_with_info_query_now),
            ("3_months", ads_query_3_months),
            ("6_months", ads_query_6_months),
            ("12_months", ads_query_12_months),
        ):
            for row in query:
                stats[row.prefecture.id]["obj"] = row
                stats[row.prefecture.id]["ads"][label] = row.ads_count

            stats_total["ads"][label] = query.aggregate(
                total=Coalesce(Sum("ads_count"), 0)
            )["total"]

        users_query_now = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(adsmanager__adsmanagerrequest__accepted=True)
            .annotate(users_count=Count("id"))
        )

        users_query_3_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 3),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_6_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 6),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_12_months = (
            ADSManagerAdministrator.objects.select_related("prefecture")
            .filter(
                adsmanager__adsmanagerrequest__accepted=True,
                adsmanager__adsmanagerrequest__created_at__lte=now
                - timedelta(weeks=4 * 12),
            )
            .annotate(users_count=Count("id"))
        )

        for label, query in (
            ("now", users_query_now),
            ("3_months", users_query_3_months),
            ("6_months", users_query_6_months),
            ("12_months", users_query_12_months),
        ):
            for row in query.all():
                stats[row.prefecture.id]["obj"] = row
                stats[row.prefecture.id]["users"][label] = row.users_count

            stats_total["users"][label] = query.aggregate(
                total=Coalesce(Sum("users_count"), 0)
            )["total"]

        return (
            # Transform dict to an ordered list
            sorted(list(stats.values()), key=lambda stat: stat["obj"].id),
            stats_total,
        )


class DashboardsDetailView(DetailView):
    template_name = "pages/ads_register/dashboards_detail.html"
    model = ADSManagerAdministrator
    pk_url_kwarg = "ads_manager_administrator_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stats"] = self.get_stats()
        return ctx

    def get_stats(self):
        stats = {}

        stats = collections.defaultdict(lambda: {"obj": None, "ads": {}, "users": {}})

        now = timezone.now()

        ads_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object)
            .annotate(ads_count=Count("ads"))
            .filter(ads_count__gt=0)
        )

        # All ADSManager, with the count of ADS with at least one of the contact fields filled.
        ads_with_info_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object)
            .annotate(
                ads_count=Count(
                    "ads",
                    filter=~Q(ads__owner_email="")
                    | ~Q(ads__owner_mobile="")
                    | ~Q(ads__owner_phone=""),
                )
            )
            .filter(ads_count__gt=0)
        )

        ads_query_3_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 3),
            )
            .annotate(ads_count=Count("ads"))
        )

        ads_query_6_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 6),
            )
            .annotate(ads_count=Count("ads"))
        )

        ads_query_12_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                ads__creation_date__lte=now - timedelta(weeks=4 * 12),
            )
            .annotate(ads_count=Count("ads"))
        )

        for label, query in (
            ("now", ads_query_now),
            ("with_info_now", ads_with_info_query_now),
            ("3_months", ads_query_3_months),
            ("6_months", ads_query_6_months),
            ("12_months", ads_query_12_months),
        ):
            for row in query:
                stats[row.id]["obj"] = row
                stats[row.id]["ads"][label] = row.ads_count

        users_query_now = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(administrator=self.object, adsmanagerrequest__accepted=True)
            .annotate(users_count=Count("id"))
        )

        users_query_3_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 3),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_6_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 6),
            )
            .annotate(users_count=Count("id"))
        )

        users_query_12_months = (
            ADSManager.objects.prefetch_related("content_type", "content_object")
            .filter(
                administrator=self.object,
                adsmanagerrequest__accepted=True,
                adsmanagerrequest__created_at__lte=now - timedelta(weeks=4 * 12),
            )
            .annotate(users_count=Count("id"))
        )

        for label, query in (
            ("now", users_query_now),
            ("3_months", users_query_3_months),
            ("6_months", users_query_6_months),
            ("12_months", users_query_12_months),
        ):
            for row in query.all():
                stats[row.id]["obj"] = row
                stats[row.id]["users"][label] = row.users_count

        return sorted(list(stats.values()), key=lambda stat: stat["obj"].id)
