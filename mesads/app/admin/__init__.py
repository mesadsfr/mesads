from django.contrib.auth.models import Group
from django.contrib import admin

from .ads import *
from .ads_manager import *
from .ads_manager_administrator import *
from .ads_manager_request import *
from .ads_update_file import *

# Remove "Group" administration from admin. We do not use groups in the
# application.
admin.site.unregister(Group)
