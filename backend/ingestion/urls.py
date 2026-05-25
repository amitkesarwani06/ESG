from django.urls import path
from ingestion.views import BatchRecordListView, RecordDetailView

urlpatterns = [
    # These are also defined in core.urls — keeping here for clarity
    # The router in config/urls.py includes both core and ingestion urls
    # so we only put ingestion-specific routes here
]
