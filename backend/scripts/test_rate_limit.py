import asyncio
import httpx

API_URL = "http://127.0.0.1:8000/api/v1/academic/generate"
# আপনার টেস্ট টোকেন এখানে দিন
TOKEN = "YOUR_VALID_STUDENT_JWT"

async def send_burst():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {"topic": "Sovereignty in 2026", "task_type": "Literature Review"}
    
    print("🚀 Firing 20 rapid requests to test endpoint rate limits...")
    async with httpx.AsyncClient() as client:
        tasks = [client.post(API_URL, json=payload, headers=headers, timeout=10) for _ in range(20)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_counts = {}
        for r in responses:
            if isinstance(r, httpx.Response):
                status_counts[r.status_code] = status_counts.get(r.status_code, 0) + 1
            else:
                status_counts["Error"] = status_counts.get("Error", 0) + 1
                
        print(f"📊 Result Status Codes: {status_counts}")
        if 429 in status_counts:
            print("✅ Rate Limiter is ACTIVE! 429 Too Many Requests returned.")
        else:
            print("⚠️ WARNING: No 429 detected. Endpoints might be vulnerable to cost exhaustion.")

if __name__ == "__main__":
    asyncio.run(send_burst())