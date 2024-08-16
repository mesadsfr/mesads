from datetime import timedelta

from django.test import RequestFactory
from django.utils import timezone

from ..models import (
    ADS,
    ADSManagerRequest,
)
from ..unittest import ClientTestCase
from ..views import DashboardsView, DashboardsDetailView


class TestDashboardsViews(ClientTestCase):
    """Test DashboardsView and DashboardsDetailView"""

    def setUp(self):
        super().setUp()
        request = RequestFactory().get("/dashboards")
        self.dashboards_view = DashboardsView()
        self.dashboards_view.setup(request)

        request = RequestFactory().get(
            f"/registre_ads/dashboards/{self.ads_manager_administrator_35.id}"
        )
        self.dashboards_detail_view = DashboardsDetailView(
            object=self.ads_manager_administrator_35
        )
        self.dashboards_detail_view.setup(request)

    def test_permissions(self):
        for client_name, client, expected_status in (
            ("anonymous", self.anonymous_client, 302),
            ("auth", self.auth_client, 302),
            ("ads_manager 35", self.ads_manager_city35_client, 302),
            ("ads_manager_admin 35", self.ads_manager_administrator_35_client, 302),
            ("admin", self.admin_client, 200),
        ):
            with self.subTest(client_name=client_name, expected_status=expected_status):
                resp = client.get("/registre_ads/dashboards")
                self.assertEqual(resp.status_code, expected_status)

                resp = client.get(
                    f"/registre_ads/dashboards/{self.ads_manager_administrator_35.id}/"
                )
                self.assertEqual(resp.status_code, expected_status)

    def test_stats_default(self):
        # The base class ClientTestCase creates ads_manager_administrator for
        # departement 35, and configures an ADSManager for the city fo Melesse.
        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {},
                "users": {
                    "now": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 0,
                "with_info_now": 0,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
            "users": {
                "now": 1,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
        }
        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {},
                    "users": {
                        "now": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )

    def test_stats_for_several_ads(self):
        # Create several ADS for the city of Melesse
        now = timezone.now()
        for idx, creation_date in enumerate(
            [
                now - timedelta(days=365 * 2),  # 2 years old ADS
                now - timedelta(days=300),  # > 6 && < 12 months old
                now - timedelta(days=120),  # > 3 && < 6 months old
                now - timedelta(days=1),  # yesterday
            ]
        ):
            ads = ADS.objects.create(
                number=str(idx), ads_manager=self.ads_manager_city35, ads_in_use=True
            )
            ads.creation_date = creation_date
            ads.save()

        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {
                    "now": 4,
                    "3_months": 3,
                    "6_months": 2,
                    "12_months": 1,
                },
                "users": {
                    "now": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 4,
                "with_info_now": 0,
                "3_months": 3,
                "6_months": 2,
                "12_months": 1,
            },
            "users": {
                "now": 1,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
        }

        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {
                        "now": 4,
                        "3_months": 3,
                        "6_months": 2,
                        "12_months": 1,
                    },
                    "users": {
                        "now": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )

    def test_stats_for_several_ads_managers(self):
        now = timezone.now()
        # Give administration permissions for several users to Melesse.
        for creation_date in [
            now - timedelta(days=365 * 2),  # 2 years old ADS
            now - timedelta(days=300),  # > 6 && < 12 months old
            now - timedelta(days=120),  # > 3 && < 6 months old
            now - timedelta(days=1),  # yesterday
        ]:
            user = self.create_user().obj
            ads_manager_request = ADSManagerRequest.objects.create(
                user=user,
                ads_manager=self.ads_manager_city35,
                accepted=True,
            )
            ads_manager_request.created_at = creation_date
            ads_manager_request.save()

        stats = [
            {
                "obj": self.ads_manager_administrator_35,
                "ads": {},
                "users": {
                    "now": 5,
                    "3_months": 3,
                    "6_months": 2,
                    "12_months": 1,
                },
            }
        ]
        stats_total = {
            "ads": {
                "now": 0,
                "with_info_now": 0,
                "3_months": 0,
                "6_months": 0,
                "12_months": 0,
            },
            "users": {
                "now": 5,
                "3_months": 3,
                "6_months": 2,
                "12_months": 1,
            },
        }

        self.assertEqual((stats, stats_total), self.dashboards_view.get_stats())

        self.assertEqual(
            [
                {
                    "obj": self.ads_manager_city35,
                    "ads": {},
                    "users": {
                        "now": 5,
                        "3_months": 3,
                        "6_months": 2,
                        "12_months": 1,
                    },
                }
            ],
            self.dashboards_detail_view.get_stats(),
        )
