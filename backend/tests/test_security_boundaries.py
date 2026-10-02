import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

# ডামি টোকেন বা হেডার (অথবা টেস্ট মক)
STUDENT_AUTH_HEADER = {"Authorization": "Bearer TEST_STUDENT_JWT"}
FACULTY_AUTH_HEADER = {"Authorization": "Bearer TEST_FACULTY_JWT"}
INVALID_AUTH_HEADER = {"Authorization": "Bearer MALFORMED_OR_EXPIRED_JWT"}

@pytest.mark.asyncio
async def test_unauthenticated_requests_blocked():
    """রুটগুলোতে টোকেন ছাড়া রিকোয়েস্ট পাঠালে ৪০১ আনঅথোরাইজড আসে কিনা যাচাই"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Chat Workspace List
        res = await client.get("/api/v1/chat/workspaces")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"

        # 2. Document Upload
        res = await client.post("/api/v1/documents/upload")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"

        # 3. Admin Analytics
        res = await client.get("/api/v1/admin/analytics")
        assert res.status_code in [401, 403], f"Expected 401/403, got {res.status_code}"


@pytest.mark.asyncio
async def test_role_privilege_escalation():
    """স্টুডেন্ট অ্যাকাউন্টের টোকেন দিয়ে ফ্যাকাল্টি বা অ্যাডমিন এন্ডপয়েন্ট অ্যাক্সেস ব্লক হচ্ছে কিনা"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # স্টুডেন্ট হয়ে Faculty Overview কল করা
        res = await client.get("/api/v1/faculty/overview", headers=STUDENT_AUTH_HEADER)
        assert res.status_code == 403, f"Expected 403 Forbidden for Student, got {res.status_code}"

        # স্টুডেন্ট হয়ে Knowledge Base Upload কল করা
        res = await client.post("/api/v1/admin/knowledge-base/upload", headers=STUDENT_AUTH_HEADER)
        assert res.status_code == 403, f"Expected 403 Forbidden for Student, got {res.status_code}"


@pytest.mark.asyncio
async def test_idor_cross_user_workspace_isolation():
    """ইউজার A এর টোকেন দিয়ে ইউজার B এর ওয়ার্কস্পেস অ্যাক্সেস ব্লক হয় কিনা"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # অন্যের ওয়ার্কস্পেস আইডি
        victim_workspace_id = "00000000-0000-0000-0000-000000000000"
        
        res = await client.get(
            f"/api/v1/chat/history/{victim_workspace_id}", 
            headers=STUDENT_AUTH_HEADER
        )
        assert res.status_code in [403, 404], f"IDOR Vulnerability! Expected 403/404, got {res.status_code}"


@pytest.mark.asyncio
async def test_payload_fuzzing_extra_forbidden():
    """অননুমোদিত বা ক্ষতিকর এক্সট্রা ফিল্ড ইনজেক্ট করলে ৪২২ আনপ্রসেসেবল আসে কিনা"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pydantic Schemas with extra="forbid"
        malicious_payload = {
            "topic": "International Relations Theory",
            "feature_type": "flashcards",
            "role": "admin",              # Privilege injection attempt
            "bypass_auth": True,          # Logic bypass attempt
            "unexpected_field": "test"
        }
        res = await client.post(
            "/api/v1/powerups/gamify", 
            json=malicious_payload, 
            headers=STUDENT_AUTH_HEADER
        )
        # extra="forbid" থাকলে ৪২২ আসবে
        assert res.status_code in [422, 400], f"Schema accepted extra fields without validation: {res.status_code}"