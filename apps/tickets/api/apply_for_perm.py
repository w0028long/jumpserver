from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.db.transaction import atomic

from common.permissions import IsValidUser
from common.utils.django import get_object_or_none
from perms.models.asset_permission import AssetPermission, Asset
from assets.models.user import SystemUser
from ..exceptions import AssetsIpsNotMatch, SystemUserNotFound
from .. import serializers
from ..models import Ticket


class TicketBaseViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    permission_classes = (IsValidUser,)
    filter_fields = ['status', 'title', 'action', 'user_display']
    search_fields = ['user_display', 'title']


class ApplyForPermViewSet(TicketBaseViewSet):
    serializer_class = serializers.ApplyForPermSerializer

    @atomic()
    def perform_update(self, serializer):
        old_action = serializer.instance.action
        serializer.save()
        new_action = serializer.instance.action

        if old_action == '' and new_action == Ticket.ACTION_APPROVE:
            meta = serializer.instance.meta
            assets = list(Asset.objects.filter(ip__in=meta['ips']))
            if len(assets) != len(meta['ips']):
                raise AssetsIpsNotMatch()

            system_user = get_object_or_none(SystemUser, username=meta['system_user'])
            if system_user is None:
                raise SystemUserNotFound()

            kwargs = {
                'name': meta.get('name'),
                'created_by': self.request.user.username
            }

            date_start = meta.get('date_start')
            date_expired = meta.get('date_expired')
            if date_start:
                kwargs['date_start'] = date_start
            if date_expired:
                kwargs['date_expired'] = date_expired

            ap = AssetPermission.objects.create(**kwargs)
            ap.assets.add(*assets)
            ap.system_users.add(system_user)
