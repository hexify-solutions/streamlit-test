if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

@st.cache_data
def load_data():
    # For local development
    try:
        df = pd.read_excel("SymptomBotDB.xlsx")
    except:
        # For Streamlit Cloud deployment
        excel_url = "https://github.com/emmsdan/streamlit-test/raw/refs/heads/main/SymptomBotDB.xlsx"
        df = pd.read_excel(excel_url)

#    df = pd.read_excel("SymptomBotDB.xlsx")
# ── Normalize every header: remove leading/trailing whitespace ──
    df.columns = df.columns.str.strip()
    return df

def login_page():
    st.title("LexAI Symptom Checker Login")

    # Create a form for login
    with st.form("login_form"):
        password = st.text_input("Enter Password", type="password")
        submit_button = st.form_submit_button("Login")

    # Check password
    if submit_button:
        if password == "lexmedical":
            st.session_state.logged_in = True
            st.session_state.page = "welcome"
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    # Optional: Add a forgot password hint (remove in production)
    st.caption("Hint: The password is 'LexTest123'")

