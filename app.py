import streamlit as st
import pandas as pd
from PIL import Image
import re
from difflib import SequenceMatcher
import os

LOG_PATH = "failure_log.csv"  # wherever you’re logging failures

def analytics_page():
    st.header("📊 App Failure Report")
    if not os.path.isfile(LOG_PATH):
        st.info("No failures logged yet.")
        return

    df = pd.read_csv(LOG_PATH, parse_dates=["timestamp"])
    st.subheader("Recent Failures")
    st.dataframe(df.sort_values("timestamp", ascending=False).head(20))

    st.subheader("Failures by Reason")
    counts = df["reason"].value_counts().reset_index()
    counts.columns = ["Reason","Count"]
    st.table(counts)

def stem(word: str) -> str:
    w = word.lower().strip()
    for suf in ("ing", "ion", "ed", "s", "ness", "able"):
        if w.endswith(suf):
            return w[: -len(suf)]
    return w

st.set_page_config(page_title="LEXY... LexMedical AI Triage System", page_icon="🩺", layout="centered")

# Initialize session state safely
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'free_input_mode' not in st.session_state:
    st.session_state.free_input_mode = False
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
        df = pd.read_excel("SymptomBotDB.xlsx")
    except:
        # For Streamlit Cloud deployment
        excel_url = "https://github.com/emmsdan/streamlit-test/raw/refs/heads/main/SymptomBotDB.xlsx"
        df = pd.read_excel(excel_url)

#    df = pd.read_excel("SymptomBotDB.xlsx")
    # ── Normalize every header: remove leading/trailing whitespace ──
    df.columns = df.columns.str.strip()
    return df


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
                if user_sym in db_sym or db_sym in user_sym or similarity(user_sym, db_sym) >= 0.65:
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
    st.markdown(
        "<p style='font-size:18px;'>Hi 👋, I’m Lexy — here to help you make sense of your symptoms and feel more in control of your health.</p>",
        unsafe_allow_html=True
    )
    if st.button("Start Symptom Check", type="primary"):
        st.session_state.page = "user_info"
        st.rerun()

    st.caption(
        """
        **Lexy** is an AI Triage tool that helps users better understand their symptoms and suggests next steps—whether that’s self-care, seeing a provider, or seeking urgent help.  
        It does not offer medical diagnoses and is not a substitute for care from a qualified health professional.  
        This tool is not recommended for children under 16, pregnant individuals, or those with multiple health conditions.  

        **In case of emergency**—such as chest pain, severe bleeding, or difficulty breathing—please call emergency services or go to the nearest hospital.
        """
    )

    # ── Hidden Admin Access (testing only) ──
    pwd = st.sidebar.text_input("Dev code", type="password")
    if pwd == "Akinola":  # ← replace with your own secret
        if st.sidebar.button("View Analytics"):
            st.session_state.page = "analytics"
            st.rerun()

def user_info_page():
    st.image(logo, width=80)
    st.subheader("Before we begin, I’d like to know a little about you.")

    with st.form("user_info_form"):
        age = st.number_input("Age", min_value=0, max_value=120)
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

    # Only show categories valid for the selected gender
    valid_categories = [
        cat for cat in db["Primary Category"].unique()
        if is_gender_allowed(cat, current_gender, suppress_error=True)
    ]

    # Render the grid of primary categories
    selected = display_grid(valid_categories, cols=3)

    if selected and is_gender_allowed(selected, current_gender):
        # ── EXIT free-text mode and clear any old subset ──
        st.session_state.free_input_mode = False
        st.session_state.matched_conditions = pd.DataFrame()

        # ── Save the normal path category and advance ──
        st.session_state.user_data['primary_category'] = selected
        st.session_state.page = "symptom_subcategory"
        st.rerun()

    # Offer the free-text fallback
    if st.button("Can’t find your symptoms? Enter them here"):
        st.session_state.page = "symptom_free_input"
        st.rerun()


