"""Run: .venv/Scripts/python.exe -m streamlit run app/ui.py --server.address 127.0.0.1"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pandas as pd
import streamlit as st

from app.cli import demo_assistant
from app.schemas import Entity
from app.settings import ROOT


st.set_page_config(page_title="East India Geo-Assistant", page_icon="🗺️", layout="wide")
st.markdown(
    """
    <style>
      :root {color-scheme: dark;}
      [data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#000;}
      .block-container {max-width: 1120px; min-height: calc(100vh - 2rem); padding-top: 5.25rem; padding-bottom: 7rem;}
      [data-testid="stSidebar"] {background:#080808; border-right:1px solid rgba(150,165,185,.13);}
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {line-height:1.55; color:#9aa9bd;}
      [data-testid="stSidebar"] h3 {font-size:1.02rem; letter-spacing:.02em;}
      .st-key-main_navigation {position:fixed; top:4rem; left:calc(50% + 150px); transform:translateX(-50%); z-index:10001; width:max-content;}
      [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][aria-expanded="false"]) .st-key-main_navigation {left:50%;}
      .st-key-main_navigation [data-testid="stRadioGroup"] {justify-content:center; gap:.1rem; padding:.22rem; border:1px solid #252525; border-radius:999px; background:#111; width:max-content; margin:0 auto; box-shadow:0 6px 28px rgba(0,0,0,.55);}
      .st-key-main_navigation [data-testid="stRadioOption"] {border:1px solid transparent; border-radius:999px; padding:0; background:transparent; transition:background .18s ease,border-color .18s ease;}
      .st-key-main_navigation [data-testid="stRadioOption"]:has(input:checked) {border-color:#303030; background:#242424;}
      .st-key-main_navigation [data-testid="stRadioOption"] > div > div:first-child {display:none !important;}
      .st-key-main_navigation [data-testid="stRadioOption"] > div {padding:.55rem 1.45rem;}
      [data-testid="stChatMessage"] {border:1px solid rgba(120,140,165,.15); border-radius:18px; padding:1rem 1.2rem; background:#101010;}
      [data-testid="stChatInput"] {border:1px solid #3a3a3a; border-radius:24px; background:#1b1b1b; box-shadow:0 0 0 1px rgba(130,170,255,.2),0 0 22px rgba(80,136,255,.16),0 8px 36px rgba(0,0,0,.35); transition:border-color .2s ease,box-shadow .2s ease;}
      [data-testid="stChatInput"]:focus-within {border-color:rgba(132,177,255,.9); box-shadow:0 0 0 1px rgba(112,162,255,.48),0 0 30px rgba(72,131,255,.3),0 8px 36px rgba(0,0,0,.4);}
      [data-testid="stChatInput"] textarea {background:transparent;}
      .welcome {max-width:820px; margin:clamp(4rem,15vh,10rem) auto 3rem; text-align:center;}
      .welcome .eyebrow {display:inline-block; padding:.5rem .9rem; border:1px solid rgba(126,225,177,.3); border-radius:999px; color:#9be5bf; background:rgba(53,119,91,.16); font-size:.9rem;}
      .welcome h1 {margin:1.8rem 0 .9rem; color:#f4f6fa; font-size:clamp(2.5rem,5.2vw,4.6rem); line-height:1.04; letter-spacing:-.045em; font-weight:600;}
      .welcome p {max-width:680px; margin:0 auto; color:#98a6ba; font-size:1.15rem; line-height:1.65;}
      .chat-intro {color:#8d9bb0; text-align:center; font-size:.86rem; margin-bottom:1.2rem;}
      .st-key-clear_chat button {border-radius:12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

_, nav_center, _ = st.columns([2, 3, 2])
with nav_center:
    section = st.radio(
        "Choose a workspace",
        ["School map", "Assistant"],
        horizontal=True,
        key="main_navigation",
        label_visibility="collapsed",
    )

with st.sidebar:
    st.markdown("### 🗺️ East India Geo-Assistant")
    st.caption("LOCAL EVIDENCE WORKSPACE")
    st.markdown("---")
    st.markdown("#### Workspace")
    st.caption("Use the switch above to move between the school map and assistant.")
    st.caption("Map locations come from the supplied GeoPackage. Assistant policies are synthetic demo content.")
    if st.session_state.get("chat_messages"):
        if st.button("＋  New conversation", key="clear_chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
if section == "School map":
    st.title("East India Geo-Assistant")
    st.caption("Local evidence explorer · school geography · transparent sources")
    st.subheader("School locations from the supplied GeoPackage")
    path = ROOT / "data/private/schools/entities.jsonl"
    if not path.exists():
        st.info("Import the supplied GeoPackage using the CLI command in README.md.")
        st.stop()

    @st.cache_data
    def schools(stamp):
        return [
            Entity.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    entities = schools(path.stat().st_mtime)
    a, b, c = st.columns(3)
    a.metric("School features", len(entities))
    b.metric("Named features", sum(not e.canonical_name.startswith("Unnamed school") for e in entities))
    c.metric("Source CRS", "EPSG:4326")

    query = st.text_input("Find a school by name or OSM ID", placeholder="Chinmaya, Railway, 130277882…")
    map_view = st.radio("Map view", ["School region", "All India"], horizontal=True)
    selected = [
        e for e in entities
        if query.casefold() in e.canonical_name.casefold() or query in (e.attributes.osm_id or "")
    ]
    frame = pd.DataFrame(
        [
            dict(name=e.canonical_name, osm_id=e.attributes.osm_id,
                 lat=e.attributes.location.lat, lon=e.attributes.location.lon)
            for e in selected
        ]
    )
    if len(frame):
        import pydeck as pdk

        countries = json.loads((ROOT / "app/assets/countries.geojson").read_text(encoding="utf-8"))
        for feature in countries["features"]:
            feature["properties"]["color"] = (
                [232, 239, 222] if feature["properties"]["ADMIN"] == "India" else [238, 238, 232]
            )
        land = pdk.Layer(
            "GeoJsonLayer", countries, filled=True, stroked=True,
            get_fill_color="properties.color", get_line_color=[149, 160, 156],
            line_width_min_pixels=1, pickable=False,
        )
        school_points = pdk.Layer(
            "ScatterplotLayer", frame, get_position="[lon, lat]",
            get_fill_color=[30, 116, 230, 210], get_line_color=[255, 255, 255],
            stroked=True, get_radius=800, radius_min_pixels=3, radius_max_pixels=8,
            line_width_min_pixels=0.5, pickable=True,
        )
        labels = [
            dict(name=f["properties"]["NAME"], lon=f["properties"]["LABEL_X"], lat=f["properties"]["LABEL_Y"])
            for f in countries["features"]
            if f["properties"]["ADMIN"] in ["India", "Nepal", "Bhutan", "Bangladesh", "Pakistan", "Myanmar", "Sri Lanka", "China"]
        ]
        names = pdk.Layer(
            "TextLayer", labels, get_position="[lon, lat]", get_text="name", get_size=14,
            get_color=[76, 86, 78], get_text_anchor="middle", get_alignment_baseline="center",
            pickable=False,
        )
        if query and len(frame) < 20:
            view = pdk.ViewState(latitude=float(frame.lat.mean()), longitude=float(frame.lon.mean()), zoom=7)
        elif map_view == "All India":
            view = pdk.ViewState(latitude=22, longitude=80, zoom=3.5)
        else:
            view = pdk.ViewState(latitude=23, longitude=86, zoom=5)
        deck = pdk.Deck(
            layers=[land, names, school_points], initial_view_state=view,
            map_provider=None, map_style=None,
            views=[pdk.View(type="MapView", controller=True)],
            parameters={"clearColor": [0.89, 0.95, 0.98, 1]},
            tooltip={"text": "{name}\nOSM ID: {osm_id}\nLatitude: {lat}\nLongitude: {lon}"},
        )
        st.pydeck_chart(deck, height=560, use_container_width=True)
        st.dataframe(frame, use_container_width=True, hide_index=True)
    else:
        st.info("No matching school in the supplied data.")
    st.caption(
        "Blue points show school building locations from the supplied data. Drag to pan, scroll to zoom, "
        "and hover for details. Points are representative positions inside source polygons, not verified entrances. "
        "Board, seats and cut-off marks were not supplied."
    )

else:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    location_data_ready = (ROOT / 'data/private/schools/entities.jsonl').exists()
    location_note = (
        'real school locations from the imported GeoPackage'
        if location_data_ready
        else 'school locations are unavailable until you import schools.gpkg'
    )
    st.markdown(
        f'<div class="chat-intro">{location_note} · admissions policies are synthetic demo content</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_messages:
        st.markdown(
            '<section class="welcome"><span class="eyebrow">✦  East India Geo-Assistant</span>'
            '<h1>What would you like to explore today?</h1>'
            '<p>Ask about the demo corpus, inspect school locations, and follow the evidence through each response.</p>'
            '</section>',
            unsafe_allow_html=True,
        )

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                st.caption("Confidence: uncalibrated demo (JSON sentinel 0).")
                if message.get("reason"):
                    st.info(message["reason"])
                for citation in message.get("citations", []):
                    with st.expander(f"Source: {citation['source']} · {citation['chunk_id']}"):
                        st.text(citation["excerpt"])
                        st.json(citation)
                if message.get("trace"):
                    with st.expander("Entities, graph paths and settings"):
                        st.json(message["trace"])

    prompt = st.chat_input("Ask a question or follow up…")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        try:
            answer, trace = demo_assistant().answer(prompt)
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": answer.answer,
                    "citations": [citation.model_dump(mode="json") for citation in answer.citations],
                    "reason": trace.get("reason"),
                    "trace": trace,
                }
            )
        except Exception as exc:
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": f"I couldn't process that question: {type(exc).__name__}. Please try again."}
            )
        st.rerun()
