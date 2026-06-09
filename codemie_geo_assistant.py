import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# --- Fix suggestions, benefits, and effort mapping ---
FIXES = {
    "Crawlability": (
        "Ensure main content is accessible without login or forms. Check robots.txt and meta robots tags.",
        "High",
        "Low"
    ),
    "HTML Availability": (
        "Ensure key content is present in server-rendered HTML, not just JavaScript.",
        "High",
        "Medium"
    ),
    "Structured Data": (
        "Add and validate Schema.org markup for main entities.",
        "High",
        "Medium"
    ),
    "Page Performance": (
        "Optimize images, enable compression, and minimize scripts.",
        "High",
        "Low"
    ),
    "URL Discoverability": (
        "Use clean URLs, provide XML sitemap, and maintain proper internal linking.",
        "Medium",
        "Low"
    ),
    "Content Chunking": (
        "Use clear headings, sections, lists, and FAQs.",
        "Medium",
        "Low"
    ),
    "Entity Clarity": (
        "Clearly identify brands, products, people, and places.",
        "Medium",
        "Low"
    ),
    "Citation Signals": (
        "Add visible sources, references, statistics, and authorship.",
        "Medium",
        "Low"
    ),
    "Freshness Signals": (
        "Expose publish/update dates in HTML.",
        "Medium",
        "Low"
    ),
    "AI Accessibility": (
        "Avoid hiding important content in tabs, modals, or infinite scroll.",
        "Medium",
        "Medium"
    ),
}

# --- Analysis functions for each criterion ---
def check_crawlability(html):
    soup = BeautifulSoup(html, 'html.parser')
    meta = soup.find('meta', attrs={'name': 'robots'})
    if meta and 'noindex' in meta.get('content', '').lower():
        return 2
    return 5

def check_html_availability(html):
    soup = BeautifulSoup(html, 'html.parser')
    if soup.find('article') or soup.find('main'):
        return 5
    return 3

def check_structured_data(html):
    soup = BeautifulSoup(html, 'html.parser')
    jsonld = soup.find('script', type='application/ld+json')
    if jsonld:
        return 5
    return 2

def check_page_performance(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.elapsed.total_seconds() < 1.5:
            return 5
        elif resp.elapsed.total_seconds() < 3:
            return 3
        else:
            return 2
    except Exception:
        return 1

def check_url_discoverability(html):
    if re.search(r'/sitemap\.xml', html):
        return 5
    return 3

def check_content_chunking(html):
    soup = BeautifulSoup(html, 'html.parser')
    headings = soup.find_all(re.compile('^h[1-6]$'))
    lists = soup.find_all(['ul', 'ol'])
    if len(headings) > 3 and len(lists) > 1:
        return 5
    return 3

def check_entity_clarity(html):
    if re.search(r'brand|product|company|person|place', html, re.IGNORECASE):
        return 5
    return 3

def check_citation_signals(html):
    if re.search(r'reference|source|author|statistic', html, re.IGNORECASE):
        return 5
    return 2

def check_freshness_signals(html):
    if re.search(r'\d{4}-\d{2}-\d{2}', html) or re.search(r'Published|Updated', html, re.IGNORECASE):
        return 5
    return 2

def check_ai_accessibility(html):
    if re.search(r'tab|modal|accordion|infinite', html, re.IGNORECASE):
        return 3
    return 5

def analyze_site(url):
    try:
        resp = requests.get(url, timeout=10)
        html = resp.text
    except Exception as e:
        return None, f"Error fetching site: {e}"

    scores = {
        "Crawlability": check_crawlability(html),
        "HTML Availability": check_html_availability(html),
        "Structured Data": check_structured_data(html),
        "Page Performance": check_page_performance(url),
        "URL Discoverability": check_url_discoverability(html),
        "Content Chunking": check_content_chunking(html),
        "Entity Clarity": check_entity_clarity(html),
        "Citation Signals": check_citation_signals(html),
        "Freshness Signals": check_freshness_signals(html),
        "AI Accessibility": check_ai_accessibility(html),
    }
    return scores, None

def generate_roadmap(scores):
    roadmap = []
    for criterion, score in scores.items():
        if score < 4:
            suggestion, benefit, effort = FIXES.get(criterion, ("TBD", "Medium", "Medium"))
            roadmap.append({
                "criterion": criterion,
                "suggestion": suggestion,
                "benefit": benefit,
                "effort": effort
            })
    return roadmap

# --- Streamlit UI ---
st.title("🤖 CodeMie GEO Readiness Assistant")
st.write("Analyze a website's GEO readiness and get a prioritized fix roadmap.")

url = st.text_input("Enter a URL to analyze (include http:// or https://):")

if st.button("Analyze"):
    if not url:
        st.warning("Please enter a valid URL.")
    else:
        with st.spinner("Analyzing..."):
            scores, error = analyze_site(url)
        if error:
            st.error(error)
        elif not scores:
            st.error("Analysis failed.")
        else:
            st.success("Analysis complete!")
            st.subheader("GEO Readiness Scores")
            overall = sum(scores.values()) / len(scores)
            st.write(f"**Overall GEO Readiness Score:** {overall:.2f} / 5")
            st.table({k: f"{v}/5" for k, v in scores.items()})

            roadmap = generate_roadmap(scores)
            if roadmap:
                st.subheader("Top Fixes Roadmap")
                for fix in roadmap:
                    st.markdown(
                        f"- **{fix['criterion']}**: {fix['suggestion']}  \n"
                        f"  _Benefit: {fix['benefit']}, Effort: {fix['effort']}_"
                    )
            else:
                st.info("No major issues found! 🎉")

st.caption("Powered by CodeMie. Expand and customize as you wish!")