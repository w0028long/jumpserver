from django.db.transaction import atomic
from rest_framework.decorators import action
from rest_framework.response import Response

from common.const.http import POST
from common.drf.api import JmsModelViewSet
from common.permissions import IsValidUser
from common.utils.django import get_object_or_none
from perms.models.asset_permission import AssetPermission, Asset
from assets.models.user import SystemUser
from ..exceptions import AssetsIpsNotMatch, SystemUserNotFound, TicketClosed, TicketActionYet
from .. import serializers
from ..models import Ticket
from ..permissions import IsAssignee


class ApplyForPermViewSet(JmsModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = serializers.ApplyForPermSerializer
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title', 'action', 'user_display']
    search_fields = ['user_display', 'title']

    def _check_can_set_action(self, instance, action):
        if instance.status == instance.STATUS_CLOSED:
            raise TicketClosed()
        if instance.action == action:
            raise TicketActionYet()

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION_REJECT
        self._check_can_set_action(instance, action)
        instance.perform_action(action, request.user)
        return Response()

    @action(detail=True, methods=[POST], permission_classes=[IsAssignee, IsValidUser])
    def approve(self, request, *args, **kwargs):
        instance = self.get_object()
        action = instance.ACTION_APPROVE
        self._check_can_set_action(instance, action)

        meta = instance.meta
        assets = list(Asset.objects.filter(ip__in=meta['ips']))
        if len(assets) != len(meta['ips']):
            raise AssetsIpsNotMatch()

        system_user = get_object_or_none(SystemUser, username=meta['system_user'])
        if system_user is None:
            raise SystemUserNotFound()

        ap_kwargs = {
            'name': meta.get('name'),
            'created_by': self.request.user.username
        }
        date_start = meta.get('date_start')
        date_expired = meta.get('date_expired')
        if date_start:
            ap_kwargs['date_start'] = date_start
        if date_expired:
            ap_kwargs['date_expired'] = date_expired

        with atomic():
            instance.perform_action(instance.ACTION_APPROVE, request.user)
            ap = AssetPermission.objects.create(**ap_kwargs)
            ap.system_users.add(system_user)
            ap.assets.add(*assets)

        return Response()
