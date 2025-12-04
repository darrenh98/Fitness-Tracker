import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta, date
import time
import copy
import re
import math
import streamlit.components.v1 as components

# Try to import docx, handle if not installed immediately
try:
    from docx import Document
except ImportError:
    Document = None

# --- Configuration & Styling ---
st.set_page_config(
    page_title="RunLog Hub",
    page_icon=":material/sprint:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1e293b;
    }

    .stApp {
        background-color: #f8fafc;
    }

    /* Material Icon Class for HTML usage */
    .material-symbols-rounded {
        font-family: 'Material Symbols Rounded';
        font-weight: normal;
        font-style: normal;
        font-size: 1.2rem;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        vertical-align: middle;
        color: #64748b;
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
        border: 1px solid #e2e8f0; /* Slightly darker border for better visibility */
        margin-bottom: 1.0rem;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.05);
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
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] > [data-testid="stContainer"] {
            padding: 0.75rem;
        }
    }
    
    /* Status Badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
        display: inline-block;
    }
    .status-red { background-color: #fee2e2; color: #991b1b; }
    .status-orange { background-color: #ffedd5; color: #9a3412; }
    .status-green { background-color: #dcfce7; color: #166534; }
    .status-gray { background-color: #f1f5f9; color: #475569; }
</style>
""", unsafe_allow_html=True)

# --- Physiology Engine ---
class PhysiologyEngine:
    def __init__(self, user_profile):
        """
        Initialize with user object containing:
        hr_max, hr_rest, vo2_max, gender ('male'/'female')
        zones: dict with keys 'z1', 'z2', 'z3', 'z4', 'z5' containing UPPER limits
        """
        self.hr_max = float(user_profile.get('hrMax', 190))
        self.hr_rest = float(user_profile.get('hrRest', 60))
        self.vo2_max = float(user_profile.get('vo2Max', 45))
        self.gender = user_profile.get('gender', 'Male').lower()
        self.zones = user_profile.get('zones', {})

    def calculate_trimp(self, duration_min, avg_hr=None, zones=None):
        """
        Calculates Training Impulse (TRIMP) using Banister's formula.
        Fallback to Zone-based load if Avg HR is missing.
        """
        if avg_hr and avg_hr > 0:
            # Banister's Impulse Response
            hr_reserve = (avg_hr - self.hr_rest) / (self.hr_max - self.hr_rest)
            # Clamp reserve between 0 and 1 for safety
            hr_reserve = max(0.0, min(1.0, hr_reserve))
            
            exponent = 1.92 if self.gender == 'male' else 1.67
            trimp = duration_min * hr_reserve * 0.64 * math.exp(exponent * hr_reserve)
            return trimp
        
        elif zones:
            # If user has defined accurate zone boundaries, use them for granular Banister calc
            # Otherwise fallback to static multipliers
            if self.zones and len(self.zones) == 5:
                total_trimp = 0
                # Assume Z1 starts at HR Rest. 
                # We iterate through zones Z1 to Z5
                prev_limit = self.hr_rest 
                zone_keys = ['z1', 'z2', 'z3', 'z4', 'z5']
                
                for i, duration in enumerate(zones):
                    if duration <= 0: continue
                    
                    key = zone_keys[i]
                    upper = float(self.zones.get(key, 0))
                    if upper == 0: continue 
                    
                    # Calculate Representative HR for this zone (Midpoint)
                    avg_zone_hr = (prev_limit + upper) / 2
                    
                    # Calculate HR Reserve for this specific zone midpoint
                    hr_reserve = (avg_zone_hr - self.hr_rest) / (self.hr_max - self.hr_rest)
                    hr_reserve = max(0.0, min(1.0, hr_reserve))
                    
                    exponent = 1.92 if self.gender == 'male' else 1.67
                    
                    # Calculate Load for this segment
                    segment_load = duration * hr_reserve * 0.64 * math.exp(exponent * hr_reserve)
                    total_trimp += segment_load
                    
                    # Set lower bound for next zone
                    prev_limit = upper
                
                return total_trimp
            else:
                # Fallback: Zone Multipliers (Standard approximations)
                # Zones input expected as list of minutes [z1, z2, z3, z4, z5]
                multipliers = [0.8, 1.5, 2.8, 4.5, 7.0]
                load = sum(z * m for z, m in zip(zones, multipliers))
                return load
        
        return 0.0

    def get_training_effect(self, trimp_score):
        """
        Scales raw TRIMP to a 0.0-5.0 Training Effect score based on VO2 Max.
        """
        # Scaling factor: Higher VO2 max needs more load to get same effect
        # Using approximation: scaling ~ vo2_max * 1.5
        scaling_factor = self.vo2_max * 1.5
        if scaling_factor == 0: return 0.0
        
        te = trimp_score / scaling_factor
        return round(min(5.0, te), 1)

    def calculate_training_status(self, activity_history):
        """
        Calculates Acute:Chronic Workload Ratio (ACWR) and Status.
        activity_history: list of dicts with {'date': 'YYYY-MM-DD', 'load': float}
        """
        today = datetime.now().date()
        
        # Setup date buckets
        acute_start = today - timedelta(days=6) # Last 7 days
        chronic_start = today - timedelta(days=27) # Last 28 days
        
        acute_load = 0
        chronic_load_total = 0
        
        for activity in activity_history:
            act_date = datetime.strptime(activity['date'], '%Y-%m-%d').date()
            load = activity.get('load', 0)
            
            if acute_start <= act_date <= today:
                acute_load += load
                
            if chronic_start <= act_date <= today:
                chronic_load_total += load
        
        # Chronic Load is normalized to a weekly view (Total / 4)
        chronic_load_weekly = chronic_load_total / 4.0 if chronic_load_total > 0 else 1.0 # Avoid div/0
        
        ratio = acute_load / chronic_load_weekly
        
        # Status Logic
        status = "Recovery"
        color_class = "status-gray"
        description = "Load is very low. You are detraining or recovering."

        if ratio > 1.5:
            status = "Overreaching"
            color_class = "status-red"
            description = "High injury risk! Workload spike is too high."
        elif 1.3 <= ratio <= 1.5:
            status = "High Strain"
            color_class = "status-orange"
            description = "Caution: You are increasing load rapidly."
        elif 0.8 <= ratio < 1.3:
            if acute_load > chronic_load_weekly:
                status = "Productive"
                color_class = "status-green"
                description = "Optimal zone. You are building fitness."
            else:
                status = "Maintaining"
                color_class = "status-green"
                description = "Load is consistent. Fitness is stable."
        else:
            # < 0.8
            status = "Recovery / Detraining"
            color_class = "status-gray"
            description = "Workload is decreasing. Good for taper weeks."

        return {
            "acute": round(acute_load),
            "chronic": round(chronic_load_weekly),
            "ratio": round(ratio, 2),
            "status": status,
            "css": color_class,
            "desc": description
        }

# --- Data Persistence Helper ---
DATA_FILE = "run_tracker_data.json"

DEFAULT_DATA = {
    "runs": [],
    "health_logs": [],
    "gym_sessions": [],
    "routines": [
        {"id": 1, "name": "Leg Day", "exercises": ["Squats", "Split Squats", "Glute Bridges", "Calf Raises"]},
        {"id": 2, "name": "Upper Body", "exercises": ["Bench Press", "Pull Ups", "Overhead Press", "Rows"]}
    ],
    # Enhanced User Profile Defaults
    "user_profile": {
        "age": 30, "height": 175, "weight": 70, "heightUnit": "cm", "weightUnit": "kg",
        "gender": "Male", "hrMax": 190, "hrRest": 60, "vo2Max": 45,
        "zones": {"z1": 130, "z2": 145, "z3": 160, "z4": 175, "z5": 190} # Default Upper Limits
    },
    "cycles": {"macro": "", "meso": "", "micro": ""},
    "weekly_plan": {day: {"am": "", "pm": ""} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Migration: Ensure new profile fields exist
            if 'gender' not in data.get('user_profile', {}):
                data['user_profile']['gender'] = "Male"
                data['user_profile']['hrMax'] = 190
                data['user_profile']['hrRest'] = 60
                data['user_profile']['vo2Max'] = 45
            if 'zones' not in data.get('user_profile', {}):
                data['user_profile']['zones'] = {"z1": 130, "z2": 145, "z3": 160, "z4": 175, "z5": 190}
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

def get_last_lift_stats(ex_name):
    sessions = st.session_state.data.get('gym_sessions', [])
    if not sessions:
        return None
    for s in sessions:
        for ex in s['exercises']:
            if ex['name'].lower() == ex_name.lower():
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
        
def scroll_to_top():
    """Injects JS to scroll to top of page"""
    js = """
    <script>
        var body = window.parent.document.querySelector(".main");
        if (body) { body.scrollTop = 0; }
    </script>
    """
    components.html(js, height=0)

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
                line = f"- {r['date'][5:]}: {r['type']} {r['distance']}km @ {format_duration(r['duration'])}"
                if r['type'] != 'Ultimate' and r['distance'] > 0:
                    pace = r['duration'] / r['distance']
                    line += f" ({format_pace(pace)}/km)"
                hr = f"{r['avgHr']}bpm" if r['avgHr'] > 0 else ""
                feel = r.get('feel', '')
                if hr or feel:
                    line += f" | {hr} {feel}"
                report.append(line)
                
                details = []
                if r.get('cadence', 0) > 0: details.append(f"Cad: {r['cadence']}")
                if r.get('power', 0) > 0: details.append(f"Pwr: {r['power']}w")
                if r.get('notes'): details.append(f"📝 {r['notes']}")
                
                zones = []
                for i in range(1, 6):
                    z_val = r.get(f'z{i}', 0)
                    if z_val > 0: zones.append(f"Z{i}:{format_duration(z_val)}")
                if zones: details.append(f"Zones: {', '.join(zones)}")
                
                if details: report.append(f"   {' | '.join(details)}")
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
    # Renamed "Stats" to "Physio" to reflect advanced dashboard
    selected_tab = st.radio("Navigate", ["Plan", "Field (Runs)", "Gym", "Physio", "Trends", "Share"], label_visibility="collapsed")
    st.divider()
    
    with st.expander("👤 Athlete Profile"):
        prof = st.session_state.data['user_profile']
        
        # Basic
        c1, c2 = st.columns(2)
        new_weight = c1.number_input("Weight (kg)", value=float(prof.get('weight', 70)), key="prof_weight")
        new_height = c2.number_input("Height (cm)", value=float(prof.get('height', 175)), key="prof_height")
        
        # Physio Params
        gender = st.selectbox("Gender", ["Male", "Female"], index=0 if prof.get('gender','Male') == 'Male' else 1)
        c3, c4, c5 = st.columns(3)
        hr_max = c3.number_input("Max HR", value=int(prof.get('hrMax', 190)))
        hr_rest = c4.number_input("Rest HR", value=int(prof.get('hrRest', 60)))
        vo2 = c5.number_input("VO2 Max", value=float(prof.get('vo2Max', 45)))

        st.markdown("**Heart Rate Zones (Upper Limits)**")
        cz = prof.get('zones', {"z1": 130, "z2": 145, "z3": 160, "z4": 175, "z5": 190})
        z1_u = st.number_input("Zone 1 Max", value=int(cz.get('z1', 130)))
        z2_u = st.number_input("Zone 2 Max", value=int(cz.get('z2', 145)))
        z3_u = st.number_input("Zone 3 Max", value=int(cz.get('z3', 160)))
        z4_u = st.number_input("Zone 4 Max", value=int(cz.get('z4', 175)))
        z5_u = st.number_input("Zone 5 Max", value=int(cz.get('z5', 190)))

        if st.button("Save Profile"):
            st.session_state.data['user_profile'].update({
                'weight': new_weight, 'height': new_height, 'gender': gender,
                'hrMax': hr_max, 'hrRest': hr_rest, 'vo2Max': vo2,
                'zones': {"z1": z1_u, "z2": z2_u, "z3": z3_u, "z4": z4_u, "z5": z5_u}
            })
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
    
    # Toast Logic
    if 'run_log_success' in st.session_state and st.session_state.run_log_success:
        st.toast("✅ Activity Logged Successfully!")
        st.session_state.run_log_success = False

    edit_run_id = st.session_state.get('edit_run_id', None)
    if 'form_act_type' not in st.session_state: st.session_state.form_act_type = "Run"
    
    # NO SMART DEFAULTS (Reset to 0)
    def_type = st.session_state.form_act_type
    def_date = datetime.now()
    def_dist = 0.0
    def_dur = 0.0 # Will render as empty string or "00:00:00"
    def_hr = 0
    def_cad = 0
    def_pwr = 0
    def_notes = ""
    def_feel = "Normal"
    def_rpe = 5
    def_z1, def_z2, def_z3, def_z4, def_z5 = "", "", "", "", ""
    
    if edit_run_id:
        run_data = next((r for r in st.session_state.data['runs'] if r['id'] == edit_run_id), None)
        if run_data:
            def_type = run_data['type']
            def_date = datetime.strptime(run_data['date'], '%Y-%m-%d').date()
            def_dist = run_data['distance']
            def_dur = run_data['duration']
            def_hr = run_data['avgHr']
            def_cad = run_data.get('cadence', 0)
            def_pwr = run_data.get('power', 0)
            def_notes = run_data.get('notes', '')
            def_feel = run_data.get('feel', 'Normal')
            def_rpe = run_data.get('rpe', 5)
            def_z1 = format_duration(run_data.get('z1', 0))
            def_z2 = format_duration(run_data.get('z2', 0))
            def_z3 = format_duration(run_data.get('z3', 0))
            def_z4 = format_duration(run_data.get('z4', 0))
            def_z5 = format_duration(run_data.get('z5', 0))
            
            # Scroll to top when editing is activated (and we are rendering the edit form)
            scroll_to_top()

    form_label = f":material/edit: Edit Activity" if edit_run_id else ":material/add_circle: Log Activity"
    # Auto collapse if not editing
    expander_state = True if edit_run_id else False

    with st.expander(form_label, expanded=expander_state):
        # Dynamic key suffix to ensure fresh form state when switching between entries or modes
        key_suffix = f"{edit_run_id}" if edit_run_id else "new"

        # Clear on submit resets the form to empty/0 values automatically
        with st.form("run_form", clear_on_submit=True):
            # Row 1: Date | Type
            c_d, c_t = st.columns([1, 3])
            with c_d:
                st.caption("Date")
                act_date = st.date_input("Date", def_date, label_visibility="collapsed", key=f"date_{key_suffix}")
            with c_t:
                st.caption("Activity Type")
                # Correctly set index based on def_type (which comes from run_data in Edit mode)
                type_idx = ["Run", "Walk", "Ultimate"].index(def_type) if def_type in ["Run", "Walk", "Ultimate"] else 0
                act_type = st.radio("Type", ["Run", "Walk", "Ultimate"], index=type_idx, key=f"type_{key_suffix}", horizontal=True, label_visibility="collapsed")
            
            # Row 2: Dist | Duration
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Distance (km)")
                # Use None for placeholder effect if default is 0.0 and not editing
                dist_val = float(def_dist) if edit_run_id or def_dist > 0 else None
                dist = st.number_input("Distance", min_value=0.0, step=0.01, value=dist_val, placeholder="0.00", label_visibility="collapsed", key=f"dist_{key_suffix}")
            with c2:
                st.caption("Duration (hh:mm:ss)")
                # If new log, show empty string so placeholder shows "00:30:00"
                dur_val = format_duration(def_dur) if edit_run_id or def_dur > 0 else ""
                dur_str = st.text_input("Duration", value=dur_val, placeholder="00:30:00", label_visibility="collapsed", key=f"dur_{key_suffix}")
            
            c3, c4, c5, c6 = st.columns(4)
            with c3:
                st.caption("Avg HR")
                hr = st.number_input("Heart Rate", min_value=0, value=int(def_hr), label_visibility="collapsed", key=f"hr_{key_suffix}")
            with c4:
                st.caption("RPE (1-10)")
                rpe = st.number_input("RPE", min_value=1, max_value=10, value=int(def_rpe), label_visibility="collapsed", key=f"rpe_{key_suffix}")
            with c5:
                st.caption("Cadence (spm)")
                cadence = st.number_input("Cadence", min_value=0, value=int(def_cad), label_visibility="collapsed", key=f"cad_{key_suffix}")
            with c6:
                st.caption("Power (w)")
                power = st.number_input("Power", min_value=0, value=int(def_pwr), label_visibility="collapsed", key=f"pwr_{key_suffix}")

            st.caption("Heart Rate Zones (Time in mm:ss)")
            rc1, rc2, rc3, rc4, rc5 = st.columns(5)
            z1 = rc1.text_input("Zone 1", value=def_z1, placeholder="00:00", key=f"z1_{key_suffix}")
            z2 = rc2.text_input("Zone 2", value=def_z2, placeholder="00:00", key=f"z2_{key_suffix}")
            z3 = rc3.text_input("Zone 3", value=def_z3, placeholder="00:00", key=f"z3_{key_suffix}")
            z4 = rc4.text_input("Zone 4", value=def_z4, placeholder="00:00", key=f"z4_{key_suffix}")
            z5 = rc5.text_input("Zone 5", value=def_z5, placeholder="00:00", key=f"z5_{key_suffix}")
            
            c_feel, c_date = st.columns(2)
            with c_feel:
                st.caption("How did it feel?")
                feel_idx = ["Good", "Normal", "Tired", "Pain"].index(def_feel) if def_feel in ["Good", "Normal", "Tired", "Pain"] else 1
                feel = st.radio("Feel", ["Good", "Normal", "Tired", "Pain"], index=feel_idx, horizontal=True, label_visibility="collapsed", key=f"feel_{key_suffix}")
            
            st.caption("Notes")
            notes = st.text_area("Notes", value=def_notes, placeholder="Easy run, felt strong...", height=3, label_visibility="collapsed", key=f"notes_{key_suffix}")
            
            btn_text = "Update Activity" if edit_run_id else "Save Activity"
            
            if st.form_submit_button(btn_text):
                new_id = int(time.time() * 1000)
                # Handle None distance input
                dist_save = dist if dist is not None else 0.0
                
                run_obj = {
                    "id": edit_run_id if edit_run_id else new_id,
                    "date": str(act_date), "type": act_type, "distance": dist_save, 
                    "duration": parse_time_input(dur_str),
                    "avgHr": hr, "rpe": rpe, "feel": feel, 
                    "cadence": cadence, "power": power,
                    "z1": parse_time_input(z1), "z2": parse_time_input(z2),
                    "z3": parse_time_input(z3), "z4": parse_time_input(z4), "z5": parse_time_input(z5), 
                    "notes": notes
                }
                if edit_run_id:
                    idx = next((i for i, r in enumerate(st.session_state.data['runs']) if r['id'] == edit_run_id), -1)
                    if idx != -1: st.session_state.data['runs'][idx] = run_obj
                    st.session_state.edit_run_id = None
                    st.session_state.run_log_success = True
                else:
                    st.session_state.data['runs'].insert(0, run_obj)
                    st.session_state.run_log_success = True
                
                persist()
                st.rerun()
        
        if edit_run_id:
            if st.button("Cancel Edit"):
                st.session_state.edit_run_id = None
                st.rerun()

    st.markdown("### Dashboard & History")
    
    # --- NEW DATE CONTROLS ---
    if 'dash_period' not in st.session_state: st.session_state.dash_period = "Weekly"
    if 'dash_offset' not in st.session_state: st.session_state.dash_offset = 0

    def get_date_range(period, offset):
        today = datetime.now().date()
        
        if period == "Weekly":
            # Start of week = Monday
            start_of_week = today - timedelta(days=today.weekday())
            start_date = start_of_week - timedelta(weeks=offset)
            end_date = start_date + timedelta(days=6)
            label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
            
        elif period == "Monthly":
            # Calculate month based on offset
            total_months = today.year * 12 + today.month - 1 - offset
            year = total_months // 12
            month = total_months % 12 + 1
            start_date = date(year, month, 1)
            
            # Last day is day before next month start
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            label = start_date.strftime("%B %Y")

        elif period == "6 Months":
            current_half = 0 if today.month <= 6 else 1
            total_halves = today.year * 2 + current_half - offset
            year = total_halves // 2
            half = total_halves % 2
            if half == 0:
                start_date = date(year, 1, 1)
                end_date = date(year, 6, 30)
                label = f"H1 {year} (Jan - Jun)"
            else:
                start_date = date(year, 7, 1)
                end_date = date(year, 12, 31)
                label = f"H2 {year} (Jul - Dec)"
                
        else: # Yearly
            target_year = today.year - offset
            start_date = date(target_year, 1, 1)
            end_date = date(target_year, 12, 31)
            label = str(target_year)
            
        return start_date, end_date, label

    # UI for Controls
    with st.container(border=True):
        c_p, c_nav = st.columns([1.5, 2.5])
        with c_p:
            new_p = st.selectbox("View Period", ["Weekly", "Monthly", "6 Months", "Yearly"], 
                                 index=["Weekly", "Monthly", "6 Months", "Yearly"].index(st.session_state.dash_period), 
                                 label_visibility="collapsed")
            if new_p != st.session_state.dash_period:
                st.session_state.dash_period = new_p
                st.session_state.dash_offset = 0
                st.rerun()
        
        start_d, end_d, d_label = get_date_range(st.session_state.dash_period, st.session_state.dash_offset)
        
        with c_nav:
            c_prev, c_lbl, c_next = st.columns([1, 2, 1])
            if c_prev.button("◀", use_container_width=True):
                st.session_state.dash_offset += 1
                st.rerun()
            c_lbl.markdown(f"<div style='text-align: center; padding-top: 5px; font-weight: 600; color: #334155;'>{d_label}</div>", unsafe_allow_html=True)
            if c_next.button("▶", use_container_width=True, disabled=(st.session_state.dash_offset <= 0)):
                st.session_state.dash_offset -= 1
                st.rerun()

    # Filter Dataframe based on Period
    period_runs_df = pd.DataFrame(columns=runs_df.columns)
    if not runs_df.empty:
        # Ensure we have datetime objects
        runs_df['dt_obj'] = pd.to_datetime(runs_df['date']).dt.date
        # Filter
        period_runs_df = runs_df[ (runs_df['dt_obj'] >= start_d) & (runs_df['dt_obj'] <= end_d) ]

    tabs = st.tabs(["All Activities", "Run", "Walk", "Ultimate"])
    categories = ["All", "Run", "Walk", "Ultimate"]
    for i, tab in enumerate(tabs):
        with tab:
            filter_cat = categories[i]
            if not period_runs_df.empty:
                filtered_df = period_runs_df[period_runs_df['type'] == filter_cat] if filter_cat != "All" else period_runs_df
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
                # Sort Chronologically: Latest First
                filtered_df = filtered_df.sort_values(by='dt_obj', ascending=False)

                for idx, row in filtered_df.iterrows():
                    with st.container(border=True):
                        c_main, c_stats, c_extra, c_act = st.columns([2, 3, 2, 1.5])
                        icon_map = {"Run": ":material/directions_run:", "Walk": ":material/directions_walk:", "Ultimate": ":material/sports_handball:"}
                        
                        # Date Formatting: Friday, Dec 05
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        date_str = date_obj.strftime('%A, %b %d')
                        
                        c_main.markdown(f"**{date_str}**")
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
                        feel_emoji = {
                            "Good": '<span class="material-symbols-rounded">sentiment_satisfied</span>',
                            "Normal": '<span class="material-symbols-rounded">sentiment_neutral</span>',
                            "Tired": '<span class="material-symbols-rounded">sentiment_dissatisfied</span>',
                            "Pain": '<span class="material-symbols-rounded">sick</span>'
                        }.get(feel_val, "")
                        
                        # NEW METRICS HTML BLOCK (No Expander)
                        metrics_list = []
                        if row['avgHr'] > 0: metrics_list.append(f"<span class='history-sub'>HR:</span> <span class='history-value'>{row['avgHr']}</span>")
                        metrics_list.append(f"<span class='history-sub'>RPE:</span> <span class='history-value'>{row.get('rpe', '-')}</span>")
                        if row.get('cadence', 0) > 0: metrics_list.append(f"<span class='history-sub'>Cad:</span> <span class='history-value'>{row['cadence']}</span>")
                        if row.get('power', 0) > 0: metrics_list.append(f"<span class='history-sub'>Pwr:</span> <span class='history-value'>{row['power']}</span>")
                        
                        metrics_html = "<div style='line-height: 1.4;'>" + "<br>".join(metrics_list) + "</div>"
                        metrics_html += f"<div style='margin-top:4px;'>{feel_emoji}</div>"
                        c_extra.markdown(metrics_html, unsafe_allow_html=True)

                        with c_act:
                            if st.button(":material/edit:", key=f"ed_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.edit_run_id = row['id']
                                st.rerun()
                            if st.button(":material/delete:", key=f"del_{row['id']}_{idx}_{filter_cat}"):
                                st.session_state.data['runs'] = [r for r in st.session_state.data['runs'] if r['id'] != row['id']]
                                persist()
                                st.rerun()
                        
                        # Render Zones (Stacked Bar - Improved)
                        z_vals = [row.get(f'z{i}', 0) for i in range(1, 6)]
                        total_z_time = sum(z_vals)
                        if total_z_time > 0:
                            pcts = [(v/total_z_time)*100 for v in z_vals]
                            t_strs = [format_duration(v) if v > 0 else "" for v in z_vals]
                            
                            # Helper to decide if text fits
                            def get_lbl(pct, txt): return txt if pct > 10 else ""
                            
                            bar_html = f"""
                            <div style="display: flex; width: 100%; height: 18px; border-radius: 4px; overflow: hidden; margin-top: 8px; background-color: #f1f5f9;">
                                <div style="width: {pcts[0]}%; background-color: #1e40af; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[0], t_strs[0])}</div>
                                <div style="width: {pcts[1]}%; background-color: #60a5fa; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[1], t_strs[1])}</div>
                                <div style="width: {pcts[2]}%; background-color: #facc15; color: black; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[2], t_strs[2])}</div>
                                <div style="width: {pcts[3]}%; background-color: #fb923c; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[3], t_strs[3])}</div>
                                <div style="width: {pcts[4]}%; background-color: #f87171; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[4], t_strs[4])}</div>
                            </div>
                            """
                            st.markdown(bar_html, unsafe_allow_html=True)

                        # Notes (if any)
                        if row.get('notes'):
                             st.markdown(f"<div style='margin-top:5px; font-size:0.85rem; color:#475569;'>📝 {row['notes']}</div>", unsafe_allow_html=True)

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

# --- TAB: PHYSIO (UPDATED) ---
elif selected_tab == "Physio":
    st.header(":material/monitor_heart: Physiological Status")
    
    # Initialize Engine
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    
    # Calculate Metrics for History
    history_data = []
    runs = st.session_state.data['runs']
    for r in runs:
        # Prepare Zones list
        zones = [
            float(r.get('z1', 0)), float(r.get('z2', 0)), 
            float(r.get('z3', 0)), float(r.get('z4', 0)), 
            float(r.get('z5', 0))
        ]
        
        trimp = engine.calculate_trimp(
            duration_min=float(r['duration']),
            avg_hr=int(r['avgHr']),
            zones=zones
        )
        
        te = engine.get_training_effect(trimp)
        
        history_data.append({
            'date': r['date'],
            'load': trimp,
            'te': te,
            'type': r['type'],
            'dist': r['distance']
        })
        
    # Calculate Status
    status_data = engine.calculate_training_status(history_data)
    
    # --- DASHBOARD UI ---
    
    # 1. Status Card
    with st.container(border=True):
        st.subheader("Training Status")
        
        sc1, sc2 = st.columns([3, 2])
        
        with sc1:
            st.markdown(f"""
            <div style="background-color: {status_data['css'] == 'status-green' and '#dcfce7' or status_data['css'] == 'status-red' and '#fee2e2' or status_data['css'] == 'status-orange' and '#ffedd5' or '#f1f5f9'}; 
                        padding: 1rem; border-radius: 12px; border: 1px solid #e2e8f0;">
                <h2 style="margin:0; color: #0f172a;">{status_data['status']}</h2>
                <p style="margin:5px 0 0 0; color: #475569;">{status_data['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with sc2:
            ratio_val = status_data['ratio']
            st.metric("Acute:Chronic Ratio", ratio_val, delta=None)
            # Simple gauge visual
            gauge_html = f"""
            <div style="height: 10px; width: 100%; background: #e2e8f0; border-radius: 5px; margin-top: 10px; position: relative;">
                <div style="height: 100%; width: {min(ratio_val/2.0 * 100, 100)}%; background: {'#22c55e' if 0.8 <= ratio_val <= 1.3 else '#ef4444' if ratio_val > 1.5 else '#f97316'}; border-radius: 5px;"></div>
                <div style="position: absolute; top: -5px; left: 50%; height: 20px; width: 2px; background: black;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: #64748b;">
                <span>0.0</span><span>1.0</span><span>2.0+</span>
            </div>
            """
            st.markdown(gauge_html, unsafe_allow_html=True)

    # 2. Load Details
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Acute Load (7d)", int(status_data['acute']))
    with c2:
        st.metric("Chronic Load (28d)", int(status_data['chronic']))

    st.divider()
    
    # 3. Activity Analysis
    st.subheader("Activity Analysis")
    
    if history_data:
        # Convert to DF for display
        df_phys = pd.DataFrame(history_data)
        # Sort by date
        df_phys = df_phys.sort_values(by='date', ascending=False).head(10)
        
        for i, row in df_phys.iterrows():
            with st.container(border=True):
                pc1, pc2, pc3, pc4 = st.columns([2, 2, 2, 2])
                pc1.markdown(f"**{row['date']}**")
                pc1.caption(row['type'])
                
                pc2.metric("TRIMP", int(row['load']))
                pc3.metric("TE (0-5)", row['te'])
                
                # Visual TE bar
                width_pct = min(row['te'] / 5.0 * 100, 100)
                color = "#22c55e" if row['te'] < 3 else "#f59e0b" if row['te'] < 4 else "#ef4444"
                pc4.markdown(f"""
                <div style="margin-top: 15px; height: 8px; width: 100%; background: #f1f5f9; border-radius: 4px;">
                    <div style="height: 100%; width: {width_pct}%; background: {color}; border-radius: 4px;"></div>
                </div>
                <div style="font-size: 0.7rem; color: #64748b; text-align: right;">Impact</div>
                """, unsafe_allow_html=True)
    else:
        st.info("No activities found to analyze.")

# --- TAB: TRENDS ---
elif selected_tab == "Trends":
    st.header(":material/trending_up: Progress & Trends")
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    if runs_df.empty:
        st.info("Log some activities to see trends!")
    else:
        runs_df['date'] = pd.to_datetime(runs_df['date'])
        runs_df['pace'] = runs_df.apply(lambda x: x['duration'] / x['distance'] if x['distance'] > 0 else 0, axis=1)
        
        with st.container(border=True):
            st.subheader("Period Comparison")
            comp_mode = st.selectbox("Compare", ["Week vs Last Week", "Month vs Last Month", "6 Months", "Year vs Last Year"], label_visibility="collapsed")
            today = datetime.now()
            if comp_mode == "Week vs Last Week": days = 7
            elif comp_mode == "Month vs Last Month": days = 30
            elif comp_mode == "6 Months": days = 180
            else: days = 365
            curr_start = today - timedelta(days=days)
            prev_start = curr_start - timedelta(days=days)
            curr_df = runs_df[(runs_df['date'] >= curr_start) & (runs_df['date'] <= today)]
            prev_df = runs_df[(runs_df['date'] >= prev_start) & (runs_df['date'] < curr_start)]
            def calc_delta(curr, prev):
                if prev == 0: return 0.0
                return ((curr - prev) / prev) * 100
            c_dist = curr_df['distance'].sum()
            p_dist = prev_df['distance'].sum()
            d_dist = calc_delta(c_dist, p_dist)
            c_time = curr_df['duration'].sum()
            p_time = prev_df['duration'].sum()
            d_time = calc_delta(c_time, p_time)
            c_pace = c_time / c_dist if c_dist > 0 else 0
            p_pace = p_time / p_dist if p_dist > 0 else 0
            d_pace = calc_delta(c_pace, p_pace)
            m1, m2, m3 = st.columns(3)
            m1.metric("Distance", f"{c_dist:.1f} km", f"{d_dist:.1f}%")
            m2.metric("Time", f"{int(c_time//60)}h {int(c_time%60)}m", f"{d_time:.1f}%")
            m3.metric("Avg Pace", format_pace(c_pace) + "/km", f"{d_pace:.1f}%", delta_color="inverse")
            
        st.subheader("Trends Visualized")
        tab_vol, tab_pace = st.tabs(["Volume", "Pace Efficiency"])
        with tab_vol:
            vol_df = runs_df.set_index('date').resample('W').agg({'distance': 'sum'}).reset_index()
            fig_vol = px.bar(vol_df, x='date', y='distance', title="Weekly Distance Volume")
            fig_vol.update_layout(xaxis_title="", yaxis_title="Km", showlegend=False)
            st.plotly_chart(fig_vol, use_container_width=True)
        with tab_pace:
            pace_df = runs_df[runs_df['distance'] > 0].copy()
            fig_pace = px.scatter(pace_df, x='date', y='pace', color='type', title="Pace Evolution", trendline="lowess")
            fig_pace.update_layout(xaxis_title="", yaxis_title="Pace (min/km)")
            st.plotly_chart(fig_pace, use_container_width=True)

# --- TAB: SHARE REPORT ---
elif selected_tab == "Share":
    st.header(":material/share: Share Report")
    with st.container(border=True):
        st.subheader("Generate Coach Summary")
        c_dates, c_dummy = st.columns([2, 1])
        with c_dates:
            d_range = st.date_input("Date Range", value=(datetime.now() - timedelta(days=6), datetime.now()), format="YYYY/MM/DD")
        if isinstance(d_range, tuple):
            if len(d_range) == 2: start_r, end_r = d_range
            elif len(d_range) == 1: start_r, end_r = d_range[0], d_range[0]
            else: start_r, end_r = datetime.now().date(), datetime.now().date()
        else: start_r, end_r = d_range, d_range
        st.divider()
        st.markdown("**Include Data:**")
        if 'share_cats' not in st.session_state: st.session_state.share_cats = ["Run", "Walk", "Ultimate", "Gym", "Stats"]
        all_cats = ["Run", "Walk", "Ultimate", "Gym", "Stats"]
        cols = st.columns(len(all_cats))
        for i, cat in enumerate(all_cats):
            is_selected = cat in st.session_state.share_cats
            if cols[i].checkbox(cat, value=is_selected, key=f"share_{cat}"):
                if cat not in st.session_state.share_cats: st.session_state.share_cats.append(cat)
            else:
                if cat in st.session_state.share_cats: st.session_state.share_cats.remove(cat)
        st.divider()
        if st.button("📄 Generate Text Report", type="primary"):
            report_text = generate_report(start_r, end_r, st.session_state.share_cats)
            st.text_area("Copy this text:", value=report_text, height=400)
