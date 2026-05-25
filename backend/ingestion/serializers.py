"""
Ingestion serializers: RawRecord + related ValidationIssues + NormalizedRecord.
"""
from rest_framework import serializers
from ingestion.models import RawRecord
from validation.models import ValidationIssue
from normalization.models import NormalizedRecord


class ValidationIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationIssue
        fields = ["id", "issue_code", "severity", "field_name", "message", "created_at"]


class NormalizedRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = NormalizedRecord
        exclude = ["raw_record"]  # Avoid circular reference


class RawRecordListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for table/list views.
    Does not embed full normalized data to keep response size manageable.
    """
    issue_count = serializers.SerializerMethodField()
    error_count = serializers.SerializerMethodField()
    has_normalized = serializers.SerializerMethodField()
    co2e_kg = serializers.SerializerMethodField()

    class Meta:
        model = RawRecord
        fields = [
            "id", "row_index", "raw_data", "ingested_at", "status",
            "issue_count", "error_count", "has_normalized", "co2e_kg",
        ]

    def get_issue_count(self, obj):
        return obj.issues.count()

    def get_error_count(self, obj):
        return obj.issues.filter(severity="error").count()

    def get_has_normalized(self, obj):
        return hasattr(obj, "normalized")

    def get_co2e_kg(self, obj):
        if hasattr(obj, "normalized") and obj.normalized.co2e_kg is not None:
            return float(obj.normalized.co2e_kg)
        return None


class RawRecordDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for single record view — includes issues and normalized data.
    """
    issues = ValidationIssueSerializer(many=True, read_only=True)
    normalized = NormalizedRecordSerializer(read_only=True)

    class Meta:
        model = RawRecord
        fields = [
            "id", "batch", "row_index", "raw_data", "ingested_at",
            "status", "issues", "normalized",
        ]
