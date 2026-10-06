from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..core.auth import verify_api_key
from ..core.config import settings
from ..core.container import container

router = APIRouter(dependencies=[Depends(verify_api_key)], tags=["classify"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


class ClassifyResponse(BaseModel):
    type: str
    """Image type: receipt, document, person, or other"""
    has_pii: bool
    """True if the image contains personal identifiable information"""
    description: str
    """Brief one-sentence description of the image content"""


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Classify image type and detect PII",
    description=(
        "Classifies an uploaded image using the **qwen2.5-vl** vision model. "
        "Returns the document type (`receipt`, `document`, `person`, `other`) and "
        "whether personal information (PII) is present in the image. "
        "Intended as a pre-processing gate before OCR: if `has_pii=true` and type is "
        "`document` or `receipt`, downstream systems can decide whether to mask or reject."
    ),
)
async def classify_image(
    file: UploadFile = File(..., description="Image file: JPEG, PNG, or WebP"),
):
    """
    ### Request
    - `file` — image to classify (multipart/form-data)

    ### Response
    | Field | Type | Description |
    |-------|------|-------------|
    | `type` | string | `receipt` | `document` | `person` | `other` |
    | `has_pii` | bool | Whether PII is detected (name, face, ID number, etc.) |
    | `description` | string | Brief description of the image |

    ### Errors
    - `415` — unsupported image format
    - `413` — file too large
    - `503` — vision model unavailable
    """
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type: {file.content_type}. Supported: jpeg, png, webp",
        )
    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        result = await container.llm.classify_image(
            image_bytes=contents,
            mime_type=file.content_type or "image/jpeg",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    doc_type = result.get("type", "other")
    if doc_type not in ("receipt", "document", "person", "other"):
        doc_type = "other"

    return ClassifyResponse(
        type=doc_type,
        has_pii=bool(result.get("has_pii", False)),
        description=str(result.get("description", "")),
    )
