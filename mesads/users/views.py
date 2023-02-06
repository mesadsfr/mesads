from django_registration.backends.activation.views import RegistrationView
from django.conf import settings
from django.template.loader import render_to_string

from .forms import CustomUserForm


class CustomRegistrationView(RegistrationView):
    form_class = CustomUserForm
    html_email_body_template = 'django_registration/activation_email_body.mjml'

    def send_activation_email(self, user):
        """django-registration can only send plain/text activation email. To
        send HTML email, this method is a copy/paste of the parent method
        except we render html_email_body_template and give it as paremeter to
        user.email_user.
        """
        activation_key = self.get_activation_key(user)
        context = self.get_email_context(activation_key)
        context["user"] = user
        subject = render_to_string(
            template_name=self.email_subject_template,
            context=context,
            request=self.request,
        )
        # Force subject to a single line to avoid header-injection
        # issues.
        subject = "".join(subject.splitlines())
        message = render_to_string(
            template_name=self.email_body_template,
            context=context,
            request=self.request,
        )
        html_message = render_to_string(
            template_name=self.html_email_body_template,
            context=context,
            request=self.request,
        )
        user.email_user(
            subject, message, settings.DEFAULT_FROM_EMAIL,
            html_message=html_message
        )
