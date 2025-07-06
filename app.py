import streamlit as st
import pandas as pd
from PIL import Image
from difflib import SequenceMatcher

st.set_page_config(page_title="LexAI Symptom Checker", page_icon="🩺", layout="centered")

# Initialize session state safely
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = "welcome"
if 'user_data' not in st.session_state:
    st.session_state.user_data = {}
if 'current_condition' not in st.session_state:
    st.session_state.current_condition = None
if 'confirmed_risks' not in st.session_state:
    st.session_state.confirmed_risks = []
if 'matched_conditions' not in st.session_state:
    st.session_state.matched_conditions = pd.DataFrame()

@st.cache_data
def load_data():
    # For local development
    try:
        return pd.read_excel("SymptomBotDB.xlsx")
    except:
        # For Streamlit Cloud deployment
        excel_url = "https://github.com/emmsdan/streamlit-test/raw/refs/heads/main/SymptomBotDB.xlsx"
        return pd.read_excel(excel_url)

def load_logo():
    return Image.open("logo.png")

db = load_data()
logo = load_logo()

# --- UTILITY FUNCTIONS ---
def is_gender_allowed(primary_category, gender, suppress_error=False):
    primary_category = primary_category.replace("’", "'")
    WOMEN_SPECIFIC = {
        "Women's Health", "Pelvic Inflammatory Disease", "Breast Lump",
        "Cervical Cancer", "Menopause", "Fibroids", "Heavy Menstrual Bleeding",
        "Yeast Infection", "Bacterial Vaginosis", "Endometriosis", "PCOS",
        "Pelvic Organ Prolapse", "Ovarian Cyst", "Ectopic Pregnancy"
    }
    MEN_SPECIFIC = {
        "Men's Health", "Prostatitis", "Testicular Torsion",
        "Benign Prostatic Hyperplasia", "Varicocele", "Balanitis"
    }
    if gender == "Male" and primary_category in WOMEN_SPECIFIC:
        if not suppress_error:
            st.error("This category is not available for your selected gender")
        return False
    if gender == "Female" and primary_category in MEN_SPECIFIC:
        if not suppress_error:
            st.error("This category is not available for your selected gender")
        return False
    return True

def display_grid(items, cols=3):
    rows = [items[i:i + cols] for i in range(0, len(items), cols)]
    for row in rows:
        columns = st.columns(len(row))
        for col, item in zip(columns, row):
            with col:
                if st.button(item, use_container_width=True):
                    return item
    return None

def generate_report():
    condition = st.session_state.current_condition
    user = st.session_state.user_data
    report = f"""
LEXAI SYMPTOM CHECKER REPORT
============================

Patient Details:
- Age: {user.get('age', 'N/A')}
- Gender: {user.get('gender', 'N/A')}

Assessment:
- Likely Condition: {condition['Condition'] if condition is not None else 'N/A'}
- Risk Factors: {', '.join(st.session_state.confirmed_risks) if st.session_state.confirmed_risks else 'None'}

Recommendation:
{condition['Escalated Recommendation' if st.session_state.get('is_high_risk') else 'Default Recommendation'] if condition is not None else ''}
"""
    return report

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def match_conditions_by_symptoms(input_text, db):
    input_symptoms = [sym.strip().lower() for sym in input_text.split(",") if sym.strip()]
    matched_conditions = []
    for _, row in db.iterrows():
        db_symptoms = [sym.lower().strip() for sym in str(row["Symptoms"]).split(",") if sym.strip()]
        for user_sym in input_symptoms:
            for db_sym in db_symptoms:
                if user_sym in db_sym or db_sym in user_sym or similarity(user_sym, db_sym) > 0.6:
                    matched_conditions.append(row)
                    break
            else:
                continue
            break
    return pd.DataFrame(matched_conditions).drop_duplicates()
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

