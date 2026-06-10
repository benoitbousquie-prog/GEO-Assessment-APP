import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import plotly.graph_objs as go

st.set_page_config(page_title="CodeMie GEO Competitor Benchmark", layout="wide")

# --- Full enterprise FIXES + scoring from code.py ---

FIXES = {
    "Crawlability": (
        "Ensure critical informational content is directly accessible by automated agents—resolve meta robots gatekeeping and avoid login/form gated flows.",
        "High",
        "Low",
        "Phase 2: URL Tree Clean-up"
    ),
    "HTML Availability": (
        "Migrate dynamic JavaScript-injected descriptions to static server-side HTML for guaranteed context discovery.",
        "High",
        "High",
        "Phase 3: SSR Data Injection & Container Adjustments"
    ),
    "Structured Data": (
        "Implement and validate comprehensive Schema.org markup covering brand, product, and FAQ content.",
        "High",
        "Medium",
        "Phase 3: SSR Data Injection & Container Adjustments"
    ),
    "Page Performance": (
        "Optimize critical resources (images, fonts, scripts); enable HTTP compression and lean delivery for sub-1.5s first byte.",
        "High",
        "Low",
        "Phase 2: URL Tree Clean-up"
    ),
    "URL Discoverability": (
        "Clean internal URLs by removing dynamic parameters (e.g., utm_, source=, id=); verify global XML sitemap and canonical tags.",
        "High",
        "Low",
        "Phase 2: URL Tree Clean-up"
    ),
    "Content Chunking": (
        "Structure typography using strict hierarchical header trees (H1 > H2 > H3); break body copy into lists, tables, and semantic sections.",
        "High",
        "Low",
        "Phase 1: Text Segmentation"
    ),
    "Entity Clarity": (
        "Explicitly disambiguate brands, products, and people with visible labels and context for easy LLM attribution.",
        "Medium",
        "Low",
        "Phase 1: Text Segmentation"
    ),
    "Citation Signals": (
        "Embed structured author, source, reference, and statistical attributions into base HTML with visible markup.",
        "Medium",
        "Low",
        "Phase 1: Text Segmentation"
    ),
    "Freshness Signals": (
        "Expose publish and update dates as machine-readable HTML for accurate recency scoring.",
        "Medium",
        "Low",
        "Phase 1: Text Segmentation"
    ),
    "AI Accessibility": (
        "Extract tab, modal, and dynamically hidden content into main document source; avoid ARIA or data attributes that obscure copy.",
        "High",
        "Medium",
        "Phase 3: SSR Data Injection & Container Adjustments"
    ),
}

def check_crawlability(html):
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "robots"})
    if meta and 'noindex' in (meta.get("content") or "").lower():
        return 2
    forms = soup.find_all("form")
    if forms and len(soup.get_text(strip=True)) < 400:
        return 2
    return 5

def check_html_availability(html):
    soup = BeautifulSoup(html, "html.parser")
    article_like = soup.find("article") or soup.find("main")
    p_tags = soup.find_all("p")
    first_paragraphs = " ".join(p.get_text() for p in p_tags[:2])
    large_divs = soup.find_all('div', attrs={"class": re.compile("container|content|main|app", re.I)})
    sparse = [
        div for div in large_divs
        if len(div.get_text(strip=True)) < 60 and len(div.find_all("p")) < 2
    ]
    if not article_like or len(p_tags) < 2 or len(first_paragraphs) < 50 or sparse:
        return 3
    return 5

def check_structured_data(html):
    soup = BeautifulSoup(html, "html.parser")
    jsonld = soup.find("script", type="application/ld+json")
    meta_schema = soup.find("meta", attrs={"itemtype": True})
    if jsonld or meta_schema:
        return 5
    return 2

def check_page_performance(url):
    try:
        resp = requests.get(url, timeout=6)
        t = resp.elapsed.total_seconds()
        if t < 1.5:
            return 5
        elif t < 3.0:
            return 3
        else:
            return 2
    except Exception:
        return 1

def check_url_discoverability(html, url):
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.find("link", rel="canonical")
    clean_canonical = canonical and canonical.get("href") and not re.search(r"[?&](utm_|source=|id=)", canonical.get("href"))
    messy_params = re.search(r"[?&](utm_|source=|id=)", url)
    sitemap_linked = "/sitemap.xml" in html or soup.find("a", href=re.compile("sitemap\\.(xml|html)"))
    if clean_canonical and not messy_params and sitemap_linked:
        return 5
    elif canonical and not messy_params:
        return 4
    elif messy_params:
        return 2
    else:
        return 3

