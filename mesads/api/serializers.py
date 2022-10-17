from django.contrib.auth import get_user_model

from rest_framework import serializers

from mesads.app.models import ADSUpdateFile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'email',
        )


class ADSUpdateFileSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)
    update_file = serializers.FileField(allow_empty_file=False)

    class Meta:
        model = ADSUpdateFile
        fields = (
            'id',
            'creation_date',
            'user',
            'update_file',
        )
