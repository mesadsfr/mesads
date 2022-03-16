from django.core.exceptions import SuspiciousOperation
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, TemplateView
from django.views.generic import UpdateView
from django.views.generic.edit import CreateView, DeleteView, FormView
from django.views.generic.list import ListView

from .forms import ADSManagerForm
from .models import ADS, ADSManager, ADSManagerAdministrator, ADSManagerRequest


class HTTP500View(TemplateView):
    """The default HTTP/500 handler can't access to context processors and does
    not have access to the variable MESADS_CONTACT_EMAIL.
    """
    template_name = '500.html'


class HomepageView(RedirectView):
    """Redirect to ADSManagerAdminView or ADSManagerView depending on the
    user role. If user is not authenticated or has no roles, redirect to
    HowItWorksView.
    """
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated and len(self.request.user.adsmanageradministrator_set.all()):
            return reverse('ads-manager-admin')
        return reverse('ads-manager-request')


class HowItWorksView(TemplateView):
    template_name = 'pages/how-it-works.html'


class ADSManagerAdminView(TemplateView):
    template_name = 'pages/ads_manager_admin.html'

    def get_context_data(self, **kwargs):
        raise ValueError
        ctx = super().get_context_data(**kwargs)

        ctx['ads_manager_requests'] = {}

        # Get all ADSManagerAdministrator objects related to the current user
        ads_manager_admins = ADSManagerAdministrator.objects.filter(users__in=[self.request.user])

        # For each admin, get the list of requests
        for ads_manager_admin in ads_manager_admins:
            ads_manager_requests = ADSManagerRequest.objects.filter(
                ads_manager__in=[obj.id for obj in ads_manager_admin.ads_managers.all()]
            ).order_by('-id')
            ctx['ads_manager_requests'][ads_manager_admin] = ads_manager_requests
        return ctx

    def post(self, request):
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')

        if action not in ('accept', 'deny'):
            raise SuspiciousOperation('Invalid action')

        ads_manager_request = get_object_or_404(
            ADSManagerRequest,
            id=request_id
        )

        # Make sure current user can accept this request
        get_object_or_404(
            ADSManagerAdministrator,
            users__in=[request.user],
            ads_managers__in=[ads_manager_request.ads_manager]
        )

        if action == 'accept':
            ads_manager_request.accepted = True
        else:
            ads_manager_request.accepted = False
        ads_manager_request.save()

        return redirect(reverse('ads-manager-admin'))


class ADSManagerRequestView(FormView):
    template_name = 'pages/ads_manager_request.html'
    form_class = ADSManagerForm
    success_url = reverse_lazy('ads-manager-request')

    def get_context_data(self, **kwargs):
        """Expose the list of ADSManagerAdministrators for which current user
        is configured.

        It is also accessible through user.adsmanageradministrator_set.all, but
        we need to prefetch ads_managers__content_object to reduce the number
        of SQL queries generated.
        """
        ctx = super().get_context_data(**kwargs)
        ctx['ads_managers_administrators'] = ADSManagerAdministrator.objects.filter(
            users__in=[self.request.user]
        ).prefetch_related('ads_managers__content_object')
        return ctx

    def form_valid(self, form):
        ADSManagerRequest.objects.get_or_create(
            user=self.request.user,
            ads_manager=form.cleaned_data['ads_manager'],
        )
        return super().form_valid(form)


class ADSManagerView(ListView):
    template_name = 'pages/ads_manager.html'
    model = ADS
    paginate_by = 20
    ordering = ['id']

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(ads_manager__id=self.kwargs['manager_id'])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])
        return ctx


class ADSView(UpdateView):
    template_name = 'pages/ads.html'
    model = ADS
    fields = (
        'number',
        'ads_creation_date',
        'ads_type',
        'attribution_date',
        'attribution_type',
        'attribution_reason',
        'accepted_cpam',
        'immatriculation_plate',
        'vehicle_compatible_pmr',
        'eco_vehicle',
        'owner_firstname',
        'owner_lastname',
        'owner_siret',
        'used_by_owner',
        'user_status',
        'user_name',
        'user_siret',
        'legal_file',
    )

    def get_success_url(self):
        return reverse('ads', kwargs={
            'manager_id': self.kwargs['manager_id'],
            'ads_id': self.kwargs['ads_id'],
        })

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ads_manager'] = ADSManager.objects.get(id=self.kwargs['manager_id'])
        return ctx

    def get_object(self, queryset=None):
        return get_object_or_404(ADS, id=self.kwargs['ads_id'])


class ADSDeleteView(DeleteView, ADSView):
    template_name = 'pages/ads_confirm_delete.html'
    model = ADS

    def get_success_url(self):
        return reverse('ads-manager', kwargs={
            'manager_id': self.kwargs['manager_id'],
        })


class ADSCreateView(ADSView, CreateView):
    def get_object(self, queryset=None):
        return None

    def get_success_url(self):
        return reverse('ads', kwargs={
            'manager_id': self.kwargs['manager_id'],
            'ads_id': self.object.id,
        })

    def form_valid(self, form):
        ads_manager = ADSManager.objects.get(id=self.kwargs['manager_id'])
        form.instance.ads_manager = ads_manager
        return super().form_valid(form)
