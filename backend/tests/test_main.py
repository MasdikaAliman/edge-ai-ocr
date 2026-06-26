import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Mock the heavy modules so we don't need paddle/vLLM/PyMuPDF for testing main.py's routing logic
sys.modules['paddleocr'] = MagicMock()
sys.modules['paddlepaddle'] = MagicMock()
sys.modules['fitz'] = MagicMock()

from main import app
from app.utils.auth import get_current_user, get_current_admin
app.dependency_overrides[get_current_user] = lambda: {"username": "Masdika", "role": "admin", "employee": "PKL449"}
app.dependency_overrides[get_current_admin] = lambda: {"username": "Masdika", "role": "admin", "employee": "PKL449"}

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Document OCR API"
    assert "COO" in data["supported_document_types"]

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_health_endpoint_healthy(mock_get):
    # Mocking external health request to vLLM server
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"
    assert response.json()["model_ready"] is True

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_health_endpoint_unhealthy(mock_get):
    import httpx
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    
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
    files = [("files", ("ktp.png", b"\x89PNG\r\n\x1a\n_dummy_content", "image/png"))]
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
        ("files", ("bill_of_lading.pdf", b"%PDF-1.4_bl_bytes", "application/pdf")),
        ("files", ("peb_ekspor.pdf", b"%PDF-1.4_peb_bytes", "application/pdf")),
        ("files", ("packing_list.pdf", b"%PDF-1.4_pl_bytes", "application/pdf")),
        ("files", ("invoice.pdf", b"%PDF-1.4_inv_bytes", "application/pdf")),
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
        ("files", ("bill_of_lading.pdf", b"%PDF-1.4_bl_bytes", "application/pdf")),
        ("files", ("peb_ekspor.pdf", b"%PDF-1.4_peb_bytes", "application/pdf")),
        ("files", ("invoice.pdf", b"%PDF-1.4_inv_bytes", "application/pdf")),
    ]
    data = {"document_type": "COO", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "coo_invalid_composition"
    assert "PL" in response.json()["detail"]["message"]

def test_process_ocr_document_coo_too_many_files():
    # 5 files (limit is 4)
    files = [
        ("files", ("bl.pdf", b"%PDF-1.4_1", "application/pdf")),
        ("files", ("peb.pdf", b"%PDF-1.4_2", "application/pdf")),
        ("files", ("pl.pdf", b"%PDF-1.4_3", "application/pdf")),
        ("files", ("inv.pdf", b"%PDF-1.4_4", "application/pdf")),
        ("files", ("extra.pdf", b"%PDF-1.4_5", "application/pdf")),
    ]
    data = {"document_type": "COO", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "coo_files_limit_exceeded"

def test_magic_bytes_detection():
    from app.utils.image import detect_mime_type, validate_file_content
    from fastapi import HTTPException
    
    # Test valid signatures
    assert detect_mime_type(b"%PDF-1.4") == "application/pdf"
    assert detect_mime_type(b"\x89PNG\r\n\x1a\n") == "image/png"
    assert detect_mime_type(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_mime_type(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert detect_mime_type(b"GIF89a...") == "image/gif"
    assert detect_mime_type(b"II\x2a\x00...") == "image/tiff"
    assert detect_mime_type(b"MM\x00\x2a...") == "image/tiff"
    
    # Test invalid / unrecognized
    assert detect_mime_type(b"plain_text") == "application/octet-stream"
    assert detect_mime_type(b"123") == "application/octet-stream"
    
    # Test validate_file_content
    assert validate_file_content(b"%PDF-1.5", "test.pdf") == "application/pdf"
    
    with pytest.raises(HTTPException) as exc_info:
        validate_file_content(b"invalid_signature_bytes", "test.txt")
    assert exc_info.value.status_code == 415
    assert exc_info.value.detail["error_type"] == "unsupported_media_type"

def test_process_ocr_document_invalid_mime():
    # Upload an invalid text file (magic bytes won't match any allowed types)
    files = [("files", ("document.txt", b"plain text content which is not an image", "text/plain"))]
    data = {"document_type": "KTP", "pages": ""}
    
    response = client.post("/ocr/process/document", files=files, data=data)
    assert response.status_code == 415
    assert response.json()["detail"]["error_type"] == "unsupported_media_type"

@patch("main.delete_user")
def test_delete_user_endpoint_success(mock_delete):
    mock_delete.return_value = True
    response = client.delete("/api/users/JohnDoe")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "JohnDoe" in response.json()["message"]
    mock_delete.assert_called_once_with("JohnDoe")

def test_delete_user_endpoint_cannot_delete_self():
    # current_admin dependency override in tests returns {"username": "Masdika", "role": "admin", "employee": "PKL449"}
    response = client.delete("/api/users/Masdika")
    assert response.status_code == 400
    assert response.json()["detail"]["error_type"] == "cannot_delete_self"

@patch("main.delete_user")
def test_delete_user_endpoint_not_found(mock_delete):
    mock_delete.return_value = False
    response = client.delete("/api/users/UnknownUser")
    assert response.status_code == 404
    assert response.json()["detail"]["error_type"] == "user_not_found"

@patch("main.update_user")
def test_update_user_endpoint_success(mock_update):
    mock_update.return_value = {"username": "John New", "employee": "PKL440", "role": "user"}
    payload = {"username": "John New", "password": "newpassword123", "role": "user"}
    response = client.put("/api/users/PKL440", json=payload)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "PKL440" in response.json()["message"]
    mock_update.assert_called_once_with(
        employee="PKL440",
        username="John New",
        plain_password="newpassword123",
        role="user",
        new_employee=None
    )

@patch("main.update_user")
def test_update_user_endpoint_not_found(mock_update):
    mock_update.return_value = None
    payload = {"username": "John New"}
    response = client.put("/api/users/PKL440", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"]["error_type"] == "user_not_found"

