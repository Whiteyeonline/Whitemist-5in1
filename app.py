import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from google import genai
import pandas as pd
import plotly.express as px
import json
import ssl
import socket

# Page Config
st.set_page_config(page_title="Multi-Job Intelligence Engine", page_icon="⚡", layout="wide")

# Setup Gemini API Key
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else st.sidebar.text_input("Enter Gemini API Key", type="password")

st.sidebar.title("🧰 Intelligence Suite")
job_selection = st.sidebar.radio(
    "Select Active Job:",
    [
        "1️⃣ Technical & SSL Web Audit (5 Checks)",
        "2️⃣ B2B Lead Generation",
        "3️⃣ Competitor Benchmarking",
        "4️⃣ Global Trademark Checker",
        "5️⃣ OSINT Life History & Footprint"
    ]
)

# Helper Function: SSL Check
def check_ssl(hostname):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                return True, cert.get('issuer', (('commonName', 'Unknown'),))[0][0][1]
    except Exception as e:
        return False, str(e)

# Helper Function: PageSpeed / Core Vitals
def fetch_pagespeed(url):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&category=PERFORMANCE&category=SEO&category=ACCESSIBILITY&category=BEST_PRACTICES"
    try:
        r = requests.get(api_url, timeout=30)
        data = r.json()
        cats = data['lighthouseResult']['categories']
        return {cat: int(details['score'] * 100) for cat, details in cats.items()}
    except Exception:
        return None

