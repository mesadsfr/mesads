from django.contrib import admin

from ..models import EntreeRegistreTransaction


@admin.register(EntreeRegistreTransaction)
class EntreeRegistreTransactionAdmin(admin.ModelAdmin):
    @admin.display(description="ADS")
    def ads_entree(self, entree):
        return f"ADS #{entree.ads.number} - {entree.ads.ads_manager.human_name()}"

    list_display = (
        "ads_entree",
        "ancien_exploitant",
        "nouvel_exploitant",
        "statut",
    )
