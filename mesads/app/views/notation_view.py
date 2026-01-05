from django.http.response import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View

from mesads.users.models import NoteUtilisateur


class NotationView(View):
    """
    Vue dédié à gérer la notation, puis a rediriger vers la page d'accueil.
    Si l'utilisateur a cliquer pour close la modale:
    on enregistre la dernière date d'affichage
    Si l'utilisateur note,
    on enregistre la dernière date d'affichage, de notation, et les notes
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        redirect_url = reverse("app.homepage")

        user = self.request.user
        action = request.POST.get("action")
        if user.is_authenticated is False or action not in ["close", "note"]:
            return redirect(redirect_url)

        note_utilisateur, _ = NoteUtilisateur.objects.get_or_create(user=user)

        if action == "close":
            note_utilisateur.dernier_affichage = timezone.now().date()
            note_utilisateur.save()
            return JsonResponse(
                data={
                    "status": "ok",
                },
            )
        else:
            note_utilisateur.dernier_affichage = timezone.now().date()
            note_utilisateur.derniere_note = timezone.now().date()
            note_utilisateur.note_qualite = request.POST.get("note_qualite")
            note_utilisateur.note_facilite = request.POST.get("note_facilite")
            note_utilisateur.save()
            return JsonResponse(
                data={
                    "status": "ok",
                },
            )
        return redirect(redirect_url)
