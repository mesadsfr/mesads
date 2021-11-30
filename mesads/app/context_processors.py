from django.conf import settings


def mesads_settings(request):
    """Expose settings starting with MESADS_ to templates."""
    return {
        key: getattr(settings, key)
        for key in dir(settings) if key.startswith('MESADS_')
    }
