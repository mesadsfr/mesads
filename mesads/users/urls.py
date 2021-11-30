from django.urls import path

from .views import SignUpView, SignUpDoneView


urlpatterns = [
    path('signup', SignUpView.as_view(), name='signup'),
    path('signup_done', SignUpDoneView.as_view(), name='signup_done'),
]