def check_content_chunking(html):
    soup = BeautifulSoup(html, "html.parser")
    headings = [h.name for h in soup.find_all(re.compile("^h[1-6]$"))]
    hierarchy = "".join(headings)
    has_h1 = "h1" in hierarchy
    has_sequential = re.search(r"h1.*h2.*h3", hierarchy)
    lengthy_section_blocks = any(len(s.get_text(strip=True)) > 300 for s in soup.find_all(["section", "main", "article"]))
    lists = soup.find_all(['ul', 'ol'])
    heading_balance = has_h1 and (len([h for h in headings if h == "h2"]) >= 1)
    flat_layout = not has_sequential or lengthy_section_blocks
    if has_h1 and heading_balance and len(lists) > 1 and not flat_layout:
        return 5
    elif has_h1 and (len(lists) >= 1 or has_sequential):
        return 4
    else:
        return 3

def check_entity_clarity(html):
    if re.search(r'brand|product|company|[A-Z][a-z]+ [A-Z][a-z]+', html):
        return 5
    return 3

def check_citation_signals(html):
    soup = BeautifulSoup(html, "html.parser")
    found = any([
        re.search(r'reference|source|statistic|autho', html, re.I),
        soup.find("cite"), soup.find("footer"),
        soup.find("span", attrs={"class": re.compile("author|source", re.I)}),
    ])
    return 5 if found else 2

def check_freshness_signals(html):
    soup = BeautifulSoup(html, "html.parser")
    date_meta = soup.find("meta", attrs={"property": re.compile("date|modified|updated", re.I)})
    pub = re.search(r"\b20\d\d[-/]\d{2}[-/]\d{2}\b", html)
    upd = re.search(r"Published|Updated|Last Modified", html, re.I)
    return 5 if date_meta or pub or upd else 2

def check_ai_accessibility(html):
    soup = BeautifulSoup(html, "html.parser")
    interactive_attrs = any([
        soup.find(attrs={"aria-expanded": "false"}),
        soup.find(attrs={"aria-hidden": "true"}),
        soup.find(attrs={"style": re.compile("display:\s*none")}),
        soup.find(attrs={"data-bs-toggle": re.compile("modal|collapse|tab", re.I)}),
        soup.find(id=re.compile("tabpanel|tab-content|modal|collapse", re.I)),
    ])
    infinite = soup.find_all(string=re.compile("infinite", re.I))
    if interactive_attrs or infinite:
        return 3
    return 5