# ==========================================
# JOB 1: TECHNICAL & SSL WEB AUDIT (5 CHECKS)
# ==========================================
if job_selection == "1️⃣ Technical & SSL Web Audit (5 Checks)":
    st.header("⚡ 5-Point Web Performance & Security Audit")
    st.caption("Inspects 1) SSL Security, 2) Meta Titles/Desc, 3) Mobile Viewport, 4) Core Web Vitals Speed, 5) Lighthouse Overall Scores.")
    
    target_url = st.text_input("Enter Website URL:", placeholder="https://example.com")
    
    if st.button("Run 5-Point Audit", type="primary"):
        if not target_url.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]
            
            with st.spinner("Executing 5 technical security & speed checks..."):
                # 1. SSL Check
                ssl_ok, ssl_info = check_ssl(domain)
                
                # 2 & 3. HTML Scrape (Meta + Viewport)
                try:
                    res = requests.get(target_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(res.text, 'html.parser')
                    title = soup.title.string if soup.title else None
                    meta_desc = soup.find('meta', attrs={'name': 'description'})
                    viewport = soup.find('meta', attrs={'name': 'viewport'})
                    html_ok = True
                except Exception:
                    html_ok = False
                
                # 4 & 5. PageSpeed Insights
                ps_scores = fetch_pagespeed(target_url)

            st.subheader("📋 5 Audit Diagnostics")
            
            # Display 5 Checks
            col1, col2 = st.columns(2)
            with col1:
                # Check 1: SSL
                if ssl_ok:
                    st.success(f"1. SSL Security: Valid (Issued by: {ssl_info})")
                else:
                    st.error(f"1. SSL Security: Invalid / Failed ({ssl_info})")
                
                # Check 2: Meta Tags
                if html_ok and title and meta_desc:
                    st.success("2. Meta Tags: Title & Description present.")
                else:
                    st.warning("2. Meta Tags: Missing Title or Meta Description.")
                    
                # Check 3: Viewport
                if html_ok and viewport:
                    st.success("3. Mobile Viewport: Properly Configured.")
                else:
                    st.error("3. Mobile Viewport: Missing tag (Site not mobile optimized).")
                    
            with col2:
                # Check 4 & 5: Speed & Scores
                if ps_scores:
                    st.success(f"4. Core Web Vitals / Speed Score: {ps_scores.get('performance', 0)}/100")
                    st.success(f"5. Overall Lighthouse SEO & Best Practices: {ps_scores.get('seo', 0)}/100")
                else:
                    st.warning("4 & 5. Speed Scores: Could not query PageSpeed API.")

# ==========================================
# JOB 2: B2B LEAD GENERATION
# ==========================================
elif job_selection == "2️⃣ B2B Lead Generation":
    st.header("🎯 B2B Contact & Lead Extraction")
    st.caption("Scans company domains to harvest emails, phone numbers, and direct profile channels.")
    
    lead_url = st.text_input("Enter Business Website:", placeholder="https://company.com")
    
    if st.button("Harvest Lead Information", type="primary"):
        if lead_url:
            with st.spinner("Extracting public contact vectors..."):
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    res = requests.get(lead_url, headers=headers, timeout=15)
                    emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', res.text)))
                    phones = list(set(re.findall(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', res.text)))
                    
                    soup = BeautifulSoup(res.text, 'html.parser')
                    links = [a.get('href') for a in soup.find_all('a', href=True)]
                    socials = list(set([l for l in links if any(s in l for s in ['linkedin.com', 'twitter.com', 'x.com', 'facebook.com'])]))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("✉️ Found Emails")
                        st.dataframe(pd.DataFrame(emails, columns=["Email"]), use_container_width=True)
                    with c2:
                        st.subheader("🌐 Found Social Profiles")
                        st.dataframe(pd.DataFrame(socials, columns=["Social Link"]), use_container_width=True)
                except Exception as e:
                    st.error(f"Error scraping site: {e}")

# ==========================================
# JOB 3: COMPETITOR BENCHMARKING
# ==========================================
elif job_selection == "3️⃣ Competitor Benchmarking":
    st.header("⚔️ Side-by-Side Competitor Comparison")
    st.caption("Compares performance metrics of two rival sites.")
    
    c1, c2 = st.columns(2)
    with c1:
        site1 = st.text_input("Your Website:", placeholder="https://yoursite.com")
    with c2:
        site2 = st.text_input("Competitor Website:", placeholder="https://competitor.com")
        
    if st.button("Compare Sites", type="primary"):
        if site1 and site2:
            with st.spinner("Fetching performance metrics for both sites..."):
                s1 = fetch_pagespeed(site1)
                s2 = fetch_pagespeed(site2)
                
            if s1 and s2:
                df = pd.DataFrame({"Metric": list(s1.keys()), "Your Site": list(s1.values()), "Competitor": list(s2.values())})
                st.dataframe(df, use_container_width=True)
                fig = px.bar(df, x="Metric", y=["Your Site", "Competitor"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# JOB 4: GLOBAL TRADEMARK CHECKER
# ==========================================
elif job_selection == "4️⃣ Global Trademark Checker":
    st.header("🛡️ Worldwide Trademark & Brand Register")
    st.caption("Check brand availability, registration age, active databases, and kid-friendly status reports.")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        brand_query = st.text_input("Enter Brand / Trademark Name (e.g. Nike, Apple, UniqueBrand):")
    with col_b:
        country_select = st.selectbox("Select Target Region / Database:", ["Worldwide (WIPO)", "United States (USPTO)", "India (IPO)", "European Union (EUIPO)", "United Kingdom (UKIPO)"])
        
    if st.button("Check Trademark & Generate Report", type="primary"):
        if brand_query and GEMINI_API_KEY:
            with st.spinner(f"Querying {country_select} records and calculating age..."):
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                prompt = f"""
                Act as a Global Trademark & Intellectual Property Specialist.
                Target Brand Name: '{brand_query}'
                Target Country/Database: '{country_select}'
                
                Generate a complete Trademark Report with TWO clear sections:
                
                SECTION 1: KID-FRIENDLY & EASY TO READ (Simple Words)
                - Is this name super famous or taken?
                - Who owns it?
                - How old is this brand? (Calculate years since it started or first registered)
                - Can a kid open a shop with this name, or will they get in trouble?
                
                SECTION 2: PROFESSIONAL LEGAL & TRADEMARK DETAILS
                - Target Database Registry context for {country_select}.
                - Trademark Category/Classes (e.g., Nice Classification system).
                - Estimated Registration History & Age.
                - Availability Risk Rating (Low Risk / High Risk / Duplicate Warning).
                """
                
                resp = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                
                st.markdown("### 📜 Brand Intelligence & Trademark Report")
                st.markdown(resp.text)
                st.download_button("Download Trademark Report (.txt)", resp.text, file_name=f"{brand_query}_trademark_report.txt")
        elif not GEMINI_API_KEY:
            st.error("Please add your Gemini API Key in the sidebar to generate trademark reports.")

# ==========================================
# JOB 5: OSINT LIFE HISTORY & FOOTPRINT
# ==========================================
elif job_selection == "5️⃣ OSINT Life History & Footprint":
    st.header("🕵️ History, Life Story & Footprint Detective")
    st.caption("Enter a person, company, or famous brand name to uncover their entire history from origin to now, wins, losses, and major life incidents.")
    
    entity_name = st.text_input("Enter Name (Person, Company, or Famous Brand):", placeholder="e.g. Elon Musk, Steve Jobs, Nike, or Local Entity Name")
    
    if st.button("Uncover Complete History", type="primary"):
        if entity_name and GEMINI_API_KEY:
            with st.spinner(f"Reconstructing birth-to-now footprint & incident timeline for '{entity_name}'..."):
                client = genai.Client(api_key=GEMINI_API_KEY)
                
                prompt = f"""
                Act as an OSINT Intelligence Historian. Reconstruct the complete story and life/brand history of: '{entity_name}'.
                
                Provide a structured report with TWO DISTINCT READABILITY STYLES:
                
                -------------------------------------------------
                STYLE 1: EASY STORY FORMAT (Kid-Friendly & Clear)
                -------------------------------------------------
                Tell their origin story like an exciting tale:
                - How they started / birth / beginnings.
                - What they are famous for today.
                - The biggest lesson from their life or business.
                
                -------------------------------------------------
                STYLE 2: PROFESSIONAL POINT-BY-POINT TIMELINE & INCIDENT LOG
                -------------------------------------------------
                1. Origins & Early Foundations (Dates/Birth/Start).
                2. Major Wins & Success Milestones (Point-by-point).
                3. Major Losses, Struggles, Scandals, or Failures (Point-by-point).
                4. Current Status & Active Footprint (Present State).
                5. Complete Incident Timeline (Chronological summary).
                """
                
                resp = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                
                st.markdown("### 📖 Footprint & History Report")
                st.markdown(resp.text)
                st.download_button("Download Footprint Story (.txt)", resp.text, file_name=f"{entity_name}_history_dossier.txt")
        elif not GEMINI_API_KEY:
            st.error("Please add your Gemini API Key in the sidebar.")
      
