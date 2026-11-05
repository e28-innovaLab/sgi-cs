from django.db.models.deletion import ProtectedError
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.exceptions import ConflictoDeRelacion
from usuarios.permissions import PermisoCatalogo
from .models import Aula, Categoria, Equipamiento
from .serializers import (
    AulaSerializer, CategoriaSerializer, EquipamientoSerializer,
    EstadoAulaSerializer, EstadoEquipamientoSerializer,
    FiltrosAulaSerializer, FiltrosEquipamientoSerializer,
)


class CatalogoViewSet(viewsets.ModelViewSet):
    permission_classes = [PermisoCatalogo]
    search_fields = ['nombre']

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError as exc:
            raise ConflictoDeRelacion('El registro está asociado a otros datos y no puede eliminarse.') from exc


class EstadoMixin:
    @action(detail=True, methods=['patch'], url_path='estado')
    def actualizar_estado(self, request, pk=None):
        if set(request.data) - {'estado'}:
            raise serializers.ValidationError({'detail': 'Este endpoint solo permite modificar estado.'})
        instance = self.get_object()
        serializer = self.estado_serializer_class(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.get_serializer(instance).data)


class AulaViewSet(EstadoMixin, CatalogoViewSet):
    queryset = Aula.objects.order_by('nombre', 'id_aula')
    serializer_class = AulaSerializer
    estado_serializer_class = EstadoAulaSerializer

    def get_queryset(self):
        filtros = FiltrosAulaSerializer(data=self.request.query_params.dict())
        filtros.is_valid(raise_exception=True)
        datos = filtros.validated_data.copy()
        if 'capacidad_min' in datos:
            datos['capacidad__gte'] = datos.pop('capacidad_min')
        return super().get_queryset().filter(**datos)

    def perform_destroy(self, instance):
        if instance.equipamientos.exists():
            raise ConflictoDeRelacion('Reasigná el equipamiento del aula antes de eliminarla.')
        super().perform_destroy(instance)

    @action(detail=True, methods=['get'])
    def equipamientos(self, request, pk=None):
        equipos = self.get_object().equipamientos.select_related('aula', 'categoria').order_by('nombre', 'id_equipo')
        pagina = self.paginate_queryset(equipos)
        serializer = EquipamientoSerializer(pagina, many=True)
        return self.get_paginated_response(serializer.data)


class CategoriaViewSet(CatalogoViewSet):
    queryset = Categoria.objects.order_by('nombre', 'id_categoria')
    serializer_class = CategoriaSerializer


class EquipamientoViewSet(EstadoMixin, CatalogoViewSet):
    queryset = Equipamiento.objects.select_related('aula', 'categoria').order_by('nombre', 'id_equipo')
    serializer_class = EquipamientoSerializer
    estado_serializer_class = EstadoEquipamientoSerializer

    def get_queryset(self):
        # Un filtro omitido no debe convertirse en el checkbox HTML False.
        filtros = FiltrosEquipamientoSerializer(data=self.request.query_params.dict())
        filtros.is_valid(raise_exception=True)
        return super().get_queryset().filter(**filtros.validated_data)