def analyze_site(url):
    try:
        resp = requests.get(url, timeout=14)
        html = resp.text
    except Exception as e:
        return None, f"Error fetching site: {e}"
    scores = {
        "Crawlability": check_crawlability(html),
        "HTML Availability": check_html_availability(html),
        "Structured Data": check_structured_data(html),
        "Page Performance": check_page_performance(url),
        "URL Discoverability": check_url_discoverability(html, url),
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
            suggestion, benefit, effort, phase = FIXES.get(criterion, ("TBD", "Medium", "Medium", "Phase 2: URL Tree Clean-up"))
            roadmap.append({
                "criterion": criterion,
                "suggestion": suggestion,
                "benefit": benefit,
                "effort": effort,
                "phase": phase
            })
    return roadmap

def prioritize_roadmap(roadmap):
    quick = []
    strat = []
    minor = []
    for item in roadmap:
        if item["benefit"] == "High" and item["effort"] == "Low":
            quick.append(item)
        elif item["benefit"] == "High":
            strat.append(item)
        else:
            minor.append(item)
    return quick, strat, minor

def phase_group_roadmap(roadmap):
    groups = {}
    for item in roadmap:
        phase = item["phase"]
        groups.setdefault(phase, []).append(item)
    phase_order = sorted(groups.items(), key=lambda x: x[0])
    return phase_order

# --- Streamlit UI for multi-site competitor comparison ---

st.title("✨ CodeMie GEO Multi-Site Competitor Benchmark")
st.write("Benchmark up to 5 domains side-by-side, with full business/effort roadmap for each.")

with st.form("multisite_geo"):
    main_url = st.text_input("Main site URL", value="https://www.marionnaud.fr")
    cols = st.columns(4)
    comp_urls = []
    comp_defaults = ["https://www.sephora.fr", "https://www.nocibe.fr", "", ""]
    for i in range(4):
        with cols[i]:
            comp_urls.append(st.text_input(f"Competitor {i+1}", value=comp_defaults[i]))
    do_bench = st.form_submit_button("Run Benchmark")

if do_bench:
    urls = [main_url] + [u for u in comp_urls if u.strip()]
    short_domains = [re.sub(r'https?://(www\.)?', '', url).split('/')[0] for url in urls]

    all_scores, all_errors = {}, {}
    for url, label in zip(urls, short_domains):
        with st.spinner(f"Analyzing {label}..."):
            scores, error = analyze_site(url)
        all_scores[label] = scores
        all_errors[label] = error

    crits = list(next(iter(all_scores.values())).keys())
    # GEO Criteria Table
    scoretable = {"Criterion": crits}
    for d in short_domains:
        scoretable[d] = [all_scores[d][k] if all_scores[d] else None for k in crits]
    st.dataframe(scoretable, use_container_width=True)

    # Radar/Spider chart
    st.markdown("### 🕸️ GEO Spider Chart")
    radar_fig = go.Figure()
    for d in short_domains:
        vals = [all_scores[d][k] if all_scores[d] and all_scores[d][k] else 1 for k in crits]
        vals += [vals[0]]
        radar_fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=crits + [crits[0]],
            fill='toself',
            name=d
        ))
    radar_fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[1, 5])),
        legend_title_text="Site",
        legend_orientation="h"
    )
    st.plotly_chart(radar_fig, use_container_width=True)

    for d in short_domains:
        st.markdown(f"---\n## 🏷️ {d} Diagnostic & Roadmap")
        if all_errors[d]:
            st.error(all_errors[d])
            continue
        scores = all_scores[d]
        overall = round(sum(scores.values())/len(scores),2)
        tag = (
            '<span class="status-tag-success">Optimal</span>' if overall >= 4.4
            else '<span class="status-tag-warning">Action Required</span>'
        )
        st.markdown(
            f'<div class="score-banner">'
            f'Overall GEO Readiness Score: <br/>{overall:.2f} <span style="font-size:1.7rem;">/ 5.00</span>'
            f' {tag} '
            f'</div>',
            unsafe_allow_html=True,
        )

        # Pillars/vulnerabilities
        pillars = {k: v for k, v in scores.items() if v >= 4}
        critical = {k: v for k, v in scores.items() if v < 4}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏆 Strong Pillars")
            for k, v in pillars.items():
                st.markdown(
                    f'<div class="pillar-block"><b>{k}</b>'
                    f'<span class="pillar-score">{v}/5</span></div>',
                    unsafe_allow_html=True,
                )
        with c2:
            st.markdown("#### 🔧 Vulnerabilities")
            for k, v in critical.items():
                st.markdown(
                    f'<div class="critical-block"><b>{k}</b>'
                    f'<span class="critical-score">{v}/5</span></div>',
                    unsafe_allow_html=True,
                )

        # Roadmap
        roadmap = generate_roadmap(scores)
        if roadmap:
            st.markdown("#### 📈 Prioritization Matrix: Business Value vs Effort")
            quick, strat, minor = prioritize_roadmap(roadmap)
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown('<div class="matrix-title">Quick Wins</div>', unsafe_allow_html=True)
                for r in quick:
                    st.markdown(f"- **{r['criterion']}**: {r['suggestion']} (_{r['benefit']}, Effort: {r['effort']}_)")
            with m2:
                st.markdown('<div class="matrix-title">Strategic</div>', unsafe_allow_html=True)
                for r in strat:
                    st.markdown(f"- **{r['criterion']}**: {r['suggestion']} (_{r['benefit']}, Effort: {r['effort']}_)")
            with m3:
                st.markdown('<div class="matrix-title">Minor Adjustments</div>', unsafe_allow_html=True)
                for r in minor:
                    st.markdown(f"- **{r['criterion']}**: {r['suggestion']} (_{r['benefit']}, Effort: {r['effort']}_)")
            st.markdown("#### 🛠️ Phase-Based Implementation Roadmap")
            phase_groups = phase_group_roadmap(roadmap)
            for phase, items in phase_groups:
                st.markdown(f'<span class="action-phase-title">{phase}</span>', unsafe_allow_html=True)
                for r in items:
                    st.markdown(
                        f"- **{r['criterion']}**: {r['suggestion']} (_Benefit: {r['benefit']}, Effort: {r['effort']}_)"
                    )
        else:
            st.info("No critical architecture vulnerabilities found!")

st.caption("Each site fetched, analyzed, and scored independently. No state or HTML reuse. Business matrix and roadmap powered by CodeMie GEO Enterprise.")
            st.caption("Diagnostics and strategic roadmap driven by CodeMie GEO Enterprise Framework. Report UI harmonized with enterprise HTML dashboard standards.")
