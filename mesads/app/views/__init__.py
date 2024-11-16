from django.urls import reverse
from django.views.generic import RedirectView

from .ads import (  # noqa: F401
    ADSDecreeView,
    ADSHistoryView,
    ADSCreateView,
    ADSDeleteView,
    ADSView,
)
from .ads_manager import (  # noqa: F401
    ADSManagerView,
    ads_manager_decree_view,
    ADSManagerAutocompleteView,
)
from .ads_manager_admin import (  # noqa: F401
    PrefectureExportView,
    ADSManagerExportView,
    ADSManagerAdminIndexView,
    ADSManagerAdminDetailsView,
    ADSManagerAdminUpdatesView,
)
from .ads_manager_request import (  # noqa: F401
    ADSManagerRequestView,
)
from .dashboards import DashboardsView, DashboardsDetailView  # noqa: F401
from .public import (  # noqa: F401
    FAQView,
    StatsView,
    ReglementationView,
    HTTP500View,
    HomepageView,
)


class ADSRegisterView(RedirectView):
    """Redirect to the appropriate dashboard depending on the user's role."""

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_staff:
            return reverse("app.dashboards.list")
        ads_manager_administrators = self.request.user.adsmanageradministrator_set.all()
        if len(ads_manager_administrators):
            return reverse(
                "app.ads-manager-admin.index",
            )
        return reverse("app.ads-manager.index")
