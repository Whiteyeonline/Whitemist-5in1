import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import ssl
import socket
import json
import time
from datetime import datetime, timezone
import urllib.parse
from google import genai
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =============================================
# PAGE CONFIG
# =============================================
st.set_page_config(page_title="🚀 Side Hustle Intelligence Engine", page_icon="🚀", layout="wide")

# =============================================
# API KEY SETUP
# =============================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None
PAGESPEED_API_KEY = st.secrets.get("PAGESPEED_API_KEY") if "PAGESPEED_API_KEY" in st.secrets else None

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/idea.png", width=60)
    st.title("🔐 API Keys")
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = st.text_input("Gemini API Key (Jobs 3-5)", type="password",
                                        help="Free at aistudio.google.com. No credit card needed.")
    if not PAGESPEED_API_KEY:
        PAGESPEED_API_KEY = st.text_input("PageSpeed Key (Jobs 1-2, optional)", type="password",
                                           help="Free from Google Cloud Console. Speeds up audits.")

    st.divider()
    st.markdown("### 🧰 Intelligence Suite")
    job_selection = st.radio(
        "Select Tool:",
        [
            "1️⃣ Website SEO & Health Audit",
            "2️⃣ Competitor Intelligence Dashboard",
            "3️⃣ AI Content & Copy Studio",
            "4️⃣ Global Trademark & Brand Checker",
            "5️⃣ OSINT Footprint & Life History",
        ]
    )
    st.divider()
    st.caption("v2.0 — Free. Zero maintenance. No databases to run.")

# =============================================
# SHARED HELPERS
# =============================================

@st.cache_data(ttl=3600)
def cached_ssl_check(hostname):
    return check_ssl(hostname)

