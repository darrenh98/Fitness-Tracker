import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import time

# --- Configuration & Styling ---
st.set_page_config(
    page_title="RunLog Hub",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Minimalist Look & Quick-Tap UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }

    .stApp {
        background-color: #f8fafc;
    }

    /* Headers */
    h1, h2, h3 {
        font-weight: 800 !important;
        letter-spacing: -0.025em;
        color: #0f172a;
    }

    /* Modern Cards/Containers */
    .stCard, [data-testid="stForm"] {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
        border: none;
        transition: box-shadow 0.2s ease-in-out, transform 0.2s ease-in-out;
    }
    
    /* List Item Containers */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] > [data-testid="stContainer"] {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #f1f5f9;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    }

    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Caption styling for history rows */
    .history-label {
        font-size: 0.7rem;
        text-transform: uppercase;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 0px;
    }
    .history-value {
        font-size: 1rem;
        font-weight: 600;
        color: #334155;
    }

    /* Inputs and Selects */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input, .stTextArea textarea {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        padding: 0.75rem;
        background-color: #fff;
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        padding: 0.4rem 0.8rem;
        border: none;
        transition: all 0.2s;
    }
    /* Primary form submit buttons */
    [data-testid="stFormSubmitButton"] button {
        background-color: #0f172a;
        color: white;
        padding: 0.6rem 1.2rem;
        width: 100%; /* Full width for mobile friendliness */
    }
    [data-testid="stFormSubmitButton"] button:hover {
        background-color: #1e293b;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }

    /* Expander headers */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #334155;
        border-radius: 8px;
        background-color: #ffffff;
    }

    /* Quick-Tap Radio Buttons (Chips look) */
    /* Note: This targets the radio group to look like buttons */
    [data-testid="stRadio"] > div {
        flex-direction: row;
        gap: 10px;
        flex-wrap: wrap;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Persistence Helper ---
DATA_FILE = "run_tracker_data.json"

DEFAULT_DATA = {
    "runs": [],
    "health_logs": [],
    "gym_sessions": [],
    "nutrition_logs": [],
    "routines": [
        {"id": 1, "name": "Leg Day", "exercises": ["Squats", "Split Squats", "Glute Bridges", "Calf Raises"]},
        {"id": 2, "name": "Upper Body", "exercises": ["Bench Press", "Pull Ups", "Overhead Press", "Rows"]}
    ],
    "templates": {},
    "user_profile": {"age": 30, "height": 175, "weight": 70, "heightUnit": "cm", "weightUnit": "kg"},
    "cycles": {"macro": "", "meso": "", "micro": ""},
    "weekly_plan": {day: {"am": "", "pm": ""} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Ensure templates key exists for older data files
            if "templates" not in data:
                data["templates"] = {}
            return data
    except:
        return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize Session State
if 'data' not in st.session_state:
    st.session_state.data = load_data()

def persist():
    save_data(st.session_state.data)

# --- Smart Defaults Helper ---
def get_last_run_defaults(activity_type):
    """Finds the last activity of this type to prefill values"""
    runs = st.session_state.data.get('runs', [])
    if not runs:
        return 5.0, 30.0, 140 # Defaults
    
    # Filter by type
    type_runs = [r for r in runs if r.get('type') == activity_type]
    if not type_runs:
        return 5.0, 30.0, 140 # Defaults if type not found
    
    last = type_runs[0] # Assumes sorted desc
    dist = float(last.get('distance', 5.0))
    # Duration stored as decimal mins
    dur = float(last.get('duration', 30.0))
    hr = int(last.get('avgHr', 140))
    return dist, dur, hr

# --- Helper Functions ---
def format_pace(decimal_min):
    if not decimal_min or decimal_min == 0:
        return "-"
    mins = int(decimal_min)
    secs = int((decimal_min - mins) * 60)
    return f"{mins}'{secs:02d}\""

def format_duration(decimal_min):
    if not decimal_min:
        return "00:00:00"
    mins = int(decimal_min)
    secs = int((decimal_min - mins) * 60)
    
    hrs = mins // 60
    rem_mins = mins % 60
    
    if hrs > 0:
        return f"{hrs:02d}:{rem_mins:02d}:{secs:02d}"
    return f"{rem_mins:02d}:{secs:02d}"

def parse_time_input(time_str):
    try:
        # Clean string
        clean = time_str.strip()
        if not clean:
            return 0.0
            
        parts = clean.split(":")
        
        # Format: hh:mm:ss
        if len(parts) == 3:
            return float(parts[0]) * 60 + float(parts[1]) + float(parts[2]) / 60
        # Format: mm:ss
        elif len(parts) == 2:
            return float(parts[0]) + float(parts[1]) / 60
        # Format: decimal minutes or raw number
        elif len(parts) == 1:
            return float(parts[0])
            
        return 0.0
    except:
        return 0.0

# --- Sidebar Navigation ---
with st.sidebar:
    st.title("🏃 RunLog Hub")
    
    selected_tab = st.radio("Navigate", ["Plan", "Field (Runs)", "Gym", "Nutrition", "Stats"], label_visibility="collapsed")
    
    st.divider()
    
    # Profile Quick View
    with st.expander("👤 Athlete Profile"):
        prof = st.session_state.data['user_profile']
        c1, c2 = st.columns(2)
        new_weight = c1.number_input("Weight (kg)", value=float(prof.get('weight', 70)), key="prof_weight")
        new_height = c2.number_input("Height (cm)", value=float(prof.get('height', 175)), key="prof_height")
        
        if c1.button("Save Profile"):
            st.session_state.data['user_profile']['weight'] = new_weight
            st.session_state.data['user_profile']['height'] = new_height
            persist()
            st.success("Saved!")

# --- TAB: PLAN ---
if selected_tab == "Plan":
    st.header("📅 Training Plan")
    
    # Cycles
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.container(border=True).markdown("**Macrocycle (Annual)**")
        macro = st.text_area("Annual Goal", value=st.session_state.data['cycles']['macro'], height=120, key="txt_macro", label_visibility="collapsed")
        if macro != st.session_state.data['cycles']['macro']:
            st.session_state.data['cycles']['macro'] = macro
            persist()

    with c2:
        st.container(border=True).markdown("**Mesocycle (Block)**")
        meso = st.text_area("Block Focus", value=st.session_state.data['cycles']['meso'], height=120, key="txt_meso", label_visibility="collapsed")
        if meso != st.session_state.data['cycles']['meso']:
            st.session_state.data['cycles']['meso'] = meso
            persist()

    with c3:
        st.container(border=True).markdown("**Microcycle (Week)**")
        micro = st.text_area("Weekly Focus", value=st.session_state.data['cycles']['micro'], height=120, key="txt_micro", label_visibility="collapsed")
        if micro != st.session_state.data['cycles']['micro']:
            st.session_state.data['cycles']['micro'] = micro
            persist()

    st.subheader("Weekly Schedule")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # We use columns to display the week grid
    cols = st.columns(7)
    for i, day in enumerate(days):
        with cols[i]:
            with st.container(border=True):
                st.caption(day.upper())
                am_val = st.text_input("AM", value=st.session_state.data['weekly_plan'][day]['am'], key=f"am_{day}", placeholder="Rest", label_visibility="collapsed")
                pm_val = st.text_input("PM", value=st.session_state.data['weekly_plan'][day]['pm'], key=f"pm_{day}", placeholder="Rest", label_visibility="collapsed")
                
                # Save on change logic (simplified for streamlit, saves on every interaction if key changes)
                if (am_val != st.session_state.data['weekly_plan'][day]['am'] or 
                    pm_val != st.session_state.data['weekly_plan'][day]['pm']):
                    st.session_state.data['weekly_plan'][day]['am'] = am_val
                    st.session_state.data['weekly_plan'][day]['pm'] = pm_val
                    persist()

# --- TAB: FIELD (RUNS) ---
elif selected_tab == "Field (Runs)":
    st.header("👟 Field Activities")
    
    # Prepare data
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    
    # --- LOGGING FORM (Always accessible at top) ---
    # Determine Edit Mode
    edit_run_id = st.session_state.get('edit_run_id', None)
    
    # State handling for Quick-Tap defaults
    # We use separate session_state keys for the widgets to control them dynamically
    if 'form_act_type' not in st.session_state: st.session_state.form_act_type = "Run"
    
    # Get smart defaults based on CURRENT selection
    # (Note: In a real "dynamic" form we'd use callback on the radio change to update defaults,
    #  but for simplicity we fetch defaults on render if not editing)
    sd_dist, sd_dur, sd_hr = get_last_run_defaults(st.session_state.form_act_type)
    
    # Default values logic
    def_type = st.session_state.form_act_type
    def_date, def_dist, def_dur, def_hr, def_notes, def_feel, def_rpe = datetime.now(), sd_dist, sd_dur, sd_hr, "", "Normal", 5
    
    if edit_run_id:
        run_data = next((r for r in st.session_state.data['runs'] if r['id'] == edit_run_id), None)
        if run_data:
            def_type = run_data['type']
            def_date = datetime.strptime(run_data['date'], '%Y-%m-%d').date()
            def_dist = run_data['distance']
            def_dur = run_data['duration'] # Decimal mins
            def_hr = run_data['avgHr']
            def_notes = run_data.get('notes', '')
            def_feel = run_data.get('feel', 'Normal')
            def_rpe = run_data.get('rpe', 5)

    form_label = f"✏️ Edit Activity" if edit_run_id else "➕ Log Activity (Quick-Tap)"
    expander_state = True if edit_run_id else False

    with st.expander(form_label, expanded=expander_state):
        
        # --- Templates Section (Only when adding) ---
        if not edit_run_id:
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                templates = st.session_state.data.get('templates', {})
                template_names = ["None"] + list(templates.keys())
                sel_template = st.selectbox("📂 Load Template", template_names, label_visibility="collapsed")
                
                if sel_template != "None":
                    t_data = templates[sel_template]
                    def_type = t_data.get('type', "Run")
                    def_dist = t_data.get('distance', 5.0)
                    def_dur = t_data.get('duration', 30.0)
                    def_notes = t_data.get('notes', "")
                    # Apply template to session state immediately for re-render if needed
                    st.session_state.form_act_type = def_type

        with st.form("run_form"):
            # Row 1: Quick Toggles
            st.caption("Activity Type")
            act_type = st.radio("Type", ["Run", "Walk", "Ultimate"], 
                                index=["Run", "Walk", "Ultimate"].index(def_type) if def_type in ["Run", "Walk", "Ultimate"] else 0,
                                key="act_type_radio",
                                horizontal=True, label_visibility="collapsed")
            
            # Row 2: Sliders for Speed & Distance
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"Distance: {def_dist} km")
                dist = st.slider("Distance", 0.0, 42.0, float(def_dist), 0.1, label_visibility="collapsed")
            with c2:
                st.caption(f"Duration: {int(def_dur)} mins")
                dur_mins = st.slider("Duration", 0, 180, int(def_dur), 5, label_visibility="collapsed")
            
            # Row 3: Effort
            c3, c4 = st.columns(2)
            with c3:
                st.caption(f"Avg HR: {def_hr} bpm")
                hr = st.slider("Heart Rate", 60, 200, int(def_hr), 1, label_visibility="collapsed")
            with c4:
                st.caption(f"RPE (Effort): {def_rpe}/10")
                rpe = st.slider("RPE", 1, 10, int(def_rpe), 1, label_visibility="collapsed")

            # Row 4: Feel & Date
            c5, c6 = st.columns(2)
            with c5:
                st.caption("How did it feel?")
                feel = st.radio("Feel", ["Good", "Normal", "Tired", "Pain"], 
                                index=["Good", "Normal", "Tired", "Pain"].index(def_feel) if def_feel in ["Good", "Normal", "Tired", "Pain"] else 1,
                                horizontal=True, label_visibility="collapsed")
            with c6:
                st.caption("Date")
                act_date = st.date_input("Date", def_date, label_visibility="collapsed")
            
            # Row 5: Notes
            notes = st.text_area("Notes", value=def_notes, placeholder="Easy run, felt strong...", height=3)
            
            # Actions
            btn_text = "Update Activity" if edit_run_id else "Save Activity"
            submitted = st.form_submit_button(btn_text)
            
            if submitted:
                # Use millisecond precision for new IDs
                new_id = int(time.time() * 1000)
                
                run_obj = {
                    "id": edit_run_id if edit_run_id else new_id,
                    "date": str(act_date),
                    "type": act_type,
                    "distance": dist,
                    "duration": float(dur_mins), # Store as decimal minutes directly
                    "avgHr": hr,
                    "rpe": rpe,
                    "feel": feel,
                    "notes": notes
                }
                
                if edit_run_id:
                    idx = next((i for i, r in enumerate(st.session_state.data['runs']) if r['id'] == edit_run_id), -1)
                    if idx != -1:
                        st.session_state.data['runs'][idx] = run_obj
                    st.session_state.edit_run_id = None
                    st.success("Activity Updated!")
                else:
                    st.session_state.data['runs'].insert(0, run_obj)
                    st.success("Activity Logged!")
                persist()
                st.rerun()

        # Save Template Button (Outside Form to avoid submit conflict, but connected visually)
        if not edit_run_id:
            with st.popover("💾 Save as Template"):
                tpl_name = st.text_input("Template Name", placeholder="Morning 5k")
                if st.button("Save Template"):
                    if tpl_name:
                        st.session_state.data['templates'][tpl_name] = {
                            "type": def_type, "distance": dist, "duration": dur_mins, "notes": notes
                        }
                        persist()
                        st.success(f"Saved '{tpl_name}'!")
                        st.rerun()

        if edit_run_id:
            if st.button("Cancel Edit"):
                st.session_state.edit_run_id = None
                st.rerun()

    st.markdown("### Dashboard & History")
    
    # --- TABS FOR FILTERING ---
    tabs = st.tabs(["All Activities", "Run", "Walk", "Ultimate"])
    
    categories = ["All", "Run", "Walk", "Ultimate"]
    
    for i, tab in enumerate(tabs):
        with tab:
            filter_cat = categories[i]
            
            # Filter Data
            if not runs_df.empty:
                if filter_cat != "All":
                    filtered_df = runs_df[runs_df['type'] == filter_cat]
                else:
                    filtered_df = runs_df
            else:
                filtered_df = pd.DataFrame(columns=['distance', 'duration', 'avgHr'])

            # Stats Calculation
            total_dist = filtered_df['distance'].sum() if not filtered_df.empty else 0
            total_mins = filtered_df['duration'].sum() if not filtered_df.empty else 0
            count = len(filtered_df)
            avg_hr = filtered_df['avgHr'].mean() if not filtered_df.empty and filtered_df['avgHr'].sum() > 0 else 0
            
            # Pace (only if not Ultimate)
            pace_label = "-"
            if total_dist > 0:
                avg_pace_val = total_mins / total_dist
                pace_label = format_pace(avg_pace_val) + " /km"
            
            # Time Format
            t_hours = int(total_mins // 60)
            t_mins = int(total_mins % 60)
            time_label = f"{t_hours}h {t_mins}m"

            # 1. DASHBOARD CARDS
            with st.container():
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Dist", f"{total_dist:.1f} km")
                m2.metric("Total Time", time_label)
                # Conditional Metric for Ultimate
                if filter_cat == "Ultimate":
                    m3.metric("Activities", count) 
                else:
                    m3.metric("Avg Pace", pace_label)
                m4.metric("Avg HR", f"{int(avg_hr)} bpm")
                if filter_cat == "Ultimate":
                     m5.empty() 
                else:
                     m5.metric("Count", count)

            st.divider()

            # 2. CLEAN HISTORY LIST
            if not filtered_df.empty:
                for idx, row in filtered_df.iterrows():
                    with st.container():
                        # Layout: Date | Type | Dist | Time | Pace/Notes | HR | Actions
                        c_date, c_type, c_dist, c_time, c_custom, c_hr, c_act = st.columns([1.5, 1.2, 1.2, 1.2, 2.5, 1, 1])
                        
                        # Date
                        c_date.markdown(f"**{row['date']}**")
                        
                        # Type Icon
                        icon_map = {"Run": "🏃", "Walk": "🚶", "Ultimate": "🥏"}
                        c_type.markdown(f"{icon_map.get(row['type'], 'activity')} **{row['type']}**")
                        
                        # Distance
                        c_dist.markdown('<p class="history-label">Dist</p>', unsafe_allow_html=True)
                        c_dist.markdown(f'<p class="history-value">{row["distance"]} km</p>', unsafe_allow_html=True)
                        
                        # Time
                        c_time.markdown('<p class="history-label">Time</p>', unsafe_allow_html=True)
                        c_time.markdown(f'<p class="history-value">{format_duration(row["duration"])}</p>', unsafe_allow_html=True)
                        
                        # Custom Column: Pace OR Notes (for Ultimate)
                        if row['type'] == 'Ultimate':
                            c_custom.markdown('<p class="history-label">Notes</p>', unsafe_allow_html=True)
                            note_text = row.get('notes', '-') 
                            c_custom.markdown(f'<p class="history-value" style="font-size:0.9rem; font-weight:400;">{note_text if note_text else "-"}</p>', unsafe_allow_html=True)
                        else:
                            c_custom.markdown('<p class="history-label">Pace</p>', unsafe_allow_html=True)
                            pace_val = row['duration'] / row['distance'] if row['distance'] > 0 else 0
                            c_custom.markdown(f'<p class="history-value">{format_pace(pace_val)} /km</p>', unsafe_allow_html=True)
                        
                        # HR / Feel
                        c_hr.markdown('<p class="history-label">HR / Feel</p>', unsafe_allow_html=True)
                        hr_val = row['avgHr'] if row['avgHr'] > 0 else "-"
                        feel_val = row.get('feel', '')
                        feel_emoji = {"Good": "😊", "Normal": "😐", "Tired": "😫", "Pain": "🤕"}.get(feel_val, "")
                        c_hr.markdown(f'<p class="history-value">{hr_val} {feel_emoji}</p>', unsafe_allow_html=True)
                        
                        # Actions
                        with c_act:
                            b1, b2 = st.columns(2)
                            if b1.button("✏️", key=f"ed_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.edit_run_id = row['id']
                                st.rerun()
                            if b2.button("🗑️", key=f"del_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.data['runs'] = [r for r in st.session_state.data['runs'] if r['id'] != row['id']]
                                persist()
                                st.rerun()
            else:
                st.info("No activities found for this category.")

# --- TAB: GYM ---
elif selected_tab == "Gym":
    st.header("💪 Gym & Weights")
    
    tab_log, tab_routines, tab_history = st.tabs(["Log Session", "Routines", "History"])
    
    with tab_routines:
        st.subheader("Manage Routines")
        
        # New Routine
        with st.form("new_routine"):
            r_name = st.text_input("Routine Name (e.g., Pull Day)")
            r_exs = st.text_area("Exercises (comma separated)", placeholder="Pullups, Rows, Curls")
            if st.form_submit_button("Create Routine"):
                ex_list = [x.strip() for x in r_exs.split(",") if x.strip()]
                new_r = {"id": int(time.time()), "name": r_name, "exercises": ex_list}
                st.session_state.data['routines'].append(new_r)
                persist()
                st.success("Routine Created!")
                st.rerun()
                
        # Display Routines
        for r in st.session_state.data['routines']:
            with st.container(border=True):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{r['name']}**")
                c1.caption(" • ".join(r['exercises']))
                if c2.button("🗑️", key=f"del_rout_{r['id']}"):
                    st.session_state.data['routines'] = [x for x in st.session_state.data['routines'] if x['id'] != r['id']]
                    persist()
                    st.rerun()

    with tab_log:
        routine_opts = {r['name']: r for r in st.session_state.data['routines']}
        selected_r_name = st.selectbox("Select Routine", list(routine_opts.keys()))
        
        if selected_r_name:
            sel_routine = routine_opts[selected_r_name]
            
            with st.form("gym_log"):
                st.subheader(f"Logging: {sel_routine['name']}")
                log_date = st.date_input("Date", datetime.now())
                
                # Dynamic inputs for exercises with SLIDERS
                exercises_data = []
                for ex in sel_routine['exercises']:
                    st.markdown(f"**{ex}**")
                    c1, c2 = st.columns(2)
                    
                    # Try to find smart default from history? 
                    # (Simplified for now: Just sliders)
                    w = c1.slider(f"Weight ({ex})", 0, 200, 40, 5)
                    r = c2.slider(f"Reps ({ex})", 0, 30, 10, 1)
                    # We store sets as a simple repeating structure for minimal UI
                    sets_count = st.slider(f"Sets ({ex})", 1, 6, 3, 1, key=f"sets_{ex}")
                    
                    # Expand sets for data structure
                    w_str = ",".join([str(w)] * sets_count)
                    r_str = ",".join([str(r)] * sets_count)
                    
                    exercises_data.append({"name": ex, "weights": w_str, "reps": r_str})
                
                if st.form_submit_button("Complete Workout"):
                    processed_exs = []
                    total_vol = 0
                    
                    for item in exercises_data:
                        # Simple parsing logic
                        ws = [float(x) for x in item['weights'].split(",") if x.strip()]
                        rs = [float(x) for x in item['reps'].split(",") if x.strip()]
                        
                        # Calculate volume for valid sets (min length of weight/reps arrays)
                        sets_data = []
                        for i in range(min(len(ws), len(rs))):
                            sets_data.append({"weight": ws[i], "reps": rs[i]})
                            total_vol += ws[i] * rs[i]
                            
                        if sets_data:
                            processed_exs.append({"name": item['name'], "sets": sets_data})
                            
                    new_session = {
                        "id": int(time.time()),
                        "date": str(log_date),
                        "routineName": selected_r_name,
                        "exercises": processed_exs,
                        "totalVolume": total_vol
                    }
                    
                    st.session_state.data['gym_sessions'].insert(0, new_session)
                    persist()
                    st.success("Workout Saved!")
                    st.rerun()

    with tab_history:
        sessions = st.session_state.data['gym_sessions']
        if sessions:
            # Stats
            total_vol_all = sum(s.get('totalVolume', 0) for s in sessions)
            
            with st.container(border=True):
                st.metric("Total Volume Lifted", f"{total_vol_all/1000:.1f}k kg")
            
            st.divider()
            
            # List rows
            for s in sessions:
                with st.container():
                    c1, c2, c3 = st.columns([3, 4, 1])
                    c1.markdown(f"**{s['date']}**")
                    c1.caption(s['routineName'])
                    
                    details = ", ".join([f"{ex['name']} ({len(ex['sets'])})" for ex in s['exercises']])
                    c2.caption(details)
                    c2.text(f"Vol: {s.get('totalVolume',0)}kg")
                    
                    if c3.button("🗑️", key=f"del_sess_{s['id']}"):
                        st.session_state.data['gym_sessions'] = [x for x in st.session_state.data['gym_sessions'] if x['id'] != s['id']]
                        persist()
                        st.rerun()
        else:
            st.info("No gym sessions logged.")

# --- TAB: NUTRITION ---
elif selected_tab == "Nutrition":
    st.header("🥗 Nutrition Log")
    
    c1, c2 = st.columns([1, 2])
    
    # Nutrition Edit Logic
    edit_nut_id = st.session_state.get('edit_nut_id', None)
    
    def_nut_date, def_meal, def_cal, def_prot, def_carb, def_fat = datetime.now(), "", 500, 30, 50, 15
    
    if edit_nut_id:
        n_data = next((n for n in st.session_state.data['nutrition_logs'] if n['id'] == edit_nut_id), None)
        if n_data:
            def_nut_date = datetime.strptime(n_data['date'], '%Y-%m-%d').date()
            def_meal = n_data['meal']
            def_cal = n_data['calories']
            def_prot = n_data['protein']
            def_carb = n_data['carbs']
            def_fat = n_data['fat']

    with c1:
        lbl = "✏️ Edit Meal" if edit_nut_id else "Add Meal"
        st.subheader(lbl)
        with st.form("food_form"):
            f_date = st.date_input("Date", def_nut_date)
            meal = st.text_input("Meal Name", value=def_meal, placeholder="Chicken Rice")
            
            # Sliders for nutrition quick log
            cal = st.slider("Calories", 0, 2000, int(def_cal), 50)
            prot = st.slider("Protein (g)", 0, 100, int(def_prot), 5)
            carbs = st.slider("Carbs (g)", 0, 200, int(def_carb), 5)
            fat = st.slider("Fat (g)", 0, 100, int(def_fat), 5)
            
            btn_txt = "Update Meal" if edit_nut_id else "Add Meal"
            if st.form_submit_button(btn_txt):
                nut_obj = {
                    "id": edit_nut_id if edit_nut_id else int(time.time()),
                    "date": str(f_date),
                    "meal": meal,
                    "calories": cal,
                    "protein": prot,
                    "carbs": carbs,
                    "fat": fat
                }
                
                if edit_nut_id:
                     idx = next((i for i, n in enumerate(st.session_state.data['nutrition_logs']) if n['id'] == edit_nut_id), -1)
                     if idx != -1: st.session_state.data['nutrition_logs'][idx] = nut_obj
                     st.session_state.edit_nut_id = None
                     st.success("Meal Updated!")
                else:
                    st.session_state.data['nutrition_logs'].insert(0, nut_obj)
                    st.success("Meal Added!")
                    
                persist()
                st.rerun()
                
        if edit_nut_id:
            if st.button("Cancel"):
                st.session_state.edit_nut_id = None
                st.rerun()
                
    with c2:
        # Today's Summary
        today_str = str(datetime.now().date())
        todays_logs = [x for x in st.session_state.data['nutrition_logs'] if x['date'] == today_str]
        
        t_cal = sum(x['calories'] for x in todays_logs)
        t_pro = sum(x['protein'] for x in todays_logs)
        t_carb = sum(x['carbs'] for x in todays_logs)
        t_fat = sum(x['fat'] for x in todays_logs)
        
        st.subheader("Today's Macros")
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Calories", t_cal)
            col2.metric("Protein", f"{t_pro}g")
            col3.metric("Carbs", f"{t_carb}g")
            col4.metric("Fat", f"{t_fat}g")
        
        # History
        st.divider()
        st.subheader("Recent Meals")
        
        for n in st.session_state.data['nutrition_logs']:
             with st.container():
                 nc1, nc2, nc3, nc4, nc_act = st.columns([2, 3, 2, 3, 2])
                 nc1.markdown(f"**{n['date']}**")
                 nc2.text(n['meal'])
                 nc3.text(f"{n['calories']} kcal")
                 nc4.caption(f"P: {n['protein']}g • C: {n['carbs']}g • F: {n['fat']}g")
                 
                 with nc_act:
                    be, bd = st.columns(2)
                    if be.button("✏️", key=f"edit_nut_{n['id']}"):
                        st.session_state.edit_nut_id = n['id']
                        st.rerun()
                    if bd.button("🗑️", key=f"del_nut_{n['id']}"):
                        st.session_state.data['nutrition_logs'] = [x for x in st.session_state.data['nutrition_logs'] if x['id'] != n['id']]
                        persist()
                        st.rerun()

# --- TAB: STATS (HEALTH) ---
elif selected_tab == "Stats":
    st.header("❤️ Physiological Stats")
    
    # Edit Logic
    edit_hlth_id = st.session_state.get('edit_hlth_id', None)
    
    def_h_date, def_rhr, def_hrv, def_vo2, def_sleep = datetime.now(), 60, 0, 0.0, 0.0
    
    if edit_hlth_id:
        h_data = next((h for h in st.session_state.data['health_logs'] if h['id'] == edit_hlth_id), None)
        if h_data:
            def_h_date = datetime.strptime(h_data['date'], '%Y-%m-%d').date()
            def_rhr = h_data['rhr']
            def_hrv = h_data['hrv']
            def_vo2 = h_data['vo2Max']
            def_sleep = h_data['sleepHours']

    lbl_h = "✏️ Edit Stats" if edit_hlth_id else "➕ Log Health Stats"
    expanded_h = True if edit_hlth_id else False

    with st.expander(lbl_h, expanded=expanded_h):
        with st.form("health_form"):
            h_date = st.date_input("Date", def_h_date)
            # Converted to Sliders
            c1, c2 = st.columns(2)
            rhr = c1.slider("Resting HR", 30, 150, int(def_rhr), 1)
            hrv = c2.slider("HRV (ms)", 0, 200, int(def_hrv), 1)
            
            c3, c4 = st.columns(2)
            vo2 = c3.slider("VO2 Max", 20.0, 80.0, float(def_vo2), 0.1)
            sleep = c4.slider("Sleep (hrs)", 0.0, 12.0, float(def_sleep), 0.1)
            
            btn_h_txt = "Update Stats" if edit_hlth_id else "Log Stats"
            
            if st.form_submit_button(btn_h_txt):
                new_h = {
                    "id": edit_hlth_id if edit_hlth_id else int(time.time()),
                    "date": str(h_date),
                    "rhr": rhr,
                    "hrv": hrv,
                    "vo2Max": vo2,
                    "sleepHours": sleep
                }
                
                if edit_hlth_id:
                     idx = next((i for i, h in enumerate(st.session_state.data['health_logs']) if h['id'] == edit_hlth_id), -1)
                     if idx != -1: st.session_state.data['health_logs'][idx] = new_h
                     st.session_state.edit_hlth_id = None
                     st.success("Stats Updated!")
                else:
                    st.session_state.data['health_logs'].insert(0, new_h)
                    st.success("Stats Logged!")
                
                persist()
                st.rerun()

        if edit_hlth_id:
            if st.button("Cancel Edit", key="cancel_h"):
                st.session_state.edit_hlth_id = None
                st.rerun()

    health_df = pd.DataFrame(st.session_state.data['health_logs'])
    
    if not health_df.empty:
        # Ensure date is datetime for sorting
        health_df['date'] = pd.to_datetime(health_df['date'])
        health_df = health_df.sort_values(by='date')
        
        # Charts
        c1, c2 = st.columns(2)
        
        with c1:
            with st.container(border=True):
                fig_hrv = px.line(health_df, x='date', y='hrv', title="HRV Trends", markers=True)
                fig_hrv.update_traces(line_color='#22c55e')
                fig_hrv.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter")
                st.plotly_chart(fig_hrv, use_container_width=True)
            
        with c2:
            with st.container(border=True):
                fig_sleep = px.bar(health_df, x='date', y='sleepHours', title="Sleep Duration")
                fig_sleep.update_traces(marker_color='#6366f1')
                fig_sleep.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter")
                st.plotly_chart(fig_sleep, use_container_width=True)
            
        c3, c4 = st.columns(2)
        with c3:
            with st.container(border=True):
                fig_rhr = px.line(health_df, x='date', y='rhr', title="Resting Heart Rate", markers=True)
                fig_rhr.update_traces(line_color='#ef4444')
                fig_rhr.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter")
                st.plotly_chart(fig_rhr, use_container_width=True)
            
        with c4:
            with st.container(border=True):
                fig_vo2 = px.line(health_df, x='date', y='vo2Max', title="VO2 Max", markers=True)
                fig_vo2.update_traces(line_color='#3b82f6')
                fig_vo2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter")
                st.plotly_chart(fig_vo2, use_container_width=True)
        
        st.divider()
        st.subheader("History")
        # List rows
        # Need to sort descending by date for list view (charts need ascending)
        list_h_df = health_df.sort_values(by='date', ascending=False)
        
        for index, row in list_h_df.iterrows():
             with st.container():
                 hc1, hc2, hc3, hc4, hc5, hc_act = st.columns(6)
                 hc1.markdown(f"**{row['date'].date()}**")
                 
                 hc2.markdown('<p class="history-label">RHR</p>', unsafe_allow_html=True)
                 hc2.markdown(f'<p class="history-value">{row["rhr"]}</p>', unsafe_allow_html=True)
                 
                 hc3.markdown('<p class="history-label">HRV</p>', unsafe_allow_html=True)
                 hc3.markdown(f'<p class="history-value">{row["hrv"]}</p>', unsafe_allow_html=True)
                 
                 hc4.markdown('<p class="history-label">VO2</p>', unsafe_allow_html=True)
                 hc4.markdown(f'<p class="history-value">{row["vo2Max"]}</p>', unsafe_allow_html=True)
                 
                 hc5.markdown('<p class="history-label">Sleep</p>', unsafe_allow_html=True)
                 hc5.markdown(f'<p class="history-value">{row["sleepHours"]}</p>', unsafe_allow_html=True)
                 
                 with hc_act:
                    he, hd = st.columns(2)
                    # Use row['id'] for logic
                    if he.button("✏️", key=f"edit_h_{row['id']}"):
                        st.session_state.edit_hlth_id = row['id']
                        st.rerun()
                    if hd.button("🗑️", key=f"del_h_{row['id']}"):
                        st.session_state.data['health_logs'] = [x for x in st.session_state.data['health_logs'] if x['id'] != row['id']]
                        persist()
                        st.rerun()
            
    else:
        st.info("No health stats logged yet.")
