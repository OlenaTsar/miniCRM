from rest_framework import serializers

from auth_app.models import User, Team, UserRole


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'avatar',
            'role',
            'is_active',
            'is_verified',
            'created_at',
            'team',
        ]
        read_only_fields = [
            'id',
            'email',
            'created_at',
            'is_verified',
            'team',
        ]

    def validate(self, attrs):
        # забороняє manager змінювати role

        user = self.context["request"].user

        if user.role == UserRole.MANAGER and "role" in attrs:
            raise serializers.ValidationError(
                {"role": "You cannot change role."}
            )

        return attrs


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'avatar',
            'role',
            'team',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'email',
            'role',
            'team',
            'created_at',
        ]


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'avatar',
        ]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = [
            'id',
            'name',
            'users',
            'products',
        ]
        read_only_fields = [
            'id',
            'users',
            'products',
        ]
