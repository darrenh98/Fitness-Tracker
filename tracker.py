import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta
import time
import copy

# --- Configuration & Styling ---
st.set_page_config(
    page_title="RunLog Hub",
    page_icon=":material/sprint:", # Browser tab icon
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
    .history-sub {
        font-size: 0.85rem;
        color: #64748b;
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
    [data-testid="stRadio"] > div {
        flex-direction: row;
        gap: 10px;
        flex-wrap: wrap;
    }

    /* --- MOBILE OPTIMIZATIONS --- */
    @media only screen and (max-width: 600px) {
        .stCard, [data-testid="stForm"] {
            padding: 1rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.4rem;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.7rem;
        }
        /* Adjust list container padding for mobile */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] > [data-testid="stContainer"] {
            padding: 0.75rem;
        }
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
            if "templates" not in data:
                data["templates"] = {}
            return data
    except:
        return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

if 'data' not in st.session_state:
    st.session_state.data = load_data()

def persist():
    save_data(st.session_state.data)

# --- Smart Defaults Helper ---
def get_last_run_defaults(activity_type):
    runs = st.session_state.data.get('runs', [])
    if not runs:
        return 5.0, 30.0, 140
    type_runs = [r for r in runs if r.get('type') == activity_type]
    if not type_runs:
        return 5.0, 30.0, 140
    last = type_runs[0]
    dist = float(last.get('distance', 5.0))
    dur = float(last.get('duration', 30.0))
    hr = int(last.get('avgHr', 140))
    return dist, dur, hr

def get_last_lift_stats(ex_name):
    """Finds the last set data for a specific exercise"""
    sessions = st.session_state.data.get('gym_sessions', [])
    if not sessions:
        return None
        
    # Sessions are already sorted newest first usually, but let's be sure
    # Assuming index 0 is newest
    for s in sessions:
        for ex in s['exercises']:
            if ex['name'].lower() == ex_name.lower():
                # Found it
                # Format: "Last: 100kg x 5, 100kg x 5"
                sets_str = ", ".join([f"{s['reps']}x{s['weight']}kg" for s in ex['sets']])
                return sets_str
    return None

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
        clean = time_str.strip()
        if not clean: return 0.0
        parts = clean.split(":")
        if len(parts) == 3: return float(parts[0]) * 60 + float(parts[1]) + float(parts[2]) / 60
        elif len(parts) == 2: return float(parts[0]) + float(parts[1]) / 60
        elif len(parts) == 1: return float(parts[0])
        return 0.0
    except:
        return 0.0

def generate_report(start_date, end_date, selected_cats):
    report = [f"📊 **Training Report**"]
    report.append(f"📅 {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}\n")
    
    # 1. FIELD ACTIVITIES
    field_types = [t for t in ["Run", "Walk", "Ultimate"] if t in selected_cats]
    
    if field_types:
        runs = st.session_state.data['runs']
        # Filter by date and type
        period_runs = [
            r for r in runs 
            if start_date <= datetime.strptime(r['date'], '%Y-%m-%d').date() <= end_date
            and r['type'] in field_types
        ]
        # Sort by date
        period_runs.sort(key=lambda x: x['date'])
        
        if period_runs:
            total_dist = sum(r['distance'] for r in period_runs)
            total_time = sum(r['duration'] for r in period_runs)
            report.append(f"👟 **FIELD ACTIVITIES ({len(period_runs)})**")
            report.append(f"Total: {total_dist:.1f} km | {format_duration(total_time)}")
            
            for r in period_runs:
                # Basic line
                line = f"- {r['date'][5:]}: {r['type']} {r['distance']}km @ {format_duration(r['duration'])}"
                
                # Pace calculation
                if r['type'] != 'Ultimate' and r['distance'] > 0:
                    pace = r['duration'] / r['distance']
                    line += f" ({format_pace(pace)}/km)"
                
                # HR & Feel
                hr = f"{r['avgHr']}bpm" if r['avgHr'] > 0 else ""
                feel = r.get('feel', '')
                if hr or feel:
                    line += f" | {hr} {feel}"
                
                report.append(line)
                
                # Detailed Notes/Zones line
                details = []
                if r.get('notes'): details.append(f"📝 {r['notes']}")
                
                # Add zones if they exist and are non-zero
                zones = []
                for i in range(1, 6):
                    z_val = r.get(f'z{i}', 0)
                    if z_val > 0:
                        zones.append(f"Z{i}:{format_duration(z_val)}")
                if zones:
                    details.append(f"Zones: {', '.join(zones)}")
                
                if details:
                    report.append(f"   {' | '.join(details)}")
            report.append("")
    
    # 2. GYM
    if "Gym" in selected_cats:
        gyms = st.session_state.data['gym_sessions']
        period_gyms = [g for g in gyms if start_date <= datetime.strptime(g['date'], '%Y-%m-%d').date() <= end_date]
        period_gyms.sort(key=lambda x: x['date'])
        
        if period_gyms:
            report.append(f"💪 **GYM ({len(period_gyms)})**")
            for g in period_gyms:
                vol = g.get('totalVolume', 0)
                report.append(f"- {g['date'][5:]}: {g['routineName']} (Vol: {vol:.0f}kg)")
                # List exercises briefly
                ex_names = [e['name'] for e in g['exercises']]
                if ex_names:
                    report.append(f"   Exs: {', '.join(ex_names)}")
            report.append("")

    # 3. STATS
    if "Stats" in selected_cats:
        stats = st.session_state.data['health_logs']
        period_stats = [s for s in stats if start_date <= datetime.strptime(s['date'], '%Y-%m-%d').date() <= end_date]
        
        if period_stats:
            avg_rhr = sum(s['rhr'] for s in period_stats) / len(period_stats)
            avg_hrv = sum(s['hrv'] for s in period_stats) / len(period_stats)
            avg_sleep = sum(s['sleepHours'] for s in period_stats) / len(period_stats)
            
            report.append(f"❤️ **RECOVERY (Avg)**")
            report.append(f"Sleep: {avg_sleep:.1f}h | HRV: {int(avg_hrv)} | RHR: {int(avg_rhr)}")

    return "\n".join(report)

# --- Sidebar Navigation ---
with st.sidebar:
    st.title(":material/sprint: RunLog Hub")
    selected_tab = st.radio("Navigate", ["Plan", "Field (Runs)", "Gym", "Nutrition", "Stats"], label_visibility="collapsed")
    st.divider()
    
    # Export Section
    with st.expander("📤 Share Report"):
        st.caption("Generate a text summary for your coach.")
        
        # Date Range
        col_r1, col_r2 = st.columns(2)
        start_r = col_r1.date_input("Start", datetime.now() - timedelta(days=6))
        end_r = col_r2.date_input("End", datetime.now())
        
        # Data Selection
        cat_options = ["Run", "Walk", "Ultimate", "Gym", "Stats"]
        selected_cats = st.multiselect("Include", cat_options, default=cat_options, label_visibility="collapsed")
        
        if st.button("Generate Report", use_container_width=True):
            report_text = generate_report(start_r, end_r, selected_cats)
            st.code(report_text, language="text")
            
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
    st.header(":material/calendar_month: Training Plan")
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
    cols = st.columns(7)
    for i, day in enumerate(days):
        with cols[i]:
            with st.container(border=True):
                st.caption(day.upper())
                am_val = st.text_input("AM", value=st.session_state.data['weekly_plan'][day]['am'], key=f"am_{day}", placeholder="Rest", label_visibility="collapsed")
                pm_val = st.text_input("PM", value=st.session_state.data['weekly_plan'][day]['pm'], key=f"pm_{day}", placeholder="Rest", label_visibility="collapsed")
                if (am_val != st.session_state.data['weekly_plan'][day]['am'] or pm_val != st.session_state.data['weekly_plan'][day]['pm']):
                    st.session_state.data['weekly_plan'][day]['am'] = am_val
                    st.session_state.data['weekly_plan'][day]['pm'] = pm_val
                    persist()

# --- TAB: FIELD (RUNS) ---
elif selected_tab == "Field (Runs)":
    st.header(":material/directions_run: Field Activities")
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    
    edit_run_id = st.session_state.get('edit_run_id', None)
    if 'form_act_type' not in st.session_state: st.session_state.form_act_type = "Run"
    
    sd_dist, sd_dur, sd_hr = get_last_run_defaults(st.session_state.form_act_type)
    
    def_type = st.session_state.form_act_type
    def_date, def_dist, def_dur, def_hr, def_notes, def_feel, def_rpe = datetime.now(), sd_dist, sd_dur, sd_hr, "", "Normal", 5
    def_z1, def_z2, def_z3, def_z4, def_z5 = "", "", "", "", ""
    
    if edit_run_id:
        run_data = next((r for r in st.session_state.data['runs'] if r['id'] == edit_run_id), None)
        if run_data:
            def_type = run_data['type']
            def_date = datetime.strptime(run_data['date'], '%Y-%m-%d').date()
            def_dist = run_data['distance']
            def_dur = run_data['duration']
            def_hr = run_data['avgHr']
            def_notes = run_data.get('notes', '')
            def_feel = run_data.get('feel', 'Normal')
            def_rpe = run_data.get('rpe', 5)
            def_z1 = format_duration(run_data.get('z1', 0))
            def_z2 = format_duration(run_data.get('z2', 0))
            def_z3 = format_duration(run_data.get('z3', 0))
            def_z4 = format_duration(run_data.get('z4', 0))
            def_z5 = format_duration(run_data.get('z5', 0))

    form_label = f":material/edit: Edit Activity" if edit_run_id else ":material/add_circle: Log Activity"
    expander_state = True if edit_run_id else False

    with st.expander(form_label, expanded=expander_state):
        if not edit_run_id:
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1:
                templates = st.session_state.data.get('templates', {})
                template_names = ["None"] + list(templates.keys())
                sel_template = st.selectbox(":material/folder_open: Load Template", template_names, label_visibility="collapsed")
                if sel_template != "None":
                    t_data = templates[sel_template]
                    def_type = t_data.get('type', "Run")
                    def_dist = t_data.get('distance', 5.0)
                    def_dur = t_data.get('duration', 30.0)
                    def_notes = t_data.get('notes', "")
                    st.session_state.form_act_type = def_type

        with st.form("run_form"):
            st.caption("Activity Type")
            act_type = st.radio("Type", ["Run", "Walk", "Ultimate"], index=["Run", "Walk", "Ultimate"].index(def_type) if def_type in ["Run", "Walk", "Ultimate"] else 0, key="act_type_radio", horizontal=True, label_visibility="collapsed")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Distance (km)")
                dist = st.number_input("Distance", min_value=0.0, step=0.01, value=float(def_dist), label_visibility="collapsed")
            with c2:
                st.caption("Duration (hh:mm:ss)")
                dur_str = st.text_input("Duration", value=format_duration(def_dur), placeholder="00:30:00", label_visibility="collapsed")
            c3, c4 = st.columns(2)
            with c3:
                st.caption("Avg HR")
                hr = st.number_input("Heart Rate", min_value=0, value=int(def_hr), label_visibility="collapsed")
            with c4:
                st.caption("RPE (1-10)")
                rpe = st.number_input("RPE", min_value=1, max_value=10, value=int(def_rpe), label_visibility="collapsed")
            st.caption("Heart Rate Zones (Time in mm:ss)")
            rc1, rc2, rc3, rc4, rc5 = st.columns(5)
            z1 = rc1.text_input("Zone 1", value=def_z1, placeholder="00:00")
            z2 = rc2.text_input("Zone 2", value=def_z2, placeholder="00:00")
            z3 = rc3.text_input("Zone 3", value=def_z3, placeholder="00:00")
            z4 = rc4.text_input("Zone 4", value=def_z4, placeholder="00:00")
            z5 = rc5.text_input("Zone 5", value=def_z5, placeholder="00:00")
            c5, c6 = st.columns(2)
            with c5:
                st.caption("How did it feel?")
                feel = st.radio("Feel", ["Good", "Normal", "Tired", "Pain"], index=["Good", "Normal", "Tired", "Pain"].index(def_feel) if def_feel in ["Good", "Normal", "Tired", "Pain"] else 1, horizontal=True, label_visibility="collapsed")
            with c6:
                st.caption("Date")
                act_date = st.date_input("Date", def_date, label_visibility="collapsed")
            st.caption("Notes")
            notes = st.text_area("Notes", value=def_notes, placeholder="Easy run, felt strong...", height=3, label_visibility="collapsed")
            btn_text = "Update Activity" if edit_run_id else "Save Activity"
            if st.form_submit_button(btn_text):
                new_id = int(time.time() * 1000)
                run_obj = {
                    "id": edit_run_id if edit_run_id else new_id,
                    "date": str(act_date), "type": act_type, "distance": dist, "duration": parse_time_input(dur_str),
                    "avgHr": hr, "rpe": rpe, "feel": feel, "z1": parse_time_input(z1), "z2": parse_time_input(z2),
                    "z3": parse_time_input(z3), "z4": parse_time_input(z4), "z5": parse_time_input(z5), "notes": notes
                }
                if edit_run_id:
                    idx = next((i for i, r in enumerate(st.session_state.data['runs']) if r['id'] == edit_run_id), -1)
                    if idx != -1: st.session_state.data['runs'][idx] = run_obj
                    st.session_state.edit_run_id = None
                    st.success("Activity Updated!")
                else:
                    st.session_state.data['runs'].insert(0, run_obj)
                    st.success("Activity Logged!")
                persist()
                st.rerun()
        if not edit_run_id:
            with st.popover(":material/save: Save as Template"):
                tpl_name = st.text_input("Template Name", placeholder="Morning 5k")
                if st.button("Save Template"):
                    if tpl_name:
                        st.session_state.data['templates'][tpl_name] = {"type": def_type, "distance": dist, "duration": parse_time_input(dur_str), "notes": notes}
                        persist()
                        st.success(f"Saved '{tpl_name}'!")
                        st.rerun()
        if edit_run_id:
            if st.button("Cancel Edit"):
                st.session_state.edit_run_id = None
                st.rerun()

    st.markdown("### Dashboard & History")
    tabs = st.tabs(["All Activities", "Run", "Walk", "Ultimate"])
    categories = ["All", "Run", "Walk", "Ultimate"]
    for i, tab in enumerate(tabs):
        with tab:
            filter_cat = categories[i]
            if not runs_df.empty:
                filtered_df = runs_df[runs_df['type'] == filter_cat] if filter_cat != "All" else runs_df
            else:
                filtered_df = pd.DataFrame(columns=['distance', 'duration', 'avgHr'])
            
            total_dist = filtered_df['distance'].sum() if not filtered_df.empty else 0
            total_mins = filtered_df['duration'].sum() if not filtered_df.empty else 0
            count = len(filtered_df)
            avg_hr = filtered_df['avgHr'].mean() if not filtered_df.empty and filtered_df['avgHr'].sum() > 0 else 0
            
            pace_label = "-"
            if total_dist > 0:
                avg_pace_val = total_mins / total_dist
                pace_label = format_pace(avg_pace_val) + " /km"
            t_hours = int(total_mins // 60)
            t_mins = int(total_mins % 60)
            time_label = f"{t_hours}h {t_mins}m"

            with st.container():
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Dist", f"{total_dist:.1f} km")
                m2.metric("Total Time", time_label)
                if filter_cat == "Ultimate": m3.metric("Activities", count)
                else: m3.metric("Avg Pace", pace_label)
                m4.metric("Avg HR", f"{int(avg_hr)} bpm")
                if filter_cat != "Ultimate": m5.metric("Count", count)
            st.divider()

            if not filtered_df.empty:
                for idx, row in filtered_df.iterrows():
                    with st.container():
                        c_main, c_stats, c_extra, c_act = st.columns([2, 3, 2, 1.5])
                        icon_map = {"Run": ":material/directions_run:", "Walk": ":material/directions_walk:", "Ultimate": ":material/sports_handball:"}
                        c_main.markdown(f"**{row['date']}**")
                        c_main.markdown(f"{icon_map.get(row['type'], ':material/help:')} {row['type']}")
                        stats_html = f"""
                        <div style="line-height: 1.4;">
                            <span class="history-sub">Dist:</span> <span class="history-value">{row['distance']}km</span><br>
                            <span class="history-sub">Time:</span> <span class="history-value">{format_duration(row['duration'])}</span><br>
                            <span class="history-sub">{'Note' if row['type'] == 'Ultimate' else 'Pace'}:</span> 
                            <span class="history-value">{row.get('notes','-') if row['type']=='Ultimate' else format_pace(row['duration']/row['distance'] if row['distance']>0 else 0)+'/km'}</span>
                        </div>
                        """
                        c_stats.markdown(stats_html, unsafe_allow_html=True)
                        feel_val = row.get('feel', '')
                        feel_emoji = {"Good": ":material/sentiment_satisfied:", "Normal": ":material/sentiment_neutral:", "Tired": ":material/sentiment_dissatisfied:", "Pain": ":material/sick:"}.get(feel_val, "")
                        hr_html = f"""
                        <div style="line-height: 1.4;">
                            <span class="history-sub">HR:</span> <span class="history-value">{row['avgHr'] if row['avgHr']>0 else '-'}</span><br>
                            <span class="history-sub">RPE:</span> <span class="history-value">{row.get('rpe', '-')}</span><br>
                            <span style="font-size:1.2rem;">{feel_emoji}</span>
                        </div>
                        """
                        c_extra.markdown(hr_html, unsafe_allow_html=True)
                        with c_act:
                            if st.button(":material/edit:", key=f"ed_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.edit_run_id = row['id']
                                st.rerun()
                            if st.button(":material/delete:", key=f"del_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.data['runs'] = [r for r in st.session_state.data['runs'] if r['id'] != row['id']]
                                persist()
                                st.rerun()
                        
                        # Details Expander
                        with st.expander("See Details", expanded=False):
                             dc1, dc2 = st.columns(2)
                             with dc1:
                                 st.markdown(f"**Notes:** {row.get('notes', '-')}")
                             with dc2:
                                 zones = []
                                 for z in range(1, 6):
                                     val = row.get(f'z{z}', 0)
                                     if val > 0: zones.append(f"**Z{z}:** {format_duration(val)}")
                                 if zones:
                                     st.markdown(" | ".join(zones))
                                 else:
                                     st.caption("No zone data")
            else:
                st.info("No activities found for this category.")

# --- TAB: GYM ---
elif selected_tab == "Gym":
    st.header(":material/fitness_center: Gym & Weights")
    
    # Initialize active workout session state
    if 'active_workout' not in st.session_state:
        st.session_state.active_workout = None
    
    # Save Dialog State
    if 'gym_save_dialog' not in st.session_state:
        st.session_state.gym_save_dialog = False

    # --- Mode 1: Selection Screen ---
    if st.session_state.active_workout is None and not st.session_state.gym_save_dialog:
        col_rout, col_hist = st.tabs(["Start Workout", "History"])
        
        with col_rout:
            st.subheader("Start from Routine")
            routine_opts = {r['name']: r for r in st.session_state.data['routines']}
            
            if routine_opts:
                sel_r_name = st.selectbox("Select Routine", list(routine_opts.keys()))
                if st.button(":material/play_arrow: Start Workout", use_container_width=True):
                    # Deep copy routine to active state
                    selected = routine_opts[sel_r_name]
                    # Transform structure for active logging: Add sets array
                    exercises_prep = []
                    for ex_name in selected['exercises']:
                        exercises_prep.append({
                            "name": ex_name,
                            "sets": [{"reps": "", "weight": ""} for _ in range(3)] # Default 3 empty sets
                        })
                    
                    st.session_state.active_workout = {
                        "routine_id": selected['id'],
                        "routine_name": selected['name'],
                        "date": datetime.now().date(),
                        "exercises": exercises_prep
                    }
                    st.rerun()
            else:
                st.info("No routines found. Create one below.")

            st.divider()
            with st.expander("Manage Routines"):
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
                
                for r in st.session_state.data['routines']:
                    c1, c2 = st.columns([5, 1])
                    c1.markdown(f"**{r['name']}**")
                    c1.caption(" • ".join(r['exercises']))
                    if c2.button(":material/delete:", key=f"del_rout_{r['id']}"):
                        st.session_state.data['routines'] = [x for x in st.session_state.data['routines'] if x['id'] != r['id']]
                        persist()
                        st.rerun()

        with col_hist:
            sessions = st.session_state.data['gym_sessions']
            if sessions:
                total_vol_all = sum(s.get('totalVolume', 0) for s in sessions)
                with st.container(border=True): st.metric("Total Volume Lifted", f"{total_vol_all/1000:.1f}k kg")
                st.divider()
                for s in sessions:
                    with st.container():
                        c1, c2, c3 = st.columns([3, 4, 1])
                        c1.markdown(f"**{s['date']}**")
                        c1.caption(s['routineName'])
                        details = ", ".join([f"{ex['name']} ({len(ex['sets'])})" for ex in s['exercises']])
                        c2.caption(details)
                        c2.text(f"Vol: {s.get('totalVolume',0)}kg")
                        if c3.button(":material/delete:", key=f"del_sess_{s['id']}"):
                            st.session_state.data['gym_sessions'] = [x for x in st.session_state.data['gym_sessions'] if x['id'] != s['id']]
                            persist()
                            st.rerun()
            else:
                st.info("No gym sessions logged.")

    # --- Mode 2: Active Logging Screen ---
    elif st.session_state.active_workout is not None and not st.session_state.gym_save_dialog:
        aw = st.session_state.active_workout
        
        # Header
        c_head, c_canc = st.columns([3, 1])
        c_head.subheader(f":material/fitness_center: {aw['routine_name']}")
        if c_canc.button("Cancel"):
            st.session_state.active_workout = None
            st.rerun()
            
        aw['date'] = st.date_input("Date", aw['date'])
        
        st.divider()
        
        # Exercises Loop
        # We iterate by index to modify in place
        exercises_to_remove = []
        
        for i, ex in enumerate(aw['exercises']):
            with st.container(border=True):
                # Header Row: Name | History | Remove
                ch1, ch2, ch3 = st.columns([3, 3, 1])
                new_name = ch1.text_input(f"Exercise {i+1}", value=ex['name'], key=f"ex_name_{i}")
                ex['name'] = new_name
                
                # History Lookup
                last_stats = get_last_lift_stats(new_name)
                if last_stats:
                    ch2.info(f"Last: {last_stats}")
                else:
                    ch2.caption("No history found")
                    
                if ch3.button(":material/delete:", key=f"del_ex_{i}"):
                    exercises_to_remove.append(i)
                
                # Sets Header
                st.markdown(f"""
                <div style="display:grid; grid-template-columns: 1fr 1fr 0.5fr; gap:10px; font-size:0.8rem; font-weight:600; color:#64748b; margin-bottom:5px;">
                    <div>REPS</div><div>WEIGHT (kg)</div><div></div>
                </div>
                """, unsafe_allow_html=True)
                
                # Sets Loop
                sets_to_remove = []
                for j, s in enumerate(ex['sets']):
                    c_reps, c_w, c_del = st.columns([1, 1, 0.5])
                    s['reps'] = c_reps.text_input("Reps", value=s['reps'], key=f"r_{i}_{j}", label_visibility="collapsed", placeholder="10")
                    s['weight'] = c_w.text_input("Weight", value=s['weight'], key=f"w_{i}_{j}", label_visibility="collapsed", placeholder="50")
                    if c_del.button(":material/close:", key=f"del_set_{i}_{j}"):
                        sets_to_remove.append(j)
                
                # Process Set Deletions
                if sets_to_remove:
                    for index in sorted(sets_to_remove, reverse=True):
                        del ex['sets'][index]
                    st.rerun()
                
                # Add Set Button
                if st.button(f":material/add: Add Set", key=f"add_set_{i}"):
                    ex['sets'].append({"reps": "", "weight": ""})
                    st.rerun()

        # Process Exercise Deletions
        if exercises_to_remove:
            for index in sorted(exercises_to_remove, reverse=True):
                del aw['exercises'][index]
            st.rerun()

        # Add New Exercise Button
        if st.button(":material/add_circle: Add New Exercise"):
            aw['exercises'].append({"name": "New Exercise", "sets": [{"reps": "", "weight": ""} for _ in range(3)]})
            st.rerun()
            
        st.divider()
        if st.button(":material/check_circle: Finish Workout", type="primary", use_container_width=True):
            st.session_state.gym_save_dialog = True
            st.rerun()

    # --- Mode 3: Save Dialog ---
    elif st.session_state.gym_save_dialog:
        st.subheader("🎉 Workout Complete!")
        st.info("You modified the routine structure. Would you like to update the original routine?")
        
        aw = st.session_state.active_workout
        
        c1, c2 = st.columns(2)
        
        # Calculate Volume & Clean Data
        final_exercises = []
        total_vol = 0
        current_ex_names = []
        
        for ex in aw['exercises']:
            clean_sets = []
            for s in ex['sets']:
                # Basic validation: check if valid numbers
                try:
                    r_val = float(s['reps'])
                    w_val = float(s['weight'])
                    clean_sets.append({"reps": s['reps'], "weight": s['weight']}) # Store as string for flexibility, calc with float
                    total_vol += r_val * w_val
                except:
                    continue # Skip empty/invalid sets
            
            if clean_sets: # Only save exercises with valid sets
                final_exercises.append({
                    "name": ex['name'],
                    "sets": clean_sets
                })
                current_ex_names.append(ex['name'])

        new_session = {
            "id": int(time.time()),
            "date": str(aw['date']),
            "routineName": aw['routine_name'],
            "exercises": final_exercises,
            "totalVolume": total_vol
        }

        # Option 1: Update Routine
        if c1.button(":material/update: Save & Update Routine"):
            # Update Routine Definition
            for r in st.session_state.data['routines']:
                if r['id'] == aw['routine_id']:
                    r['exercises'] = current_ex_names
                    break
            
            # Save Session
            st.session_state.data['gym_sessions'].insert(0, new_session)
            persist()
            
            # Reset State
            st.session_state.active_workout = None
            st.session_state.gym_save_dialog = False
            st.success("Routine updated and workout logged!")
            st.rerun()

        # Option 2: Just Save
        if c2.button(":material/save: Just Save Session"):
            st.session_state.data['gym_sessions'].insert(0, new_session)
            persist()
            
            st.session_state.active_workout = None
            st.session_state.gym_save_dialog = False
            st.success("Workout logged!")
            st.rerun()
            
        if st.button("Go Back"):
            st.session_state.gym_save_dialog = False
            st.rerun()

# --- TAB: NUTRITION ---
elif selected_tab == "Nutrition":
    st.header(":material/restaurant: Nutrition Log")
    c1, c2 = st.columns([1, 2])
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
        lbl = ":material/edit: Edit Meal" if edit_nut_id else "Add Meal"
        st.subheader(lbl)
        with st.form("food_form"):
            f_date = st.date_input("Date", def_nut_date)
            meal = st.text_input("Meal Name", value=def_meal, placeholder="Chicken Rice")
            cal = st.number_input("Calories", value=int(def_cal), min_value=0, step=50)
            prot = st.number_input("Protein (g)", value=int(def_prot), min_value=0, step=1)
            carbs = st.number_input("Carbs (g)", value=int(def_carb), min_value=0, step=1)
            fat = st.number_input("Fat (g)", value=int(def_fat), min_value=0, step=1)
            btn_txt = "Update Meal" if edit_nut_id else "Add Meal"
            if st.form_submit_button(btn_txt):
                nut_obj = {"id": edit_nut_id if edit_nut_id else int(time.time()), "date": str(f_date), "meal": meal, "calories": cal, "protein": prot, "carbs": carbs, "fat": fat}
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
        st.divider()
        st.subheader("Recent Meals")
        for n in st.session_state.data['nutrition_logs']:
             with st.container():
                 # Mobile optimized cols
                 nc1, nc2, nc_act = st.columns([2, 4, 1.5])
                 nc1.markdown(f"**{n['date']}**")
                 
                 macro_html = f"""
                 <div style="line-height:1.2;">
                    <span style="font-weight:600; color:#334155;">{n['meal']}</span><br>
                    <span style="font-size:0.85rem; color:#64748b;">{n['calories']} kcal</span> 
                    <span style="font-size:0.75rem; color:#94a3b8;">(P:{n['protein']} C:{n['carbs']} F:{n['fat']})</span>
                 </div>
                 """
                 nc2.markdown(macro_html, unsafe_allow_html=True)
                 with nc_act:
                    if st.button(":material/edit:", key=f"edit_nut_{n['id']}"):
                        st.session_state.edit_nut_id = n['id']
                        st.rerun()
                    if st.button(":material/delete:", key=f"del_nut_{n['id']}"):
                        st.session_state.data['nutrition_logs'] = [x for x in st.session_state.data['nutrition_logs'] if x['id'] != n['id']]
                        persist()
                        st.rerun()

# --- TAB: STATS (HEALTH) ---
elif selected_tab == "Stats":
    st.header(":material/favorite: Physiological Stats")
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

    lbl_h = ":material/edit: Edit Stats" if edit_hlth_id else ":material/add_circle: Log Health Stats"
    expanded_h = True if edit_hlth_id else False

    with st.expander(lbl_h, expanded=expanded_h):
        with st.form("health_form"):
            h_date = st.date_input("Date", def_h_date)
            c1, c2 = st.columns(2)
            rhr = c1.number_input("Resting HR", min_value=30, max_value=150, value=int(def_rhr))
            hrv = c2.number_input("HRV (ms)", min_value=0, value=int(def_hrv))
            c3, c4 = st.columns(2)
            vo2 = c3.number_input("VO2 Max", min_value=0.0, value=float(def_vo2), step=0.1)
            sleep = c4.number_input("Sleep (hrs)", min_value=0.0, value=float(def_sleep), step=0.1)
            btn_h_txt = "Update Stats" if edit_hlth_id else "Log Stats"
            if st.form_submit_button(btn_h_txt):
                new_h = {"id": edit_hlth_id if edit_hlth_id else int(time.time()), "date": str(h_date), "rhr": rhr, "hrv": hrv, "vo2Max": vo2, "sleepHours": sleep}
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
        health_df['date'] = pd.to_datetime(health_df['date'])
        health_df = health_df.sort_values(by='date')
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                fig_hrv = px.line(health_df, x='date', y='hrv', title="HRV Trends", markers=True)
                fig_hrv.update_traces(line_color='#22c55e')
                fig_hrv.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter", margin=dict(l=20, r=20, t=40, b=20), height=250)
                st.plotly_chart(fig_hrv, use_container_width=True)
        with c2:
            with st.container(border=True):
                fig_sleep = px.bar(health_df, x='date', y='sleepHours', title="Sleep Duration")
                fig_sleep.update_traces(marker_color='#6366f1')
                fig_sleep.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_family="Inter", margin=dict(l=20, r=20, t=40, b=20), height=250)
                st.plotly_chart(fig_sleep, use_container_width=True)
        
        st.divider()
        st.subheader("History")
        list_h_df = health_df.sort_values(by='date', ascending=False)
        for index, row in list_h_df.iterrows():
             with st.container():
                 # Mobile Optimized 3-col layout
                 hc1, hc2, hc3 = st.columns([2, 4, 1.5])
                 hc1.markdown(f"**{row['date'].date()}**")
                 
                 stats_str = f"""
                 <div style="line-height:1.4;">
                    <span class="history-sub">RHR:</span> <b>{row['rhr']}</b> &nbsp; 
                    <span class="history-sub">HRV:</span> <b>{row['hrv']}</b><br>
                    <span class="history-sub">VO2:</span> <b>{row['vo2Max']}</b> &nbsp;
                    <span class="history-sub">Sleep:</span> <b>{row['sleepHours']}h</b>
                 </div>
                 """
                 hc2.markdown(stats_str, unsafe_allow_html=True)
                 
                 with hc3:
                    if st.button(":material/edit:", key=f"edit_h_{row['id']}"):
                        st.session_state.edit_hlth_id = row['id']
                        st.rerun()
                    if st.button(":material/delete:", key=f"del_h_{row['id']}"):
                        st.session_state.data['health_logs'] = [x for x in st.session_state.data['health_logs'] if x['id'] != row['id']]
                        persist()
                        st.rerun()
    else:
        st.info("No health stats logged yet.")
