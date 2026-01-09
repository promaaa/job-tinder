import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.store import get_store

@pytest.fixture()
def sandbox(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("JOB_TINDER_ROOT", str(tmp_path))
    get_store.cache_clear()
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Init empty files
    (data_dir / "contacts.json").write_text("[]", encoding="utf-8")
    (data_dir / "outreach.json").write_text("[]", encoding="utf-8")
    
    # Stub profile
    (data_dir / "cv_profile.json").write_text(json.dumps({"name": "Test User", "skills": ["Python"]}), encoding="utf-8")
    
    yield tmp_path
    monkeypatch.delenv("JOB_TINDER_ROOT", raising=False)
    get_store.cache_clear()

@pytest.fixture()
def client(sandbox):
    return TestClient(app)

def test_contact_lifecycle(client, sandbox):
    # 1. Create Contact
    payload = {
        "name": "Alice Recruiter",
        "email": "alice@tech.co",
        "role": "HR Manager",
        "company": "Tech Co"
    }
    resp = client.post("/contacts", json=payload)
    assert resp.status_code == 200
    
    # 2. List to get ID
    resp = client.get("/contacts")
    contacts = resp.json()
    assert len(contacts) == 1
    c_id = contacts[0]["id"]
    
    # 3. Generate Draft
    resp = client.post("/outreach/generate", json={"contact_id": c_id})
    assert resp.status_code == 200
    msg = resp.json()
    m_id = msg["id"]
    assert msg["status"] == "draft"
    assert "Tech Co" in msg["subject"]
    
    # 4. Send (Mocked)
    # We patch the 'send' method on the class itself
    with patch("backend.outreach.sender.EmailSender.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        resp = client.post(f"/outreach/{m_id}/send")
        assert resp.status_code == 200
        
        # TestClient (Starlette) runs background tasks synchronously after request
        mock_send.assert_called_once()
        
def test_attachment_flow(client, sandbox):
    # 1. Setup Profile with Attachment
    cv_path = sandbox / "my_cv.pdf"
    cv_path.write_text("dummy content")
    
    profile = {
        "name": "Test User",
        "email": "test@user.com",
        "uploaded_file": {
            "filename": "my_cv.pdf",
            "path": str(cv_path),
            "size": 123
        }
    }
    client.post("/cv", json=profile)
    
    # 2. Create Contact
    c_resp = client.post("/contacts", json={"name": "Bob", "email": "bob@corp.com"})
    c_id = client.get("/contacts").json()[0]["id"]
    
    # 3. Generate Draft with Attachment
    resp = client.post("/outreach/generate", json={"contact_id": c_id, "attach_cv": True})
    assert resp.status_code == 200
    msg = resp.json()
    assert len(msg["attachments"]) == 1
    assert msg["attachments"][0] == str(cv_path)
    
    # 4. Send with Attachment
    with patch("backend.outreach.sender.EmailSender.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        client.post(f"/outreach/{msg['id']}/send")
        
        # Verify call args
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        # Depending on how it was called (args vs kwargs), check attachments
        # send(message, to_email, attachments=...)
        assert "attachments" in call_kwargs or len(mock_send.call_args.args) > 2
        
        if "attachments" in call_kwargs:
            assert call_kwargs["attachments"] == [str(cv_path)]

