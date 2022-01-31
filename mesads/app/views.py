from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, TemplateView
from django.views.generic.edit import FormView

from .forms import ADSManagerForm
from .models import ADSManagerRequest


class HomepageView(RedirectView):
    """Redirect to ADSManagerAdminView or ADSManagerView depending on the
    user role. If user is not authenticated or has no roles, redirect to
    HowItWorksView.
    """
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            if len(self.request.user.adsmanageradministrator_set.all()):
                return reverse('ads-manager-admin')
            if len(self.request.user.adsmanager_set.all()):
                return reverse('ads-manager-request')
        return reverse('how-it-works')


class HowItWorksView(TemplateView):
    template_name = 'pages/how-it-works.html'


class ADSManagerAdminView(TemplateView):
    template_name = 'pages/ads_manager_admin.html'


class ADSManagerRequestView(FormView):
    template_name = 'pages/ads_manager_request.html'
    form_class = ADSManagerForm
    success_url = reverse_lazy('ads-manager-request')

    def form_valid(self, form):
        ADSManagerRequest.objects.get_or_create(
            user=self.request.user,
            ads_manager=form.cleaned_data['ads_manager'],
        )
        return super().form_valid(form)
