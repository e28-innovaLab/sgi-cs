from django.contrib.auth.models import update_last_login
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Rol, Usuario
from .permissions import SoloAdministrador
from .serializers import LoginSerializer, PerfilSerializer, RolSerializer, UsuarioSerializer


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        usuario = serializer.validated_data['usuario']
        token, _ = Token.objects.get_or_create(user=usuario)
        update_last_login(None, usuario)
        return Response({'token': token.key, 'usuario': PerfilSerializer(usuario).data})


class LogoutView(APIView):
    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PerfilView(APIView):
    def get(self, request):
        return Response(PerfilSerializer(request.user).data)


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.filter(nombre__in=[Rol.ADMIN, Rol.COORDINACION]).order_by('id_rol')
    serializer_class = RolSerializer


class UsuarioViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Usuario.objects.select_related('rol').order_by('id_usuario')
    serializer_class = UsuarioSerializer
    permission_classes = [SoloAdministrador]
    search_fields = ['username', 'first_name', 'last_name', 'email', 'numero_documento']
