from django.urls import path
from core.views import (
    SourceTypeListView, BatchListView, BatchDetailView,
    UploadView, StatsView
)
from ingestion.views import BatchRecordListView, RecordDetailView

urlpatterns = [
    path("source-types/", SourceTypeListView.as_view(), name="source-type-list"),
    path("batches/", BatchListView.as_view(), name="batch-list"),
    path("batches/upload/", UploadView.as_view(), name="batch-upload"),
    path("batches/<uuid:pk>/", BatchDetailView.as_view(), name="batch-detail"),
    path("batches/<uuid:batch_id>/records/", BatchRecordListView.as_view(), name="batch-records"),
    path("records/<uuid:pk>/", RecordDetailView.as_view(), name="record-detail"),
    path("stats/", StatsView.as_view(), name="stats"),
]
