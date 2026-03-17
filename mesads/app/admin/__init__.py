from django.contrib import admin
from django.contrib.auth.models import Group

from .ads import *  # noqa
from .ads_manager import *  # noqa
from .ads_manager_administrator import *  # noqa
from .ads_manager_request import *  # noqa
from .ads_update_file import *  # noqa
from .demande_gestion_prefecture import *  # noqa
from .inscription_liste_attente import *  # noqa
from .notifications import *  # noqa

# Remove "Group" administration from admin. We do not use groups in the
# application.
admin.site.unregister(Group)
