from django.urls import path

from . import views


urlpatterns = [
    path('commune/autocomplete',
         views.CommuneAutocompleteView.as_view(),
         name='commune-autocomplete'),

    path('epci/autocomplete',
         views.EPCIAutocompleteView.as_view(),
         name='epci-autocomplete'),

    path('prefecture/autocomplete',
         views.PrefectureAutocompleteView.as_view(),
         name='prefecture-autocomplete'),
]
