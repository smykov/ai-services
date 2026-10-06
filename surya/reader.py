from surya.model.detection.model import load_model as load_detection
from surya.model.detection.model import load_processor as load_det_processor
from surya.model.recognition.model import load_model as load_recognition
from surya.model.recognition.processor import load_processor as load_rec_processor
from surya.ocr import run_ocr

_det_model = None
_det_processor = None
_rec_model = None
_rec_processor = None


def _ensure_models():
    global _det_model, _det_processor, _rec_model, _rec_processor
    if _det_model is None:
        _det_model = load_detection()
        _det_processor = load_det_processor()
        _rec_model = load_recognition()
        _rec_processor = load_rec_processor()


def extract_text(image_path: str, languages: list[str] | None = None) -> dict:
    _ensure_models()

    from PIL import Image
    image = Image.open(image_path)

    langs = [languages or ["en", "ru"]]
    predictions = run_ocr(
        [image], langs, _det_model, _det_processor, _rec_model, _rec_processor
    )

    all_text = []
    blocks = []

    for page in predictions:
        for line in page.text_lines:
            all_text.append(line.text)
            blocks.append({
                "text": line.text,
                "confidence": line.confidence,
                "bbox": line.bbox,
            })

    return {
        "text": "\n".join(all_text),
        "blocks": blocks,
    }

# Preload models at import time so first OCR call doesn't cold-start
_ensure_models()

