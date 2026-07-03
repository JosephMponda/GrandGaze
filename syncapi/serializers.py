from rest_framework import serializers

from .models import SyncConflict, SyncSubmission


class SyncSubmitSerializer(serializers.Serializer):
    client_uuid = serializers.CharField(max_length=255)
    form_type = serializers.CharField(max_length=50)
    payload_json = serializers.JSONField()


class SyncStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncSubmission
        fields = ["client_uuid", "form_type", "status", "received_at", "applied_at", "conflict_note"]


class SyncConflictSerializer(serializers.ModelSerializer):
    client_uuid = serializers.CharField(source="submission.client_uuid", read_only=True)

    class Meta:
        model = SyncConflict
        fields = ["client_uuid", "conflicting_record_description", "resolved_at"]
