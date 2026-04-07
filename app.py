import streamlit as st

st.set_page_config(
    page_title="Mumbai Suburban Railway — Operations Portal",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🚆 Mumbai Suburban Railway — Operations Portal")
st.markdown("**26 March Working Timetable · 1315 Services · 37 Stations**")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📊 Visualisation")
    st.page_link("pages/1_Marey_Chart.py",       label="🗺️ Marey Chart (Station × Time)",     icon="🗺️")
    st.page_link("pages/2_Headway_Chart.py",      label="📏 Headway Chart",                    icon="📏")
    st.page_link("pages/3_Train_Count.py",        label="📈 Train Count by Hour",              icon="📈")

with col2:
    st.markdown("### 🔍 Lookup Tools")
    st.page_link("pages/4_Next_Train.py",         label="⏱️ Next Train from Station",          icon="⏱️")
    st.page_link("pages/5_Set_Working.py",        label="🔧 Set Working Sheet",                icon="🔧")
    st.page_link("pages/6_Reversal_Summary.py",   label="🔄 Reversal Summary",                 icon="🔄")
    st.page_link("pages/7_Halt_Durations.py",     label="⏸️ Halt Durations (KLV/PLG/BOR/VGN)",icon="⏸️")

with col3:
    st.markdown("### 🖨️ Print & Export")
    st.page_link("pages/8_Station_Timetable.py",  label="📋 Station Timetable Cards",          icon="📋")
    st.page_link("pages/9_Print_Marey.py",        label="🖨️ Print Marey Chart (PDF)",         icon="🖨️")

st.markdown("---")
st.info(
    "**How to use:** Select a tool from the sidebar or click a link above. "
    "All charts support filtering by direction (UP/DOWN), train type (SLOW/FAST), and time window."
)
