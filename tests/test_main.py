import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Mock the heavy modules so we don't need paddle/vLLM/PyMuPDF for testing main.py's routing logic
sys.modules['paddleocr'] = MagicMock()
sys.modules['paddlepaddle'] = MagicMock()
sys.modules['fitz'] = MagicMock()

from main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Document OCR API"
    assert "COO" in data["supported_document_types"]

@patch("main.requests.get")
def test_health_endpoint_healthy(mock_get):
    # Mocking external health request to vLLM server
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"
    assert response.json()["model_ready"] is True

@patch("main.requests.get")
def test_health_endpoint_unhealthy(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.ConnectionError()
    
    response = client.get("/health")
    assert response.status_code == 200
    assert "not reachable" in response.json()["status"]
    assert response.json()["model_ready"] is False

@patch("main._process_files", new_callable=AsyncMock)
@patch("main.run_semantic", new_callable=AsyncMock)
@patch("main.create_call_log")
def test_process_ocr_document_non_coo(mock_create_call_log, mock_run_semantic, mock_process_files):
    # Mock return values
    mock_process_files.return_value = [
        {"page_no": 1, "image": MagicMock(), "width": 800, "height": 1000}
    ]
    mock_run_semantic.return_value = {
        "success": True,
        "data": {"nik": "1234567890", "nama": "John Doe"},
        "messages_log": []
    }
    
    # Perform request
    files = [("files", ("ktp.png", b"dummy_content", "image/png"))]
    data = {"document_type": "KTP", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["nama"] == "John Doe"
    assert response.json()["page_dimensions"]["1"] == {"width": 800, "height": 1000}
    
    # Assert main.py routed correctly
    mock_process_files.assert_called_once()
    mock_run_semantic.assert_called_once_with("KTP", mock_process_files.return_value, fields=None, custom_prompt="", show_only_mismatch=False)
    mock_create_call_log.assert_called_once()


@patch("main._process_files", new_callable=AsyncMock)
@patch("main.run_semantic", new_callable=AsyncMock)
@patch("main.create_call_log")
def test_process_ocr_document_coo_success(mock_create_call_log, mock_run_semantic, mock_process_files):
    # Mock process files and run_semantic to simulate sub-document extraction for COO
    # We have 4 separate sub-documents: BL, PEB, PL, INV_COO
    mock_process_files.side_effect = [
        [{"page_no": 1, "image": MagicMock(), "width": 800, "height": 1000}], # BL
        [{"page_no": 1, "image": MagicMock(), "width": 800, "height": 1000}], # PEB
        [{"page_no": 1, "image": MagicMock(), "width": 800, "height": 1000}], # PL
        [{"page_no": 1, "image": MagicMock(), "width": 800, "height": 1000}], # INV_COO
    ]
    
    # run_semantic will be called 4 times
    mock_run_semantic.side_effect = [
        {"success": True, "data": {"consignee": "Receiver Corp", "vessel_voyage_no": "V123", "document_no": "BL999", "document_date": "2026-06-16"}, "messages_log": []}, # BL
        {"success": True, "data": {"nomor_pendaftaran": "PEB111", "tanggal_pendaftaran": "2026-06-15"}, "messages_log": []}, # PEB
        {"success": True, "data": {"no": "PL222", "date": "2026-06-14"}, "messages_log": []}, # PL
        {"success": True, "data": {"invoice_number": "INV333", "invoice_date": "2026-06-13", "total_amount": 1000}, "messages_log": []}, # INV_COO
    ]
    
    # Perform request with 4 files matching the required names
    files = [
        ("files", ("bill_of_lading.pdf", b"bl_bytes", "application/pdf")),
        ("files", ("peb_ekspor.pdf", b"peb_bytes", "application/pdf")),
        ("files", ("packing_list.pdf", b"pl_bytes", "application/pdf")),
        ("files", ("invoice.pdf", b"inv_bytes", "application/pdf")),
    ]
    data = {"document_type": "COO", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 200
    
    res_data = response.json()
    assert res_data["success"] is True
    
    # Assert combined/merged data
    merged = res_data["data"]
    assert merged["consignee"] == "Receiver Corp"
    assert merged["vessel_voyage_no"] == "V123"
    assert merged["document_no_bl"] == "BL999"
    assert merged["document_no_peb"] == "PEB111"
    assert merged["document_no_pl"] == "PL222"
    assert merged["invoice_no"] == "INV333"
    assert res_data["page_dimensions"]["1"] == {"width": 800, "height": 1000}
    assert res_data["page_dimensions"]["4"] == {"width": 800, "height": 1000}
    
    assert mock_process_files.call_count == 4
    assert mock_run_semantic.call_count == 4
    mock_create_call_log.assert_called_once()

def test_process_ocr_document_coo_invalid_composition():
    # 3 files instead of 4 (missing PL)
    files = [
        ("files", ("bill_of_lading.pdf", b"bl_bytes", "application/pdf")),
        ("files", ("peb_ekspor.pdf", b"peb_bytes", "application/pdf")),
        ("files", ("invoice.pdf", b"inv_bytes", "application/pdf")),
    ]
    data = {"document_type": "COO", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "coo_invalid_composition"
    assert "PL" in response.json()["detail"]["message"]

def test_process_ocr_document_coo_too_many_files():
    # 5 files (limit is 4)
    files = [
        ("files", ("bl.pdf", b"1", "application/pdf")),
        ("files", ("peb.pdf", b"2", "application/pdf")),
        ("files", ("pl.pdf", b"3", "application/pdf")),
        ("files", ("inv.pdf", b"4", "application/pdf")),
        ("files", ("extra.pdf", b"5", "application/pdf")),
    ]
    data = {"document_type": "COO", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "coo_files_limit_exceeded"
