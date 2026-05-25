"""
Core serializers: Client, SourceType, UploadBatch.
"""
from rest_framework import serializers
from core.models import Client, SourceType, UploadBatch


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "name", "slug", "created_at"]


class SourceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceType
        fields = ["id", "code", "label", "scope"]


class UploadBatchSerializer(serializers.ModelSerializer):
    source_type = SourceTypeSerializer(read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)

    # Computed stats — queried from related RawRecords
    pending_count = serializers.SerializerMethodField()
    suspicious_count = serializers.SerializerMethodField()
    approved_count = serializers.SerializerMethodField()
    locked_count = serializers.SerializerMethodField()

    class Meta:
        model = UploadBatch
        fields = [
            "id", "client_name", "source_type", "filename",
            "uploaded_by", "uploaded_at", "row_count", "status",
            "error_message", "pending_count", "suspicious_count",
            "approved_count", "locked_count",
        ]

    def get_pending_count(self, obj):
        return obj.raw_records.filter(status="pending").count()

    def get_suspicious_count(self, obj):
        return obj.raw_records.filter(status="suspicious").count()

    def get_approved_count(self, obj):
        return obj.raw_records.filter(status="approved").count()

    def get_locked_count(self, obj):
        return obj.raw_records.filter(status="locked").count()
