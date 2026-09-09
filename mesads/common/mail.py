from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def envoi_email(
    content_template_txt: str,
    content_template_mjml: str,
    context,
    destinataires,
    sujet: str = None,
    sujet_template: str = None,
    from_email: str = settings.MESADS_CONTACT_EMAIL,
):
    email_subject = None
    if sujet:
        email_subject = sujet
    elif sujet_template:
        email_subject = render_to_string(
            sujet_template,
            context,
        ).strip()
    else:
        raise ValueError(
            "La fonction doit prendre un paramètre 'sujet' ou 'sujet_template'."
        )

    email_content = render_to_string(
        content_template_txt,
        context,
    )
    email_content_html = render_to_string(
        content_template_mjml,
        context,
    )
    send_mail(
        email_subject,
        email_content,
        from_email,
        destinataires,
        fail_silently=True,
        html_message=email_content_html,
    )
