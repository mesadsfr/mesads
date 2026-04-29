import re

from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles import finders
from django.db.models import Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import DetailView, ListView, View
from weasyprint import CSS, HTML

from mesads.app.forms import ConsultationADSForm
from mesads.app.models import ADS
from mesads.fradm.models import EPCI, Aeroport, Commune, Prefecture


class ConsultationADSSearchView(ListView):
    template_name = "pages/ads_register/consultation_ads/consultation_ads_search.html"
    context_object_name = "results"
    paginate_by = 50

    def get_initial(self):
        departement = None
        if self.request.GET.get("departement"):
            departement = self.request.GET.get("departement")
        elif self.request.user.prefecture_consultation:
            departement = self.request.user.prefecture_consultation.id
        return {
            "departement": departement,
            "commune": self.request.GET.get("commune", ""),
            "immatriculation": self.request.GET.get("immatriculation", ""),
            "conducteur": self.request.GET.get("conducteur", ""),
            "siret": self.request.GET.get("siret", ""),
            "numero": self.request.GET.get("numero", ""),
        }

    def get_queryset(self):
        if not self.request.GET:
            return []

        qs = ADS.objects.all()
        departement = self.request.GET.get("departement")
        commune = self.request.GET.get("commune")
        immatriculation = self.request.GET.get("immatriculation")
        conducteur = self.request.GET.get("conducteur")
        siret = self.request.GET.get("siret")
        numero = self.request.GET.get("numero")

        if departement:
            qs = qs.filter(ads_manager__administrator__prefecture__id=departement)
        if commune:
            content_type_commune = ContentType.objects.get_for_model(Commune)
            content_type_prefecture = ContentType.objects.get_for_model(Prefecture)
            content_type_epci = ContentType.objects.get_for_model(EPCI)
            content_type_aeroport = ContentType.objects.get_for_model(Aeroport)

            communes_ids = Commune.objects.filter(libelle__icontains=commune).values(
                "pk"
            )
            prefectures_ids = Prefecture.objects.filter(
                libelle__icontains=commune
            ).values("pk")
            epcis_ids = EPCI.objects.filter(name__icontains=commune).values("pk")
            aeroport_ids = Aeroport.objects.filter(name__icontains=commune).values("pk")

            qs = qs.filter(
                Q(
                    ads_manager__content_type=content_type_commune,
                    ads_manager__object_id__in=Subquery(communes_ids),
                )
                | Q(
                    ads_manager__content_type=content_type_prefecture,
                    ads_manager__object_id__in=Subquery(prefectures_ids),
                )
                | Q(
                    ads_manager__content_type=content_type_epci,
                    ads_manager__object_id__in=Subquery(epcis_ids),
                )
                | Q(
                    ads_manager__content_type=content_type_aeroport,
                    ads_manager__object_id__in=Subquery(aeroport_ids),
                )
                | Q(epci_commune__libelle__icontains=commune)
            )
        if immatriculation:
            qs = qs.filter(immatriculation_plate=immatriculation)
        if conducteur:
            terms = re.findall(r"\w+", conducteur.strip())
            for term in terms:
                qs = qs.filter(
                    Q(owner_name__icontains=term) | Q(adsuser__name__icontains=term)
                )
        if siret:
            qs = qs.filter(owner_siret=siret)
        if numero:
            qs = qs.filter(number=numero)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ConsultationADSForm(self.get_initial())
        return context


class ConsultationADSView(DetailView):
    template_name = "pages/ads_register/consultation_ads/consultation_ads.html"
    model = ADS
    pk_url_kwarg = "ads_id"


class ExportADSPDFView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        ads = get_object_or_404(ADS, id=kwargs["ads_id"])

        context = {"ads": ads}

        html_string = render_to_string(
            "pages/ads_register/consultation_ads/consultation_ads_export.html", context
        )
        filename = f"ads-{ads.number}.pdf"
        response = HttpResponse(
            content_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

        stylesheets = []
        dsfr_css_path = finders.find("@gouvfr/dsfr/dsfr.min.css")
        pdf_css_path = finders.find("css/pdf.css")
        if dsfr_css_path:
            stylesheets.append(CSS(filename=dsfr_css_path))

        if pdf_css_path:
            stylesheets.append(CSS(filename=pdf_css_path))

        HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(
            target=response,
            stylesheets=stylesheets,
            pdf_variant="pdf/ua-1",
            metadata={
                "title": f"ADS {ads.number} - {ads.ads_manager.human_name}",
                "author": "MesADS",
                "language": "fr",
            },
        )

        return response
