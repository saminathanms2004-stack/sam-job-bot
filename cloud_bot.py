"""
Cloud Job Bot Runner
Sam's LinkedIn Auto-Applier — Cloud Version
Runs on GitHub Actions (headless), uses Groq API (free) for AI,
Supabase for job deduplication, Telegram for notifications.
"""
import os, sys, json, time, requests
from datetime import datetime

# ── Config from env vars (GitHub Secrets) ──────────────────────────────────
LINKEDIN_USERNAME = os.environ.get("LINKEDIN_USERNAME", "")
LINKEDIN_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY", "")
SUPABASE_URL       = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY       = os.environ.get("SUPABASE_KEY", "")
MAX_JOBS           = int(os.environ.get("MAX_JOBS", "15"))

def telegram_notify(msg):
    """Send Telegram message."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM SKIP] {msg}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def groq_rewrite_cover(job_title, company, resume_snippet):
    """Use Groq free API to tailor cover note."""
    if not GROQ_API_KEY:
        return f"Interested in {job_title} at {company}."
    try:
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{
                "role": "user",
                "content": f"Write a 2-sentence cover note for {job_title} at {company}. My background: {resume_snippet}. Be direct, no fluff."
            }],
            "max_tokens": 120
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers=headers, json=payload, timeout=15)
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return f"Interested in {job_title} at {company}."

def supabase_already_applied(job_id):
    """Check Supabase if we already applied to this job."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = requests.get(f"{SUPABASE_URL}/rest/v1/applied_jobs?job_id=eq.{job_id}",
                         headers=headers, timeout=10)
        return len(r.json()) > 0
    except:
        return False

def supabase_log_job(job_id, job_title, company, status="applied"):
    """Log applied job to Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        data = {
            "job_id": job_id,
            "job_title": job_title,
            "company": company,
            "status": status,
            "applied_at": datetime.utcnow().isoformat()
        }
        requests.post(f"{SUPABASE_URL}/rest/v1/applied_jobs",
                      headers=headers, json=data, timeout=10)
    except Exception as e:
        print(f"Supabase log error: {e}")

def main():
    print(f"[{datetime.now()}] Cloud Job Bot starting...")
    telegram_notify(f"🤖 Job bot started at {datetime.now().strftime('%H:%M IST')}")
    
    # Import the actual LinkedIn bot (must be in same directory or PYTHONPATH)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        # Override secrets with env vars before importing
        import config.secrets as sec
        sec.username = LINKEDIN_USERNAME or sec.username
        sec.password = LINKEDIN_PASSWORD or sec.password
        sec.llm_api_key = GROQ_API_KEY if GROQ_API_KEY else "not-needed"
        if GROQ_API_KEY:
            sec.llm_api_url = "https://api.groq.com/openai/v1/"
            sec.llm_model = "llama3-8b-8192"
            sec.ai_provider = "openai"
        
        print("Config patched. Running bot...")
        # The actual LinkedIn bot entry point
        from linkedIn_easy_applier import start_applying
        applied, skipped = start_applying(max_applications=MAX_JOBS,
                                          already_applied_check=supabase_already_applied,
                                          on_apply=supabase_log_job)
        msg = f"✅ Bot done! Applied: {applied} | Skipped: {skipped}"
        print(msg)
        telegram_notify(msg)
    except ImportError as e:
        # Standalone mode — just notify
        msg = f"⚠️ Bot ran in standalone mode (import error): {e}"
        print(msg)
        telegram_notify(msg)

if __name__ == "__main__":
    main()
