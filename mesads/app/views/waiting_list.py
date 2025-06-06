from django.contrib import messages
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from reversion.views import RevisionMixin

from ..models import ADSManager, WaitingList, WAITING_LIST_UNIQUE_ERROR_MESSAGE
from ..forms import WaitingListForm, WaitingListEditForm
from ..reversion_diff import ModelHistory


class WaitingListView(ListView):
    template_name = "pages/ads_register/waiting_list.html"
    model = WaitingList
    paginate_by = 50
    ordering = "initial_request_date"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return ctx


class WaitingListDetailsView(RevisionMixin, UpdateView):
    template_name = "pages/ads_register/waiting_list_details.html"
    form_class = WaitingListEditForm

    def get_success_url(self):
        return reverse(
            "app.waiting-list.list",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["ads_manager"] = ADSManager.objects.get(id=self.kwargs["manager_id"])
        return ctx

    def get_object(self, queryset=None):
        waiting_list = get_object_or_404(WaitingList, id=self.kwargs["waiting_list_id"])
        return waiting_list

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Le formulaire contient des erreurs. Veuillez les corriger avant de soumettre à nouveau.",
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        self.object = form.save()
        # XXX: add WaitingListUpdateLog
        messages.success(self.request, "Les modifications ont été enregistrées.")
        return HttpResponseRedirect(self.get_success_url())


class WaitingListCreateView(WaitingListDetailsView, CreateView):
    form_class = WaitingListForm

    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        return reverse(
            "app.waiting-list.list",
            kwargs={
                "manager_id": self.kwargs["manager_id"],
            },
        )

    def form_valid(self, form):
        ads_manager = ADSManager.objects.get(id=self.kwargs["manager_id"])
        form.instance.ads_manager = ads_manager

        # CreateView doesn't call validate_constraints(). The try/catch below
        # attemps to save the object. If IntegrityError is returned from
        # database, we return a custom error message for "number".
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("number", WAITING_LIST_UNIQUE_ERROR_MESSAGE)
            return super().form_invalid(form)


class WaitingListHistoryView(DetailView):
    template_name = "pages/ads_register/waiting_list_history.html"
    model = WaitingList
    pk_url_kwarg = "waiting_list_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["history"] = ModelHistory(
            self.object,
            ignore_fields=[
                WaitingList._meta.get_field("ads_manager"),
            ],
        )
        return ctx


class WaitingListAttributionView(DetailView):
    template_name = "pages/ads_register/waiting_list_attribution.html"
    model = WaitingList
    pk_url_kwarg = "waiting_list_id"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx
