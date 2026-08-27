from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.PATIENT)

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "password", "role", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_role(self, value):
        # Admin accounts must never be self-registered via the public API.
        if value == User.Role.ADMIN:
            raise serializers.ValidationError(
                "Admin/pharmacist accounts cannot be self-registered. Contact a system administrator."
            )
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.", code="authorization")
        if not user.is_active:
            raise serializers.ValidationError("This account has been disabled.", code="authorization")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phone", "role", "created_at"]
        read_only_fields = fields
