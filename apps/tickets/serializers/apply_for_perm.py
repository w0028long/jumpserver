from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models.asset import Asset
from assets.models.user import SystemUser
from ..models import Ticket


class ApplyForPermSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=128, source='meta.name', default='')
    ips = serializers.ListField(child=serializers.IPAddressField(), source='meta.ips', default=list)
    system_user = serializers.CharField(max_length=64, source='meta.system_user', default=None)
    date_start = serializers.DateTimeField(source='meta.date_start', default=None)
    date_expired = serializers.DateTimeField(source='meta.date_expired', default=None)

    assets = serializers.SerializerMethodField()
    system_user_exist = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        mini_fields = ['id']
        small_fields = [
            'title', 'status', 'action', 'date_created', 'date_updated',
            'type', 'type_display', 'action_display', 'ips', 'system_user',
            'date_start', 'date_expired'
        ]
        m2m_fields = [
            'user', 'user_display', 'assignees', 'assignees_display',
            'assignee', 'assignee_display', 'assets', 'system_user_exist'
        ]

        fields = mini_fields + small_fields + m2m_fields
        read_only_fields = [
            'user_display', 'assignees_display', 'type', 'user',
            'date_created', 'date_updated', 'action'
        ]
        extra_kwargs = {
            'status': {'label': _('Status')},
            'action': {'label': _('Action')},
            'user_display': {'label': _('User')}
        }

    def create(self, validated_data):
        validated_data['type'] = self.Meta.model.TYPE_APPLY_FOR_PERM
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def get_system_user_exist(self, obj: Ticket):
        if not self._is_assignee(obj):
            return None
        return SystemUser.objects.filter(username=obj.meta['system_user']).exists()

    def _is_assignee(self, obj: Ticket):
        user = self.context['request'].user
        return obj.is_assignee(user)

    def get_assets(self, obj: Ticket):
        if not self._is_assignee(obj):
            return None
        assets = Asset.objects.filter(ip__in=obj.meta['ips'])
        return [{'ip': asset.ip, 'hostname': asset.hostname} for asset in assets]
