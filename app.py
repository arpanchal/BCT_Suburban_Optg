import streamlit as st

st.set_page_config(
    page_title="Mumbai Suburban Railway — Operations Portal",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "role" not in st.session_state:
    st.session_state.role = None

def login():
    st.title("🚆 Mumbai Suburban Railway — Login")
    st.markdown("Please log in to continue.")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log In")
        
        if submit:
            if username == "admin" and password == "admin123":
                st.session_state.role = "admin"
                st.rerun()
            elif username == "user" and password == "user123":
                st.session_state.role = "user"
                st.rerun()
            else:
                st.error("Invalid username or password")

def logout():
    st.title("Log out")
    if st.button("Log out currently active session?"):
        st.session_state.role = None
        st.rerun()

# --- Auth Check ---
if st.session_state.role is None:
    pg = st.navigation([st.Page(login, title="Log In", icon="🔐")])
    pg.run()
    st.stop()


# --- Build Authenticated Navigation ---
home_page = st.Page("pages/Home.py", title="Home Dashboard", icon="🏠", default=True)

vis_pages = [
    st.Page("pages/1_Marey_Chart.py", title="Marey Chart", icon="🗺️"),
    st.Page("pages/2_Headway_Chart.py", title="Headway Chart", icon="📏"),
    st.Page("pages/3_Train_Count.py", title="Train Count by Hour", icon="📈"),
    st.Page("pages/A_Line_Capacity.py", title="Line Capacity", icon="🚦"),
    st.Page("pages/D_Rake_Link.py", title="Rake Link", icon="🚃"),
]

lookup_pages = [
    st.Page("pages/4_Next_Train.py", title="Next Train from Station", icon="⏱️"),
    st.Page("pages/5_Set_Working.py", title="Set Working Sheet", icon="🔧"),
    st.Page("pages/6_Reversal_Summary.py", title="Reversal Summary", icon="🔄"),
    st.Page("pages/7_Halt_Durations.py", title="Halt Durations (KLV/PLG/BOR/VGN)", icon="⏸️"),
    st.Page("pages/C_Path_Finder.py", title="Path Finder", icon="🛤️"),
]

print_pages = [
    st.Page("pages/8_Station_Timetable.py", title="Station Timetable Cards", icon="📋"),
    st.Page("pages/9_Print_Marey.py", title="Print Marey Chart (PDF)", icon="🖨️"),
]    

pages = {
    "": [home_page],
    "📊 Visualisation": vis_pages,
    "🔍 Lookup Tools": lookup_pages,
    "🖨️ Print & Export": print_pages,
}

if st.session_state.role == "admin":
    admin_pages = [
        st.Page("pages/0_Regenerate_Data.py", title="Regenerate Data", icon="🔄"),
        st.Page("pages/B_Train_Category_Editor.py", title="Train Category Editor", icon="✏️"),
    ]
    pages["⚙️ Admin Tools"] = admin_pages

pages["Account"] = [st.Page(logout, title="Log out", icon="👋")]

pg = st.navigation(pages)

with st.sidebar:
    st.markdown("---")
    st.markdown(f"**Logged in as:** `{st.session_state.role}`")

pg.run()
