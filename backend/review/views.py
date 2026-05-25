"""
Review serializers and views: approval actions, audit log.
"""
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from ingestion.models import RawRecord
from review.models import ApprovalAction, AuditLog
from review.services.approval_service import (
    approve_record, reject_record, lock_batch, ApprovalError
)
from core.models import UploadBatch


class ApprovalActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalAction
        fields = ["id", "action", "analyst_name", "note", "acted_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id", "entity_type", "entity_id", "action",
            "old_value", "new_value", "actor", "occurred_at"
        ]


class ApproveRecordView(APIView):
    """
    POST /api/records/{pk}/approve/

    Body: { "analyst_name": "Jane Smith", "note": "Verified against source" }
    """
    def post(self, request, pk):
        try:
            record = RawRecord.objects.get(pk=pk)
        except RawRecord.DoesNotExist:
            return Response({"detail": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        analyst_name = request.data.get("analyst_name", "").strip()
        if not analyst_name:
            return Response(
                {"analyst_name": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            action = approve_record(
                record,
                analyst_name=analyst_name,
                note=request.data.get("note", "")
            )
        except ApprovalError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response(
            ApprovalActionSerializer(action).data,
            status=status.HTTP_200_OK
        )


class RejectRecordView(APIView):
    """
    POST /api/records/{pk}/reject/

    Body: { "analyst_name": "Jane Smith", "note": "Duplicate from prior batch" }
    """
    def post(self, request, pk):
        try:
            record = RawRecord.objects.get(pk=pk)
        except RawRecord.DoesNotExist:
            return Response({"detail": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

        analyst_name = request.data.get("analyst_name", "").strip()
        if not analyst_name:
            return Response(
                {"analyst_name": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            action = reject_record(
                record,
                analyst_name=analyst_name,
                note=request.data.get("note", "")
            )
        except ApprovalError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response(
            ApprovalActionSerializer(action).data,
            status=status.HTTP_200_OK
        )


class LockBatchView(APIView):
    """
    POST /api/batches/{pk}/lock/

    Locks all APPROVED records in a batch. Irreversible.
    Body: { "analyst_name": "Jane Smith" }
    """
    def post(self, request, pk):
        try:
            batch = UploadBatch.objects.get(pk=pk)
        except UploadBatch.DoesNotExist:
            return Response({"detail": "Batch not found."}, status=status.HTTP_404_NOT_FOUND)

        analyst_name = request.data.get("analyst_name", "").strip()
        if not analyst_name:
            return Response(
                {"analyst_name": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            locked_count = lock_batch(batch, analyst_name=analyst_name)
        except ApprovalError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {"locked_count": locked_count, "message": f"{locked_count} records locked."},
            status=status.HTTP_200_OK
        )


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit-log/

    Query params: entity_type, entity_id, actor
    """
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        qs = AuditLog.objects.all()
        entity_type = self.request.query_params.get("entity_type")
        entity_id = self.request.query_params.get("entity_id")
        actor = self.request.query_params.get("actor")

        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if actor:
            qs = qs.filter(actor=actor)

        return qs