def check_ssl(hostname):
    """Check SSL certificate validity and issuer."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        issuer = dict(x[0] for x in cert.get('issuer', [])) if cert.get('issuer') else {}
        expiry = cert.get('notAfter', 'Unknown')
        issuer_name = issuer.get('organizationName', 'Unknown')
        return True, issuer_name, expiry
    except Exception as e:
        return False, str(e), None


@st.cache_data(ttl=3600)
def cached_lighthouse(url):
    return fetch_lighthouse(url)

def fetch_lighthouse(url):
    """Fetch PageSpeed/Lighthouse scores."""
    params = {"url": url, "category": ["PERFORMANCE", "SEO", "ACCESSIBILITY", "BEST_PRACTICES"]}
    if PAGESPEED_API_KEY:
        params["key"] = PAGESPEED_API_KEY
    try:
        r = requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                         params=params, timeout=30)
        data = r.json()
        cats = data['lighthouseResult']['categories']
        scores = {cat: int(details['score'] * 100) for cat, details in cats.items()}
        audits = data['lighthouseResult'].get('audits', {})
        metrics = {}
        for key, label in [("first-contentful-paint", "FCP"), ("interactive", "TTI"),
                           ("total-blocking-time", "TBT"), ("largest-contentful-paint", "LCP"),
                           ("cumulative-layout-shift", "CLS")]:
            if key in audits:
                raw = audits[key].get('numericValue')
                if raw is not None:
                    metrics[label] = round(raw / 1000, 2) if key not in ("total-blocking-time", "cumulative-layout-shift") else round(raw, 3)
        return scores, metrics
    except Exception as e:
        return None, None


@st.cache_data(ttl=600)
def cached_fetch(url):
    return safe_fetch(url)

def safe_fetch(url, timeout=10):
    """Safe HTTP GET with common user-agent."""
    try:
        h = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        return requests.get(url, headers=h, timeout=timeout)
    except Exception:
        return None


def check_social_handle(platform, username):
    """Check if a username exists on a social platform via HTTP status."""
    patterns = {
        "Twitter/X": "https://x.com/{}",
        "Instagram": "https://instagram.com/{}",
        "LinkedIn (profile)": "https://linkedin.com/in/{}",
        "GitHub": "https://github.com/{}",
        "YouTube": "https://youtube.com/@{}",
        "Reddit": "https://reddit.com/user/{}",
        "TikTok": "https://tiktok.com/@{}",
        "Medium": "https://medium.com/@{}",
        "Pinterest": "https://pinterest.com/{}",
        "Twitch": "https://twitch.tv/{}",
        "Dev.to": "https://dev.to/{}",
        "Facebook": "https://facebook.com/{}",
    }
    if platform not in patterns:
        return None
    url = patterns[platform].format(username)
    try:
        r = requests.get(url, timeout=5, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return "✅ TAKEN", url
        elif r.status_code == 404:
            return "🟢 AVAILABLE", url
        else:
            return f"⚠️ {r.status_code}", url
    except Exception:
        return "❌ ERROR", url


@st.cache_data(ttl=1800)
def rdap_lookup(domain):
    """Free RDAP domain lookup — no API key needed."""
    try:
        r = requests.get(f"https://rdap.org/domain/{domain}",
                         headers={"Accept": "application/json"},
                         timeout=10)
        if r.status_code == 200:
            data = r.json()
            result = {}
            # Extract events
            events = {e["eventAction"]: e["eventDate"] for e in data.get("events", [])}
            result["creation_date"] = events.get("registration")
            result["expiry_date"] = events.get("expiration")
            result["last_changed"] = events.get("last changed")

            # Extract registrar
            entities = data.get("entities", [])
            for ent in entities:
                if any(role in ("registrar",) for role in ent.get("roles", [])):
                    vcard = ent.get("vcardArray", [[], []])[1]
                    for item in vcard:
                        if item[0] == "fn":
                            result["registrar"] = item[3]
                            break
            # Extract name servers
            ns = data.get("nameservers", [])
            result["nameservers"] = [n.get("ldhName") for n in ns if n.get("ldhName")]

            # Extract status
            result["status"] = data.get("status", [])

            return result
    except Exception:
        return None


def search_tmview(brand, max_results=15):
    """Search TMview (EUIPO global cross-register) — FREE, NO API KEY."""
    try:
        payload = {
            "page": "1",
            "pageSize": str(max_results),
            "criteria": "C",
            "basicSearch": brand
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Origin": "https://www.tmdn.org",
            "Referer": "https://www.tmdn.org/tmview/"
        }
        r = requests.post("https://www.tmdn.org/tmview/api/search/results",
                          json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            return data.get("results", data)
        return None
    except Exception as e:
        return None


def search_uspto(brand, max_results=10):
    """Search USPTO trademark database — FREE, NO API KEY."""
    try:
        payload = {
            "query": brand,
            "from": 0,
            "size": max_results
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        r = requests.post("https://tmsearch.uspto.gov/prod-v1-0-0/tmsearch",
                          json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ============================================
# JOB 1: WEBSITE SEO & HEALTH AUDIT
# ============================================
if job_selection == "1️⃣ Website SEO & Health Audit":
    st.header("🔍 Website SEO & Health Audit")
    st.caption("Complete technical SEO inspection: SSL, meta tags, headings, images, viewport, Core Web Vitals — deliver this as a $50-200 freelance report.")

    target_url = st.text_input("Enter Website URL:", placeholder="https://example.com")

    if st.button("Run Full Audit", type="primary"):
        if not target_url.startswith(("http://", "https://")):
            st.error("Enter a URL starting with http:// or https://")
            st.stop()

        domain = urllib.parse.urlparse(target_url).netloc

        with st.spinner("Running 7-point technical audit..."):
            ssl_ok, ssl_info, ssl_expiry = cached_ssl_check(domain)
            scores, metrics = cached_lighthouse(target_url)

            resp = cached_fetch(target_url)
            html_ok = resp is not None and resp.status_code == 200
            soup = BeautifulSoup(resp.text, "html.parser") if html_ok else None

            # --- META ANALYSIS ---
            title_tag = soup.title.string.strip() if soup and soup.title else None
            title_len = len(title_tag) if title_tag else 0
            meta_desc = soup.find("meta", attrs={"name": "description"})
            meta_desc_content = meta_desc["content"].strip() if meta_desc and meta_desc.get("content") else None
            viewport = soup.find("meta", attrs={"name": "viewport"})
            canonical = soup.find("link", rel="canonical")
            og_title = soup.find("meta", property="og:title")
            og_desc = soup.find("meta", property="og:description")
            og_image = soup.find("meta", property="og:image")

            # --- HEADINGS ---
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1")] if soup else []
            h2s = [h.get_text(strip=True) for h in soup.find_all("h2")] if soup else []

            # --- IMAGES ---
            imgs = soup.find_all("img") if soup else []
            imgs_with_alt = [i for i in imgs if i.get("alt")]
            imgs_missing_alt = [i for i in imgs if not i.get("alt")]
            alt_pct = round(len(imgs_with_alt) / len(imgs) * 100) if imgs else 100

            # --- LINKS ---
            internal_links = []
            external_links = []
            broken_count = 0
            if soup:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith(("http://", "https://")):
                        if domain in href:
                            internal_links.append(href)
                        else:
                            external_links.append(href)
                    elif href.startswith("/") or href.startswith("#") or href.startswith("?"):
                        internal_links.append(href)

        # ====== DISPLAY ======
        st.subheader("📋 Audit Report")
        st.caption(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

        tab1, tab2, tab3, tab4 = st.tabs(
            ["🔒 Security & Meta", "📐 Structure & Media", "⚡ Performance", "📊 Score Overview"]
        )

        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔒 SSL Certificate",
                          "✅ Valid" if ssl_ok else "❌ Invalid",
                          delta=f"Issuer: {ssl_info}" if ssl_ok else ssl_info)
                if ssl_ok and ssl_expiry:
                    st.caption(f"Expires: {ssl_expiry}")

                st.metric("📄 Title Tag",
                          f"✅ {title_len} chars" if title_tag else "❌ Missing")
                if title_tag:
                    st.info(f"`{title_tag[:80]}{'...' if len(title_tag) > 80 else ''}`")
                    if title_len < 30:
                        st.warning("⚠️ Title too short (< 30 chars) — bad for SEO")
                    elif title_len > 60:
                        st.warning("⚠️ Title may truncate in SERPs (> 60 chars)")

            with col2:
                st.metric("📱 Mobile Viewport",
                          "✅ Configured" if viewport else "❌ MISSING")
                st.metric("🔗 Canonical URL",
                          "✅ Present" if canonical else "⚠️ Missing (duplicate content risk)")
                st.metric("📢 Open Graph",
                          "✅ Complete" if og_title and og_desc and og_image
                          else "⚠️ Partial" if (og_title or og_desc)
                          else "❌ Missing (bad for social sharing)")

            if meta_desc_content:
                st.metric("📝 Meta Description", f"✅ {len(meta_desc_content)} chars")
                st.info(meta_desc_content[:150])
                if len(meta_desc_content) < 50:
                    st.warning("⚠️ Too short (< 50 chars)")
                elif len(meta_desc_content) > 160:
                    st.warning("⚠️ May truncate in SERPs (> 160 chars)")
            else:
                st.metric("📝 Meta Description", "❌ Missing (bad for CTR)")

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("H1 Tags", len(h1s),
                          delta="✅ Exactly 1" if len(h1s) == 1
                          else "❌ Should have 1" if len(h1s) == 0
                          else f"⚠️ {len(h1s)} H1s found (use 1)")
                if h1s:
                    for i, h in enumerate(h1s):
                        st.caption(f"  H1 #{i+1}: {h[:100]}")

                st.metric("H2 Tags", len(h2s))
                if h2s:
                    for i, h in enumerate(h2s[:5]):
                        st.caption(f"  H2 #{i+1}: {h[:80]}")
                    if len(h2s) > 5:
                        st.caption(f"  ... +{len(h2s)-5} more")

            with col2:
                st.metric("Images with Alt Text",
                          f"{alt_pct}% ({len(imgs_with_alt)}/{len(imgs)})",
                          delta="✅ Good" if alt_pct >= 80
                          else "⚠️ Needs work" if alt_pct >= 50
                          else "❌ Poor — accessibility risk")
                if imgs_missing_alt:
                    with st.expander(f"View {len(imgs_missing_alt)} images missing alt text"):
                        for img in imgs_missing_alt[:10]:
                            src = img.get("src", "?")
                            st.caption(f"  • `{src[:60]}`")
                        if len(imgs_missing_alt) > 10:
                            st.caption(f"  ... +{len(imgs_missing_alt)-10} more")

                st.metric("Internal Links", len(internal_links))
                st.metric("External Links", len(external_links))

        with tab3:
            if scores and metrics:
                col1, col2, col3, col4, col5 = st.columns(5)
                metric_map = {"performance": "Performance", "seo": "SEO",
                              "accessibility": "Accessibility", "best-practices": "Best Practices"}
                labels = list(metric_map.keys())
                for i, (key, label) in enumerate(metric_map.items()):
                    val = scores.get(key, 0)
                    color = "normal" if val >= 80 else ("warning" if val >= 50 else "error")
                    [col1, col2, col3, col4, col5][i].metric(label, f"{val}/100")

                st.divider()
                st.write("**Key Web Vitals**")
                m_cols = st.columns(len(metrics))
                for i, (label, val) in enumerate(metrics.items()):
                    m_cols[i].metric(label, val)
            else:
                st.warning("⚠️ PageSpeed API unavailable. Add an API key in sidebar for speed metrics, or the site may be unreachable.")

        with tab4:
            if scores:
                df_scores = pd.DataFrame(list(scores.items()), columns=["Category", "Score"])
                fig = px.bar(df_scores, x="Category", y="Score", range_y=[0, 100],
                             color="Score", color_continuous_scale=["#ea4335", "#fbbc04", "#34a853"],
                             text="Score")
                fig.update_traces(textposition="outside")
                fig.update_layout(title="Lighthouse Category Scores (higher is better)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No speed scores available. The rest of the audit is still valid.")


# ============================================
# JOB 2: COMPETITOR INTELLIGENCE DASHBOARD
# ============================================
elif job_selection == "2️⃣ Competitor Intelligence Dashboard":
    st.header("⚔️ Competitor Intelligence Dashboard")
    st.caption("Compare up to 4 websites side-by-side on SEO, performance, and technical metrics. Clients pay $100-300 for this.")

    st.info("Enter your site + up to 3 competitors. Only domain name is fine (https:// is added automatically).")

    cols = st.columns(4)
    site_labels = ["Your Site", "Competitor 1", "Competitor 2", "Competitor 3"]
    site_inputs = {}
    for i, (col, label) in enumerate(zip(cols, site_labels)):
        with col:
            site_inputs[label] = st.text_input(label, placeholder="example.com")

    if st.button("Run Competitive Analysis", type="primary"):
        sites = {k: v for k, v in site_inputs.items() if v}
        if len(sites) < 2:
            st.error("Enter at least your site + 1 competitor.")
            st.stop()

        # Normalize URLs
        urls = {}
        for name, s in sites.items():
            if not s.startswith("http"):
                s = "https://" + s
            urls[name] = s

        progress_bar = st.progress(0, text="Fetching site data...")

        results = []
        for i, (name, url) in enumerate(urls.items()):
            progress_bar.progress((i) / len(urls), text=f"Analyzing {name}...")
            scores, metrics = cached_lighthouse(url)
            domain = urllib.parse.urlparse(url).netloc

            resp = cached_fetch(url, timeout=8)
            title = ""
            desc_found = False
            h1_count = 0
            if resp:
                s = BeautifulSoup(resp.text, "html.parser")
                title = s.title.string.strip()[:50] if s.title else ""
                meta_desc = s.find("meta", attrs={"name": "description"})
                desc_found = meta_desc is not None
                h1_count = len(s.find_all("h1"))

            row = {
                "Site": name,
                "Domain": domain,
                "Title Tag": title[:40] + "..." if len(title) > 40 else title,
                "Meta Desc": "✅" if desc_found else "❌",
                "H1 Tags": h1_count,
            }
            if scores:
                row.update({
                    "🏆 Performance": scores.get("performance", 0),
                    "🔍 SEO": scores.get("seo", 0),
                    "♿ Accessibility": scores.get("accessibility", 0),
                    "⚙️ Best Practices": scores.get("best-practices", 0),
                })
            results.append(row)

        progress_bar.progress(1.0, text="Done!")
        time.sleep(0.3)
        progress_bar.empt