def symptom_free_input_page():
    st.image(logo, width=80)
    st.subheader("What are your symptoms?")
    st.markdown("Enter symptoms separated by commas (e.g., headache, fever, leg pain)")

    # — Wrap in a form so Enter works —
    with st.form("free_input_form"):
        symptom_input = st.text_input("Your symptoms:")
        search = st.form_submit_button("Search Symptoms")

    if search:
        if not symptom_input.strip():
            st.warning("Please enter at least one symptom to search.")
        else:
            # 1) Normalize & split user entry
            inputs = [s.strip().lower() for s in symptom_input.split(",") if s.strip()]

            # ─── Quick anchor: map words → Primary Categories ───
            primary_names = db["Primary Category"].dropna().unique().tolist()
            cat_tokens = {
                cat: set(re.sub(r"[^A-Za-z ]+", "", cat).lower().split())
                for cat in primary_names
            }
            user_words = [
                w
                for part in inputs
                for w in re.sub(r"[^A-Za-z ]+", "", part).lower().split()
            ]
            quick_cats = [
                cat for cat, toks in cat_tokens.items()
                if any(w in toks for w in user_words)
            ]
            if quick_cats:
                # short-circuit into those categories
                subset = db[db["Primary Category"].isin(quick_cats)]
                st.session_state.free_input_mode            = True
                st.session_state.matched_conditions         = subset
                st.session_state.user_data['free_symptoms'] = symptom_input
                st.session_state.page                       = "symptom_primary_category_freeinput"
                st.rerun()
                return

            # ─── Fallback: Perform token-and-stem / fuzzy matching ───
            matches   = set()
            threshold = 0.65

            for inp in inputs:
                inp_norm = inp
                inp_stem = stem(inp_norm)
                for idx, row in db.iterrows():
                    for raw_sym in str(row["Symptoms"]).split(","):
                        cleaned     = re.sub(r"[^A-Za-z ]+", "", raw_sym).lower()
                        tokens      = cleaned.split()
                        token_stems = [stem(tok) for tok in tokens]

                        # exact token-stem match?
                        if inp_stem in token_stems:
                            matches.add(idx)
                            break

                        # fallback: substring or fuzzy-match on full-phrase stem
                        full_stem = stem(cleaned)
                        if (
                                inp_norm in cleaned
                                or cleaned in inp_norm
                                or SequenceMatcher(None, inp_stem, full_stem).ratio() >= threshold
                        ):
                            matches.add(idx)
                            break
                    # end raw_sym
                # end row
            # end inp

            subset = db.loc[sorted(matches)]
            if subset.empty:
                st.warning(
                    "❗️ No matches found. Check spelling, try again, or speak to a doctor."
                )
                if st.button("Try Again"):
                    st.rerun()
                if st.button("Speak to a Doctor"):
                    st.session_state.page = "fallback_page"
                    st.rerun()
                if st.button("Start Over"):
                    st.session_state.clear()
                    st.session_state.page = "welcome"
                    st.rerun()
                return

            # 3) Save and advance
            st.session_state.free_input_mode            = True
            st.session_state.matched_conditions         = subset
            st.session_state.user_data['free_symptoms'] = symptom_input
            st.session_state.page                       = "symptom_primary_category_freeinput"
            st.rerun()

    # — Back button outside the form —
    if st.button("← Back"):
        st.session_state.page = "symptom_category"
        st.rerun()

def symptom_primary_category_freeinput_page():
    # ── Guard: only allow free-text category pick when we actually have matches ──
    if not st.session_state.get("free_input_mode") or st.session_state.matched_conditions.empty:
        # fall back to the normal category picker
        st.session_state.page = "symptom_category"
        st.rerun()

    st.image(logo, width=80)
    st.subheader("What feels closest to how you’re feeling?")

    # now safe: we know matched_conditions exists and has columns
    subset = st.session_state.matched_conditions
    primaries = sorted(subset["Primary Category"].dropna().unique())
    choice = display_grid(primaries, cols=2)
    if choice:
        st.session_state.user_data['primary_category'] = choice
        st.session_state.page = "symptom_subcategory"
        st.rerun()

    if st.button("← Back"):
        # Back one step in the free-text flow
        st.session_state.page = "symptom_free_input"
        st.rerun()



