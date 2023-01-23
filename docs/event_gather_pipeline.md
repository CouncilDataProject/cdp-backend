# Event Gather Pipeline

Council Data Project documentation generally shortens the steps that the
event gather pipeline takes into three short and easy to remember key points.

1. **Gather Events**<br>
   This function is created by each instance maintainer and
   generally scrapes or requests data from an API and
   returns a list of events to process and store.
   [Learn more about our ingestion models](./ingestion_models.html).
2. **Transcribe**<br>
   If the event was provided with a closed caption file we clean the file up
   into the CDP format, if not, CDP tools generate a transcription.
   [Learn more about the produced transcript model](./transcript_model.html).
3. **Index**<br>
   An entirely different pipeline from the event gather pipeline but in
   the context of the short and sweet version, this makes sense to include.
   This is the pipeline that runs to generate and index using all the event
   transcripts.

These key points make sense from the thousand-foot-view, but is not
satifactory for the developers and others who are simply interested in
how the event gather pipeline works step-by-step.

This document gives visualizations of each and every step the event gather
pipeline takes, starting immediately after the maintainer provided function
returns the `List[EventIngestionModel]`.

### Pipeline Configuration

Pipeline configuration is generally quite simple but can be quite complex if you
need to parametrize specific tasks in the workflow. While generally you will only
need to provide credential details and the `get_events_function` path, full pipeline
configuration can be done with the options found in our
[EventGatherPipelineConfig documentation](./cdp_backend.pipeline.html#module-cdp_backend.pipeline.pipeline_config)
