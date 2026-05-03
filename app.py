import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import csv
import io

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_competitors(idea, location):
    prompt = f"""
    Business idea: {idea}
    Location: {location}
    Return 5-10 competitors in JSON format:
    [
        {{
            "name": "",
            "description": "",
            "reason": "",
            "threat_score": 0
        }}
    ]
    - threat_score is a number from 1 to 10 (10 = biggest threat)
    Only return the JSON, nothing else.
    """
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def get_market_gaps(idea, location, competitors):
    competitor_names = ", ".join([c["name"] for c in competitors])
    prompt = f"""
    Business idea: {idea}
    Location: {location}
    Current competitors: {competitor_names}

    Based on these competitors, identify market gaps and opportunities.
    Return in JSON format:
    {{
        "summary": "Brief overview of the competitive landscape",
        "gaps": [
            {{
                "opportunity": "",
                "explanation": ""
            }}
        ],
        "recommendation": "Your overall recommendation for how to position this business"
    }}
    You must return ONLY the raw JSON object. No markdown, no backticks, no explanation.
    """
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return clean

def convert_to_csv(competitors, gaps, idea, location):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Business Idea", idea])
    writer.writerow(["Location", location])
    writer.writerow([])

    writer.writerow(["COMPETITORS"])
    writer.writerow(["Rank", "Name", "Description", "Why They're a Threat", "Threat Score"])
    for i, comp in enumerate(competitors):
        writer.writerow([
            f"#{i+1}",
            comp["name"],
            comp["description"],
            comp["reason"],
            f"{comp['threat_score']}/10"
        ])

    writer.writerow([])
    writer.writerow(["MARKET GAP ANALYSIS"])
    writer.writerow(["Summary", gaps["summary"]])
    writer.writerow([])
    writer.writerow(["Opportunities"])
    writer.writerow(["#", "Opportunity", "Explanation"])
    for i, gap in enumerate(gaps["gaps"]):
        writer.writerow([f"#{i+1}", gap["opportunity"], gap["explanation"]])

    writer.writerow([])
    writer.writerow(["Recommendation", gaps["recommendation"]])

    return output.getvalue()

# Helper: color based on score
def threat_color(score):
    if score >= 8:
        return "🔴"
    elif score >= 5:
        return "🟡"
    else:
        return "🟢"

# Page config
st.set_page_config(page_title="Competitor Finder", page_icon="🔍", layout="centered")

# Header
st.title("🔍 Competitor Finder")
st.markdown("Discover who you're up against before you launch.")
st.divider()

# Inputs
col1, col2 = st.columns(2)
with col1:
    idea = st.text_area("💡 Your Business Idea", placeholder="e.g. Bubble tea shop")
with col2:
    location = st.text_input("📍 Location (optional)", placeholder="e.g. Surrey, BC")
    st.markdown(" ")
    search = st.button("Find Competitors 🚀", use_container_width=True)

st.divider()

# Run analysis and store in session state
if search:
    if not idea:
        st.warning("Please enter a business idea first!")
    else:
        with st.spinner("Analyzing competitors..."):
            result = get_competitors(idea, location)
            competitors = json.loads(result)
            competitors = sorted(competitors, key=lambda x: x["threat_score"], reverse=True)

        with st.spinner("Identifying market opportunities..."):
            gaps_result = get_market_gaps(idea, location, competitors)
            gaps = json.loads(gaps_result)

        # Save to session state
        st.session_state.competitors = competitors
        st.session_state.gaps = gaps
        st.session_state.idea = idea
        st.session_state.location = location

# Display results from session state
if "competitors" in st.session_state:
    competitors = st.session_state.competitors
    gaps = st.session_state.gaps
    idea = st.session_state.idea
    location = st.session_state.location

    st.success(f"Found {len(competitors)} competitors!")
    st.markdown(" ")

    st.markdown("## 🏆 Competitors")
    for i, comp in enumerate(competitors):
        score = comp["threat_score"]
        emoji = threat_color(score)
        with st.expander(f"{emoji} #{i+1} — {comp['name']} | Threat Score: {score}/10", expanded=True):
            st.progress(score / 10)
            st.markdown(f"**About:** {comp['description']}")
            st.info(f"⚠️ **Why they're a threat:** {comp['reason']}")

    st.divider()

    st.markdown("## 🌍 Market Gap Analysis")
    st.info(f"📊 **Landscape Summary:** {gaps['summary']}")
    st.markdown(" ")

    st.markdown("### 💡 Opportunities You Can Exploit")
    for i, gap in enumerate(gaps["gaps"]):
        with st.expander(f"Opportunity #{i+1} — {gap['opportunity']}", expanded=True):
            st.write(gap["explanation"])

    st.divider()
    st.success(f"✅ **Our Recommendation:** {gaps['recommendation']}")

    st.divider()

    st.markdown("## 📥 Export Results")
    csv_data = convert_to_csv(competitors, gaps, idea, location)
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv_data,
        file_name=f"competitor_analysis_{idea[:20].replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True
    )