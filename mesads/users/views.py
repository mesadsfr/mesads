from django.conf import settings
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django_registration.backends.activation.views import RegistrationView

import pyotp

from .forms import CustomUserForm, OTPAuthenticationForm


class CustomRegistrationView(RegistrationView):
    form_class = CustomUserForm
    html_email_body_template = "django_registration/activation_email_body.mjml"

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
            subject, message, settings.DEFAULT_FROM_EMAIL, html_message=html_message
        )


class OTPLoginView(LoginView):
    authentication_form = OTPAuthenticationForm

    # By default, LoginView displays the login form to authenticated users,
    # and also a permission error message if ?next is set. Override to force
    # redirect to ?next or to LOGIN_REDIRECT_URL.
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Log the user in only if OTP (if required) is provided."""
        user = form.get_user()

        if user.otp_secret:
            totp = pyotp.TOTP(user.otp_secret, interval=60 * 10)  # 10 minutes

            otp = form.cleaned_data.get("otp")
            # For the first request, otp is empty, so we send the OTP by email.
            # If necessary in the future, we can add a field in User
            # "last_otp_sent" to limit the number of OTP sent.
            if not otp:
                otp_code = totp.now()
                email_subject = render_to_string(
                    "pages/email_send_otp_subject.txt",
                    {
                        "otp_code": otp_code,
                    },
                    request=self.request,
                ).strip()
                email_content = render_to_string(
                    "pages/email_send_otp_content.txt",
                    {
                        "otp_code": otp_code,
                    },
                    request=self.request,
                )
                email_content_html = render_to_string(
                    "pages/email_send_otp_content.mjml",
                    {
                        "otp_code": otp_code,
                    },
                    request=self.request,
                )
                send_mail(
                    email_subject,
                    email_content,
                    settings.MESADS_CONTACT_EMAIL,
                    [user.email],
                    fail_silently=True,
                    html_message=email_content_html,
                )
                return self.form_invalid(form)
            elif not totp.verify(otp):
                form.add_error(
                    "otp", "Le code est invalide. Vérifiez votre boîte mail."
                )
                return self.form_invalid(form)

        # If no OTP is required, proceed to log in immediately.
        auth_login(self.request, user)

        remember = form.cleaned_data.get("remember_me")
        if remember:
            self.request.session.set_expiry(43200)
            self.request.session.modified = True

        return HttpResponseRedirect(self.get_success_url())
