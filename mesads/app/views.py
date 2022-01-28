from django.urls import reverse, reverse_lazy
from django.views.generic import RedirectView, TemplateView
from django.views.generic.edit import FormView

from mesads.fradm.forms import FrenchAdministrationForm


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
                return reverse('ads-manager')
        return reverse('how-it-works')


class HowItWorksView(TemplateView):
    template_name = 'pages/how-it-works.html'


class ADSManagerAdminView(TemplateView):
    template_name = 'pages/ads_manager_admin.html'


class ADSManagerView(FormView):
    template_name = 'pages/ads_manager.html'
    form_class = FrenchAdministrationForm
    success_url = reverse_lazy('ads-manager')

    def form_valid(self, form):
        return super().form_valid(form)
