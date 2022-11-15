from django.urls import path

from . import views


urlpatterns = [
    path('commune/autocomplete',
         views.CommuneAutocompleteView.as_view(),
         name='fradm.autocomplete.commune'),

    path('commune/<str:departement>/autocomplete',
         views.CommuneAutocompleteView.as_view(),
         name='fradm.autocomplete.commune'),

    path('epci/autocomplete',
         views.EPCIAutocompleteView.as_view(),
         name='fradm.autocomplete.epci'),

    path('prefecture/autocomplete',
         views.PrefectureAutocompleteView.as_view(),
         name='fradm.autocomplete.prefecture'),
]
