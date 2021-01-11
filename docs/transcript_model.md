# Transcript Data Model

While most users will end up browsing and searching transcripts using the CDP frontend
tooling, we also need a standardized method for storing the transcript data for both
pipeline processing and adds the additional benefit of creating a stable API for
research and archival purposes.

Below you will find an example transcript.<br>
For more specific details please see the
[object definition documentation](./cdp_backend.pipeline.html#module-cdp_backend.pipeline.transcript_models).

## Example Transcript
```json
{
    "confidence": 0.93325,
    "generator": "Google Speech-to-Text -- Lib Version: 2.0.1",
    "session_datetime": "2021-01-11T02:00:32.581238",
    "created_datetime": "2021-01-11T05:00:32.581248",
    "data": [
        {
            "text": "Hello everyone.",
            "start_time": 0.0,
            "end_time": 1.0,
            "speaker": "Jackson Maxfield Brown",
            "annotations": {
                "confidence": 0.987
            }
        },
        {
            "text": "Hey!",
            "start_time": 1.2,
            "end_time": 1.4,
            "speaker": "Isaac Na",
            "annotations": {
                "confidence": 0.912
            }
        },
        {
            "text": "Hello!",
            "start_time": 1.6,
            "end_time": 1.9,
            "speaker": "To Huynh",
            "annotations": {
                "confidence": 0.999
            }
        },
        {
            "text": "Who is speaking this?",
            "start_time": 2.2,
            "end_time": 3.9,
            "speaker": null,
            "annotations": {
                "confidence": 0.835
            }
        }
    ],
    "annotations": null
}
```