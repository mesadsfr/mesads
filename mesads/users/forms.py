from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpUserForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email',)

    def save(self):
        user = super().save(commit=False)
        user.is_active = False
        user.save()
        return user
