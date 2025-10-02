import func
from cloudevents.http import CloudEvent
import functions_framework

@functions_framework.cloud_event
def ingest_revenues(event: CloudEvent):
    func.run_ingest(event)