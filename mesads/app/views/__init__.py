from .ads import (  # noqa: F401
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
    ADSManagerAdminRequestsView,
    ADSManagerAdminUpdatesView,
    ADSManagerAdministratorView,
    RepertoireVehiculeRelaisView,
    VehiculeView,
)
from .ads_manager_request import (  # noqa: F401
    DemandeGestionADSView,
)

from .arretes import ListeArretesFilesView, TelechargementArreteView  # noqa: F401

from .dashboards import DashboardsView  # noqa: F401
from .public import (  # noqa: F401
    FAQView,
    StatsView,
    ReglementationView,
    HTTP500View,
    HomepageView,
    PlanSiteView,
)

from .liste_attente import (  # noqa: F401
    ListeAttenteView,
    CreationInscriptionListeAttenteView,
    ModificationInscriptionListeAttenteView,
    ExportCSVInscriptionListeAttenteView,
    ArchivageInscriptionListeAttenteView,
    ArchivageConfirmationView,
    DemandeArchiveesView,
    AttributionListeAttenteView,
    InscriptionTraitementListeAttenteView,
    ModeleCourrierArchivageView,
    ModeleCourrierContactView,
)
