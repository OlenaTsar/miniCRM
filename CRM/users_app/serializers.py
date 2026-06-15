from rest_framework import serializers

from auth_app.models import User, Team


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_active',
            'is_verified',
            'created_at',
            'team',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'is_verified',
        ]


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'team',
        ]
        read_only_fields = [
            'id',
            'email',
            'role',
            'team',
        ]


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
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
