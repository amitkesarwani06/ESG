"""
Ingestion views: record list (with filtering) and record detail.
"""
from rest_framework import generics
from ingestion.models import RawRecord
from ingestion.serializers import RawRecordListSerializer, RawRecordDetailSerializer
from core.models import UploadBatch


class BatchRecordListView(generics.ListAPIView):
    """
    GET /api/batches/{batch_id}/records/

    Query params:
    - status: filter by status (pending, suspicious, approved, locked)
    """
    serializer_class = RawRecordListSerializer

    def get_queryset(self):
        batch_id = self.kwargs["batch_id"]
        qs = (
            RawRecord.objects
            .filter(batch_id=batch_id)
            .prefetch_related("issues")
            .select_related("normalized")
            .order_by("row_index")
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs


class RecordDetailView(generics.RetrieveAPIView):
    """
    GET /api/records/{pk}/

    Returns full record with validation issues and normalized data.
    """
    serializer_class = RawRecordDetailSerializer

    def get_queryset(self):
        return (
            RawRecord.objects
            .prefetch_related("issues")
            .select_related("normalized", "batch__source_type")
        )
