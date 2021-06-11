from ..sr_models import SRModel
from prefect import task
from prefect.triggers import all_finished
from ..pipeline.transcript_model import Transcript
from typing import Any, List, Optional, Union
import logging

from pathlib import Path

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
    return sr_model.transcribe(file_uri, phrases, **kwargs)

