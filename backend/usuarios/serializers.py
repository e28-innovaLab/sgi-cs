from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import Rol, Usuario


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id_rol', 'nombre']


class PerfilSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'username', 'first_name', 'last_name', 'email', 'rol']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        usuario = authenticate(request=self.context['request'], **attrs)
        if usuario is None:
            raise serializers.ValidationError('Usuario o contraseña incorrectos.')
        if not usuario.is_superuser and usuario.rol.nombre not in (Rol.ADMIN, Rol.COORDINACION):
            raise serializers.ValidationError('El usuario no tiene un rol habilitado.')
        return {'usuario': usuario}


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    is_active = serializers.BooleanField(required=False, default=True)
    rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.filter(nombre__in=[Rol.ADMIN, Rol.COORDINACION]),
    )

    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'username', 'first_name', 'last_name', 'email',
            'tipo_documento', 'numero_documento', 'rol', 'is_active', 'password',
        ]
        read_only_fields = ['id_usuario']
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
            'email': {'required': True, 'allow_blank': False},
        }

    def validate(self, attrs):
        if self.instance is None and 'password' not in attrs:
            raise serializers.ValidationError({'password': 'Este campo es obligatorio.'})
        if self.instance and self.instance.pk == self.context['request'].user.pk:
            if attrs.get('is_active') is False:
                raise serializers.ValidationError({'is_active': 'No podés desactivar tu propio usuario.'})
            if 'rol' in attrs and attrs['rol'].nombre != Rol.ADMIN:
                raise serializers.ValidationError({'rol': 'No podés quitarte tu rol de administrador.'})
        if 'password' in attrs:
            datos = {
                campo: attrs.get(campo, getattr(self.instance, campo, ''))
                for campo in ['username', 'first_name', 'last_name', 'email']
            }
            try:
                password_validation.validate_password(attrs['password'], Usuario(**datos))
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': exc.messages}) from exc
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        return Usuario.objects.create_user(password=password, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password is not None:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        if password is not None or not instance.is_active:
            Token.objects.filter(user=instance).delete()
        return instance
