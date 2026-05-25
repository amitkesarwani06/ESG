from django.urls import path
from review.views import (
    ApproveRecordView, RejectRecordView,
    LockBatchView, AuditLogListView
)

urlpatterns = [
    path("records/<uuid:pk>/approve/", ApproveRecordView.as_view(), name="record-approve"),
    path("records/<uuid:pk>/reject/", RejectRecordView.as_view(), name="record-reject"),
    path("batches/<uuid:pk>/lock/", LockBatchView.as_view(), name="batch-lock"),
    path("audit-log/", AuditLogListView.as_view(), name="audit-log"),
]