def symptom_subcategory_page():
    st.image(logo, width=80)
    st.subheader("Let’s get a bit more specific—what feels closest to what you’re experiencing?")

    # Ensure we have a primary category
    primary = st.session_state.user_data.get("primary_category")
    if not primary:
        st.error("No category selected. Please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    # Choose source: matched subset in free-text mode, otherwise the full DB
    if st.session_state.get("free_input_mode", False):
        source = st.session_state.matched_conditions
    else:
        source = db

    # Filter by the chosen primary category
    filtered = source[source["Primary Category"] == primary]

    # Build and display the list of unique subcategories
    subcats = sorted(filtered["SubCategory"].dropna().unique())
    choice = display_grid(subcats, cols=2)
    if choice:
        st.session_state.user_data["subcategory"] = choice
        # Pick the first matching condition for the next page
        st.session_state.current_condition = filtered[filtered["SubCategory"] == choice].iloc[0]
        st.session_state.page = "symptom_selection"
        st.rerun()

    # Back button: go back to the appropriate previous page
    if st.button("← Back"):
        if st.session_state.get("free_input_mode", False):
            st.session_state.page = "symptom_primary_category_freeinput"
        else:
            st.session_state.page = "symptom_category"
        st.rerun()

def symptom_selection_page():
    st.image(logo, width=80)
    st.subheader("Tell me about your symptoms")

    primary = st.session_state.user_data.get("primary_category")
    subcat  = st.session_state.user_data.get("subcategory")
    if not primary or not subcat:
        st.error("Category or subcategory missing. Please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    # 1) Decide source: full DB for normal, matched_conditions for free-text
    source = st.session_state.matched_conditions if st.session_state.get("free_input_mode") else db

    # 2) Filter to your chosen subcategory
    subset = source[
        (source["Primary Category"] == primary) &
        (source["SubCategory"]      == subcat)
        ]

    # 3) Aggregate **all** symptoms across those rows
    options = sorted({
        s.strip()
        for row in subset["Symptoms"].dropna()
        for s   in row.split(",")
    })

    # 4) Render them
    selected = st.multiselect("Select all that apply:", options)

    # 5) Navigation
    col1, col2 = st.columns([1,3])
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
    st.subheader("Just a couple more quick questions to guide you")

    # 1️⃣ Build the subset of rows for this pathway
    primary = st.session_state.user_data.get("primary_category")
    subcat  = st.session_state.user_data.get("subcategory")

    # pick source: full DB if normal, else your matched free-text subset
    source = db if not st.session_state.get("free_input_mode", False) else st.session_state.matched_conditions

    # filter to the chosen primary/subcategory
    subset = source[
        (source["Primary Category"] == primary) &
        (source["SubCategory"]      == subcat)
        ]
    if subset.empty:
        st.error("No conditions found here—please start over.")
        if st.button("Start Over"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    # 2️⃣ Stage 1: ask every unique CQ1 in this subset
    if not st.session_state.get("cq1_done"):
        cq1s    = list(subset["Clarifying Questions 1"].dropna().unique())
        answers1 = {}
        with st.form("cq1_form"):
            for i, q in enumerate(cq1s, 1):
                answers1[q] = st.radio(q, ["Yes", "No"], key=f"cq1_{i}")
            if st.form_submit_button("Continue →"):
                st.session_state.user_data["answers1"] = answers1
                st.session_state.cq1_done = True
                st.rerun()

        # Back takes you up one step (category or free-text)
        if st.button("← Back"):
            st.session_state.page = (
                "symptom_primary_category_freeinput"
                if st.session_state.get("free_input_mode", False)
                else "symptom_subcategory"
            )
            st.rerun()
        return

    # 3️⃣ Stage 2: only if any CQ1 was “Yes”
    answers1 = st.session_state.user_data.get("answers1", {})
    if any(v == "Yes" for v in answers1.values()):
        cq2s     = list(subset["Clarifying Questions2"].dropna().unique())
        answers2 = {}
        with st.form("cq2_form"):
            for j, q in enumerate(cq2s, 1):
                answers2[q] = st.radio(q, ["Yes", "No"], key=f"cq2_{j}")
            if st.form_submit_button("Continue →"):
                merged = {**answers1, **answers2}
                st.session_state.user_data["clarifying_answers"] = merged
                st.session_state.page = "risk_flag_selection"
                del st.session_state.cq1_done
                st.rerun()

        # Back goes back into Stage 1
        if st.button("← Back"):
            del st.session_state.cq1_done
            st.rerun()
        return

    # 4️⃣ No “Yes” in CQ1: skip straight to risk flags
    st.session_state.user_data["clarifying_answers"] = answers1
    del st.session_state.cq1_done
    st.session_state.page = "risk_flag_selection"
    st.rerun()

def risk_flag_selection_page():
    st.image(logo, width=80)
    st.subheader("These factors can affect your care. Select any that apply, or “None.”")

    # ── 1) Build the subset of candidate conditions ──
    cat    = st.session_state.user_data.get("primary_category")
    sub    = st.session_state.user_data.get("subcategory")
    source = (
        st.session_state.matched_conditions
        if st.session_state.get("free_input_mode", False)
        else db
    )
    subset = source[
        (source["Primary Category"] == cat) &
        (source["SubCategory"]      == sub)
        ]
    if subset.empty:
        st.error("No conditions found here—please start over.")
        return

    # ── 2) Map CQ2 “Yes” answers back to rows ──
    answers = st.session_state.user_data.get("clarifying_answers", {})
    flagged = []
    for idx, row in subset.iterrows():
        q2 = row["Clarifying Questions2"]
        if pd.notna(q2) and answers.get(q2) == "Yes":
            flagged.append(idx)

    # ── 3) Triaging logic, always run ──
    if len(flagged) == 1:
        chosen_idx = flagged[0]
    elif len(flagged) > 1:
        df_flagged = subset.loc[flagged].copy()
        df_flagged["Acuity Level"] = df_flagged["Acuity Level"].astype(int)
        chosen_idx = df_flagged["Acuity Level"].idxmax()
    else:
        subset["Acuity Level"] = subset["Acuity Level"].astype(int)
        chosen_idx = subset["Acuity Level"].idxmax()

    # ── 4) Save the final condition ──
    st.session_state.current_condition = subset.loc[chosen_idx]

    # ── 5) Render its RiskFlags ──
    cond = st.session_state.current_condition
    raw = str(cond.get("RiskFlags", "") or "")
    flags = [f.strip() for f in raw.split(",") if f.strip()]

    selected = []
    for flag in flags:
        if st.checkbox(flag, key=f"rf_{flag}"):
            selected.append(flag)

    none = st.checkbox("None / Not Applicable", key="rf_none")
    if none and selected:
        st.warning("“None” cannot be combined with other selections; only “None” will be used.")

    # ── 6) Continue → record and go to Results ──
    if st.button("Continue"):
        st.session_state.user_data["confirmed_risks"] = [] if none else selected
        st.session_state.page = "results"
        st.rerun()

    # ← Back → clarifiers
    if st.button("← Back"):
        st.session_state.page = "clarifying_questions"
        st.rerun()


def results_page():
    # ——— Header & Title ———
    st.image(logo, width=80)
    st.header("Based on your answers, your likely condition is:")

    # ——— Fetch the chosen condition ———
    condition = st.session_state.current_condition
    if condition is None:
        st.error("No condition selected. Please start over.")
        if st.button("🔄 Start New Check"):
            st.session_state.clear()
            st.session_state.page = "welcome"
            st.rerun()
        return

    # ——— Show the condition’s name ———
    condition_title = condition["Condition"]
    st.subheader(condition_title)

    # ——— Determine baseline acuity ———
    if st.session_state.get("free_input_mode"):
        # free-text path: look at all matched rows
        baseline_rank = int(st.session_state.matched_conditions["Acuity Level"].max())
    else:
        # normal path: single selected condition
        baseline_rank = int(condition["Acuity Level"])

    # ——— Gather risk flags ———
    risk_flags = st.session_state.user_data.get("confirmed_risks", [])
    has_risk    = bool(risk_flags)

    # ——— Escalation decision ———
    is_high_acuity = (baseline_rank == 3)
    if is_high_acuity or has_risk:
        st.error("🚨 **Your answers indicate immediate/urgent action; see my recommendations below:**")
        st.write(condition["Escalated Recommendation"])
    else:
        st.success("✅ **See my recommendations below:**")
        st.write(condition["Default Recommendation"])

    # ——— Optional: Schedule Appointment button ———
    if condition.get("Referral"):
        if st.button("📅 Schedule an Appointment"):
            st.info("Appointment scheduling will be available soon.")

    # ——— Download report & New Check buttons ———
    col1, col2 = st.columns([1,1])
    with col1:
        report_text = generate_report()
        st.download_button(
            label="📄 Download Full Report",
            data=report_text,
            file_name=f"{condition_title}_report.txt"
        )
    with col2:
        if st.button("🔄 Start New Check"):
            st.session_state.clear()
            st.session_state.page = "welcome"
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
    "analytics": analytics_page,
}

if not st.session_state.logged_in:
    login_page()
else:
    PAGES[st.session_state.page]()