def welcome_page():
    st.image(logo, width=120)
    st.markdown("<p style='font-size:18px;'>Hi 👋, I’m LexAI — here to help you make sense of your symptoms and feel more in control of your health.</p>", unsafe_allow_html=True)
    if st.button("Start Symptom Check", type="primary"):
        st.session_state.page = "user_info"
        st.rerun()

def user_info_page():
    st.image(logo, width=80)
    st.subheader("Before we begin, I’d like to know a little about you.")

    with st.form("user_info_form"):
        age = st.number_input("Age", min_value=18, max_value=120)
        gender = st.radio("Gender", ["Male", "Female"], horizontal=True)
        conditions = st.text_input("Existing conditions", placeholder="Mention any long-term health issues you live with (like asthma or none)")
        
        submit_col, _ = st.columns([1, 2])
        with submit_col:
            cont = st.form_submit_button("Continue →", type="primary")

    back_col, _ = st.columns([1, 2])
    with back_col:
        back = st.button("← Back")

    if back:
        st.session_state.page = "welcome"
        st.rerun()
    if cont:
        st.session_state.user_data['age'] = age
        st.session_state.user_data['gender'] = gender
        st.session_state.user_data['conditions'] = conditions
        st.session_state.page = "symptom_category"
        st.rerun()


def symptom_category_page():
    st.image(logo, width=80)
    st.subheader("Let’s start with what’s bothering you today")
    current_gender = st.session_state.user_data.get('gender')
    if not current_gender:
        st.error("Gender not selected. Please go back.")
        return
    valid_categories = [cat for cat in db["Primary Category"].unique() if is_gender_allowed(cat, current_gender, suppress_error=True)]
    selected = display_grid(valid_categories, cols=3)
    if selected and is_gender_allowed(selected, current_gender):
        st.session_state.user_data['primary_category'] = selected
        st.session_state.page = "symptom_subcategory"
        st.rerun()

    if st.button("Can’t find your symptoms? Enter them here"):
        st.session_state.page = "symptom_free_input"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "user_info"
        st.rerun()

def symptom_free_input_page():
    st.image(logo, width=80)
    st.subheader("What are your symptoms?")
    st.markdown("Please enter your symptoms separated by commas. For example: headache, fever, nausea")

    with st.form("symptom_input_form"):
        symptom_input = st.text_input("Enter symptoms here", placeholder="e.g., headache, fever, nausea")
        submit_col, _ = st.columns([3,1])
        with submit_col:
            submit = st.form_submit_button("Search Symptoms →")

    back_col, _ = st.columns([1,3])
    with back_col:
        back = st.button("← Back")

    if back:
        st.session_state.page = "symptom_category"
        st.rerun()
    if submit:
        if not symptom_input.strip():
            st.warning("Please enter at least one symptom to search.")
        else:
            st.session_state.user_data['free_symptoms'] = symptom_input
            st.session_state.page = "symptom_primary_category_freeinput"
            st.rerun()

def symptom_primary_category_freeinput_page():
    st.image(logo, width=80)
    st.subheader("Let’s find the right category for your symptoms.")

    symptom_input = st.session_state.user_data.get('free_symptoms', "")
    matched_conditions = match_conditions_by_symptoms(symptom_input, db)
    st.session_state.matched_conditions = matched_conditions  # Save for downstream filtering

    if matched_conditions.empty:
        st.warning("No matching primary categories found.")
        if st.button("Try Again"):
            st.session_state.page = "symptom_free_input"
            st.rerun()
        if st.button("Speak with a Doctor"):
            st.session_state.page = "fallback_page"
            st.rerun()
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    matched_primary_cats = matched_conditions["Primary Category"].unique().tolist()
    selected = display_grid(matched_primary_cats, cols=2)
    if selected:
        st.session_state.user_data['primary_category'] = selected
        st.session_state.page = "symptom_subcategory"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "symptom_free_input"
        st.rerun()

