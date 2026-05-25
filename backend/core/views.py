"""
Core views: batch list, batch detail, file upload, stats.
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from django.db.models import Count, Q
from core.models import Client, SourceType, UploadBatch
from core.serializers import UploadBatchSerializer, SourceTypeSerializer
from ingestion.services.pipeline import ingest_batch


class SourceTypeListView(generics.ListAPIView):
    queryset = SourceType.objects.all()
    serializer_class = SourceTypeSerializer


class BatchListView(generics.ListAPIView):
    queryset = UploadBatch.objects.select_related("client", "source_type").all()
    serializer_class = UploadBatchSerializer
    filterset_fields = ["status", "source_type__code"]


class BatchDetailView(generics.RetrieveAPIView):
    queryset = UploadBatch.objects.select_related("client", "source_type").all()
    serializer_class = UploadBatchSerializer
    lookup_field = "pk"


class UploadView(APIView):
    """
    POST /api/batches/upload/

    Accepts a multipart form with:
    - file: the CSV file
    - source_type_code: e.g., 'sap_fuel'
    - client_slug: e.g., 'acme-corp'
    - uploaded_by: analyst name

    Returns batch details + ingestion stats on success.
    """
    parser_classes = [MultiPartParser]

    def post(self, request):
        file_obj = request.FILES.get("file")
        source_code = request.data.get("source_type_code")
        client_slug = request.data.get("client_slug")
        uploaded_by = request.data.get("uploaded_by", "Unknown Analyst")

        # --- Input validation ---
        errors = {}
        if not file_obj:
            errors["file"] = "A CSV file is required."
        if not source_code:
            errors["source_type_code"] = "source_type_code is required."
        if not client_slug:
            errors["client_slug"] = "client_slug is required."

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # --- File type check ---
        filename = file_obj.name
        if not filename.lower().endswith(".csv"):
            return Response(
                {"file": "Only CSV files are accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Look up source type and client ---
        try:
            source_type = SourceType.objects.get(code=source_code)
        except SourceType.DoesNotExist:
            return Response(
                {"source_type_code": f"Unknown source type: '{source_code}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Auto-create client if not found (useful for dev/demo)
        client, _ = Client.objects.get_or_create(
            slug=client_slug,
            defaults={"name": client_slug.replace("-", " ").title()}
        )

        # --- Create batch record ---
        batch = UploadBatch.objects.create(
            client=client,
            source_type=source_type,
            filename=filename,
            uploaded_by=uploaded_by,
            status="processing",
        )

        # --- Run ingestion pipeline ---
        try:
            file_content = file_obj.read()
            stats = ingest_batch(batch, file_content)
        except Exception as e:
            # Pipeline updates batch.status = 'failed' internally on parse errors
            # This catches any unexpected errors
            batch.refresh_from_db()
            return Response(
                {
                    "error": "Ingestion failed",
                    "detail": str(e),
                    "batch_id": str(batch.id),
                    "batch_status": batch.status,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        batch.refresh_from_db()
        return Response(
            {
                "batch": UploadBatchSerializer(batch).data,
                "stats": stats,
            },
            status=status.HTTP_201_CREATED
        )


class StatsView(APIView):
    """
    GET /api/stats/

    Returns dashboard summary statistics.
    """
    def get(self, request):
        from ingestion.models import RawRecord

        # Status breakdown across all records
        status_counts = (
            RawRecord.objects
            .values("status")
            .annotate(count=Count("id"))
        )

        # CO2e totals by source type (from normalized records)
        from normalization.models import NormalizedRecord
        from django.db.models import Sum
        co2e_by_source = (
            NormalizedRecord.objects
            .values("source_type_code")
            .annotate(total_co2e_kg=Sum("co2e_kg"))
        )

        # Recent batches
        recent_batches = UploadBatch.objects.select_related(
            "source_type"
        ).order_by("-uploaded_at")[:5]

        return Response({
            "status_counts": {item["status"]: item["count"] for item in status_counts},
            "co2e_by_source": list(co2e_by_source),
            "recent_batches": UploadBatchSerializer(recent_batches, many=True).data,
        })
