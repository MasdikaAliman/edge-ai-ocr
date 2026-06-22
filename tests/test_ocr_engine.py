import pytest
from unittest.mock import MagicMock, patch
from PIL import Image
from app.services.ocr_engine import run_ocr_on_image

@patch("app.services.ocr_engine.get_ocr_engine")
def test_run_ocr_on_image(mock_get_ocr):
    # Mock paddleocr instance
    mock_ocr = MagicMock()
    mock_get_ocr.return_value = mock_ocr
    
    # Mock predict output
    # PaddleOCR predict output: List of dict-like items with rec_texts, rec_scores, rec_boxes
    mock_res = MagicMock()
    mock_res.get.side_effect = lambda key, default=None: {
        "rec_texts": ["Test Text"],
        "rec_scores": [0.9876],
        "rec_boxes": [[[10, 20], [50, 20], [50, 40], [10, 40]]]
    }.get(key, default)
    
    mock_ocr.predict.return_value = [mock_res]
    
    img = Image.new("RGB", (100, 100))
    fragments = run_ocr_on_image(img, page_no=1)
    
    assert len(fragments) == 1
    assert fragments[0]["text"] == "Test Text"
    assert fragments[0]["bbox"] == [10, 20, 50, 40]
    assert fragments[0]["confidence"] == 0.9876
    assert fragments[0]["page_no"] == 1