def symptom_subcategory_page():
    st.image(logo, width=80)
    st.subheader("Select a subcategory within your chosen primary category")

    primary_category = st.session_state.user_data.get('primary_category')
    if not primary_category:
        st.error("Primary category not selected. Please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    filtered = db[db["Primary Category"] == primary_category]
    subcategories = filtered["SubCategory"].unique()
    selected = display_grid(subcategories, cols=2)
    if selected:
        st.session_state.user_data['subcategory'] = selected
        st.session_state.current_condition = filtered[filtered["SubCategory"] == selected].iloc[0]
        st.session_state.page = "symptom_selection"
        st.rerun()

    if st.button("← Back"):
        st.session_state.page = "symptom_primary_category_freeinput"
        st.rerun()

def symptom_selection_page():
    st.image(logo, width=80)
    st.subheader("Tell me more about your symptoms")

    condition = st.session_state.current_condition
    if condition is None:
        st.error("Condition not selected. Please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    symptoms = [s.strip() for s in str(condition["Symptoms"]).split(",")] if pd.notna(condition["Symptoms"]) else []

    selected = st.multiselect("Select all that apply:", symptoms)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back"):
            st.session_state.page = "symptom_subcategory"
            st.rerun()
    with col2:
        if st.button("Continue →"):
            st.session_state.user_data['selected_symptoms'] = selected
            st.session_state.page = "clarifying_questions"
            st.rerun()

def clarifying_questions_page():
    st.image(logo, width=80)
    st.subheader("Before I continue, I’d like to understand a bit more about your symptoms")

    condition = st.session_state.current_condition
    if condition is None:
        st.error("Condition not selected. Please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    q1 = condition["Clarifying Questions 1"]
    q2 = condition["Clarifying Questions2"]

    with st.form("clarifying_form"):
        answers = {}
        if pd.notna(q1):
            answers['q1'] = st.radio(q1, ["Yes", "No"])
        if pd.notna(q2):
            answers['q2'] = st.radio(q2, ["Yes", "No"])
        col1, col2 = st.columns([1, 3])
        with col1:
            back = st.form_submit_button("← Back")
        with col2:
            cont = st.form_submit_button("Continue →")

    if back:
        st.session_state.page = "symptom_selection"
        st.rerun()
    if cont:
        st.session_state.user_data['clarifying_1'] = answers.get('q1')
        st.session_state.user_data['clarifying_2'] = answers.get('q2')

        if answers.get('q1') == "No" and answers.get('q2') == "No":
            st.session_state.page = "fallback_page"
        elif "Yes" in answers.values():
            st.session_state.page = "risk_flag_selection"
        else:
            st.session_state.page = "results"
        st.rerun()

def risk_flag_selection_page():
    st.image(logo, width=80)
    st.markdown("""
    <p style='font-size: 26px; margin-bottom: 8px;font-weight: 600;line-height: 1.2;'>
        Some factors can increase the significance of your symptoms. This information will also help guide better care.
        Below is a list of such risk factors, tailored to your profile. Select those that apply, or 'None' if none do
    </p>
    """, unsafe_allow_html=True)

    condition = st.session_state.current_condition
    risk_flags = [x.strip() for x in str(condition["RiskFlags"]).split(",") if x.strip()] if pd.notna(condition["RiskFlags"]) else []
    selected_risks = [flag for flag in risk_flags if st.checkbox(flag, key=f"risk_{flag}")]
    none_selected = st.checkbox("None / Not Applicable", key="no_risk", value=not bool(selected_risks))

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("← Back"):
            st.session_state.page = "clarifying_questions"
            st.rerun()
    with col2:
        if st.button("Continue →"):
            st.session_state.confirmed_risks = [] if none_selected else selected_risks
            st.session_state.page = "results"
            st.rerun()

def results_page():
    st.image(logo, width=80)
    st.subheader("Your Personalized Recommendation")

    condition = st.session_state.current_condition
    risks = st.session_state.get('confirmed_risks', [])
    clarifying_1 = st.session_state.user_data.get('clarifying_1')
    clarifying_2 = st.session_state.user_data.get('clarifying_2')
    has_risk = bool(risks)
    high_acuity = condition["Acuity Level"] == 3 if condition is not None else False

    if clarifying_1 == "No" and clarifying_2 == "No" and not has_risk:
        condition_title = "No Clear Match"
    else:
        condition_title = condition['Condition'] if condition is not None else "N/A"

    st.markdown(f"""
    <div style='margin-bottom: 20px;'>
        <p style='font-size: 16px;'><strong>Likely Condition:</strong></p>
        <p style='font-size: 18px; padding: 10px; background: #eefced; color: #0D5C0D; border-radius: 5px;'>
        {condition_title}
        </p>
    </div>
    """, unsafe_allow_html=True)

    if clarifying_1 == "Yes" or clarifying_2 == "Yes":
        if has_risk:
            st.session_state.is_high_risk = True
            st.markdown("**Based on my assessment and your pre-existing health status:**")
            st.info(condition["Escalated Recommendation"])
        else:
            st.session_state.is_high_risk = False
            st.markdown("**Based on my assessment, your likely condition is:**")
            st.success(condition["Default Recommendation"])
    elif clarifying_1 == "No" and clarifying_2 == "No" and not has_risk:
        st.session_state.is_high_risk = False
        st.warning("I couldn’t find a clear match for your symptoms, which could mean they’re mild or need professional evaluation.")

        if pd.notna(condition["Referral"]) if condition is not None else False:
            st.markdown(f"<div style='margin-top: 10px; background: #eefced; color: #0D5C0D; padding: 10px; border-radius: 5px;'>{condition['Referral']}</div>", unsafe_allow_html=True)
            st.button("📅 Schedule Appointment")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.download_button(
                label="📄 Download Full Report",
                data=generate_report(),
                file_name=f"lexai_report_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
        with col2:
            if st.button("🔄 Start New Check"):
                st.session_state.clear()
                st.rerun()

        return
    elif high_acuity:
        st.session_state.is_high_risk = True
        st.markdown("**Due to severity indicators:**")
        st.error(condition["Escalated Recommendation"])
    else:
        st.session_state.is_high_risk = False
        st.markdown("**General Advice:**")
        st.success(condition["Default Recommendation"])

    if pd.notna(condition["Referral"]) if condition is not None else False:
        st.markdown(f"<div style='margin-top: 20px; padding: 10px; background: #eefced; color: #0D5C0D; border-radius: 5px;'>{condition['Referral']}</div>", unsafe_allow_html=True)
        st.button("📅 Schedule Appointment")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button("📄 Download Full Report", generate_report(), file_name=f"lexai_report_{pd.Timestamp.now().strftime('%Y%m%d')}.txt", mime="text/plain")
    with col2:
        if st.button("🔄 Start New Check"):
            st.session_state.clear()
            st.rerun()

def fallback_page():
    st.image(logo, width=80)
    st.warning("I couldn’t find a clear match for your symptoms, which could mean they’re mild or need professional evaluation.")
    st.markdown("**Would you like to speak with a Doctor about this?**")
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("📅 Schedule an Appointment"):
            st.info("Appointment scheduling flow will be implemented here.")
    with col2:
        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
    with col3:
        if st.button("← Back"):
            st.session_state.page = "clarifying_questions"
            st.rerun()

PAGES = {
    "login": login_page,
    "welcome": welcome_page,
    "user_info": user_info_page,
    "symptom_category": symptom_category_page,
    "symptom_free_input": symptom_free_input_page,
    "symptom_primary_category_freeinput": symptom_primary_category_freeinput_page,
    "symptom_subcategory": symptom_subcategory_page,
    "symptom_selection": symptom_selection_page,
    "clarifying_questions": clarifying_questions_page,
    "risk_flag_selection": risk_flag_selection_page,
    "results": results_page,
    "fallback_page": fallback_page,
}

if not st.session_state.logged_in:
    login_page()
else:
    PAGES[st.session_state.page]()
