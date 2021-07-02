import logging
from pathlib import Path
from typing import Any, List, Optional, Union

from prefect import task

from ..pipeline.transcript_model import Transcript
from ..sr_models import SRModel

###############################################################################

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
)
log = logging.getLogger(__name__)

###############################################################################


@task
def transcribe_task(
    sr_model: SRModel,
    file_uri: Union[str, Path],
    phrases: Optional[List[str]] = None,
    **kwargs: Any
) -> Transcript:
    return sr_model.transcribe(file_uri, phrases=phrases, **kwargs)
