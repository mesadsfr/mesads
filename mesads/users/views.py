from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView

from .forms import SignUpUserForm


class SignUpView(CreateView):
    template_name = 'registration/signup.html'
    form_class = SignUpUserForm
    success_url = reverse_lazy('signup_done')


class SignUpDoneView(TemplateView):
    template_name = 'registration/signup_done.html'
