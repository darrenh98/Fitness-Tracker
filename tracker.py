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
    
    /* Daily Target Card */
    .daily-target {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        margin-top: 1rem;
    }
    .target-header {
        font-size: 1.1rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .target-load {
        font-size: 1.2rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0.5rem 0;
    }
    
    /* Load Focus Bars */
    .load-bar-container {
        position: relative;
        height: 24px;
        background-color: #f1f5f9;
        border-radius: 12px;
        margin-bottom: 8px;
        margin-top: 4px;
    }
    .load-bar-fill {
        height: 100%;
        border-radius: 12px;
        position: absolute;
        left: 0;
        top: 0;
    }
    .load-bar-target {
        position: absolute;
        height: 100%;
        border: 2px solid #1e293b;
        border-radius: 12px;
        top: 0;
        pointer-events: none;
        box-sizing: border-box;
    }
    .load-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #475569;
        margin-bottom: 2px;
        display: flex;
        justify-content: space-between;
    }
</style>
""", unsafe_allow_html=True)

# --- Physiology Engine ---
class PhysiologyEngine:
    def __init__(self, user_profile):
        """
        Initialize with user object containing:
        hr_max, hr_rest, vo2_max, gender ('male'/'female')
        zones: dict with boundary keys
        """
        self.hr_max = float(user_profile.get('hrMax', 190))
        # hrRest here comes from the monthAvgRHR in the profile updates
        self.hr_rest = float(user_profile.get('hrRest', 60)) 
        self.vo2_max = float(user_profile.get('vo2Max', 45))
        self.gender = user_profile.get('gender', 'Male').lower()
        self.zones = user_profile.get('zones', {})

    def classify_activity_load(self, load, avg_hr, zones):
        """
        Classifies a session's load into Anaerobic, High Aerobic, or Low Aerobic.
        Rules:
        - Anaerobic: Time in Z5 > 5 mins OR Avg HR > Z4 threshold
        - High Aerobic: Time in Z4 > 10 mins AND Not Anaerobic
        - Low Aerobic: Everything else
        """
        # Get thresholds
        z4_upper = float(self.zones.get('z4_u', 175))
        z4_lower = float(self.zones.get('z4_l', 161))
        
        # Zones list is [z1, z2, z3, z4, z5] in minutes
        time_z5 = zones[4] if len(zones) > 4 else 0
        time_z4 = zones[3] if len(zones) > 3 else 0
        
        # Anaerobic Check
        if time_z5 > 5 or (avg_hr > z4_upper):
            return "anaerobic"
        
        # High Aerobic Check
        if time_z4 > 10:
            return "high"
            
        # Default to Low Aerobic
        return "low"

    def calculate_trimp(self, duration_min, avg_hr=None, zones=None):
        """
        Calculates Training Impulse (TRIMP) using Banister's formula.
        Uses explicit zone boundaries if available.
        
        RETURNS: (total_load, focus_scores_dict)
        Note: focus_scores dict now puts the ENTIRE load into ONE bucket 
        (Anaerobic, High, or Low) based on the classification of the activity.
        """
        load = 0.0
        focus_scores = {'low': 0, 'high': 0, 'anaerobic': 0}

        if zones and len(self.zones) > 0:
            # Granular Calculation per Zone using explicit Midpoints
            z1_mid = (self.hr_rest + float(self.zones.get('z1_u', 130))) / 2
            z2_mid = (float(self.zones.get('z2_l', 131)) + float(self.zones.get('z2_u', 145))) / 2
            z3_mid = (float(self.zones.get('z3_l', 146)) + float(self.zones.get('z3_u', 160))) / 2
            z4_mid = (float(self.zones.get('z4_l', 161)) + float(self.zones.get('z4_u', 175))) / 2
            z5_mid = (float(self.zones.get('z5_l', 176)) + self.hr_max) / 2
            
            midpoints = [z1_mid, z2_mid, z3_mid, z4_mid, z5_mid]
            exponent = 1.92 if self.gender == 'male' else 1.67
            
            for i, duration in enumerate(zones):
                if duration <= 0: continue
                avg_zone_hr = midpoints[i]
                hr_reserve = max(0.0, min(1.0, (avg_zone_hr - self.hr_rest) / (self.hr_max - self.hr_rest)))
                segment_load = duration * hr_reserve * 0.64 * math.exp(exponent * hr_reserve)
                load += segment_load
                
        elif avg_hr and avg_hr > 0:
            # Basic Banister
            hr_reserve = max(0.0, min(1.0, (avg_hr - self.hr_rest) / (self.hr_max - self.hr_rest)))
            exponent = 1.92 if self.gender == 'male' else 1.67
            load = duration_min * hr_reserve * 0.64 * math.exp(exponent * hr_reserve)

        # --- CLASSIFICATION STEP (Restored Whole Activity Logic) ---
        # Determine the single focus type for the entire activity
        focus_type = self.classify_activity_load(load, avg_hr if avg_hr else 0, zones if zones else [0,0,0,0,0])
        
        # Assign the FULL load to that single bucket
        focus_scores[focus_type] = load
            
        return load, focus_scores

    def get_daily_target(self, current_rhr):
        """
        Determines daily training target based on Morning RHR vs Baseline (hr_rest).
        """
        diff = current_rhr - self.hr_rest
        
        if diff < -2:
            # RHR is lower than baseline -> High Readiness
            return {
                "readiness": "High",
                "recommendation": "Go Hard / Interval Day",
                "target_load": "Heavy (e.g., Threshold or 90m+ Long Run)",
                "message": "Green light. Your system is primed for high intensity.",
                "color": "#22c55e" # Green
            }
        elif diff > 5:
            # RHR is significantly higher -> Low Readiness
            return {
                "readiness": "Low",
                "recommendation": "Active Recovery / Rest",
                "target_load": "Recovery (e.g., 30m easy jog or Rest)",
                "message": "Red light. Focus on sleep and mobility today.",
                "color": "#ef4444" # Red
            }
        else:
            # Moderate Readiness
            return {
                "readiness": "Moderate",
                "recommendation": "Steady State / Base Miles",
                "target_load": "Maintenance (e.g., 45-60m Aerobic Z2)",
                "message": "Train, but keep it controlled. Don't dig a hole.",
                "color": "#f97316" # Orange
            }

    def get_training_effect(self, trimp_score):
        """
        Scales raw TRIMP to a 0.0-5.0 Training Effect score based on VO2 Max.
        """
        scaling_factor = self.vo2_max * 1.5
        if scaling_factor == 0: return 0.0, "None"
        
        te = trimp_score / scaling_factor
        te = round(min(5.0, te), 1)
        
        label = "Recovery"
        if te >= 1.0 and te < 2.0: label = "Maintaining"
        elif te >= 2.0 and te < 3.0: label = "Productive"
        elif te >= 3.0 and te < 4.0: label = "Improving"
        elif te >= 4.0 and te < 5.0: label = "Highly Improving"
        elif te >= 5.0: label = "Overreaching"
            
        return te, label

    def get_trimp_label(self, trimp):
        if trimp < 50: return "Light"
        if trimp < 100: return "Moderate"
        if trimp < 200: return "Hard"
        return "Extreme"

    def calculate_training_status(self, activity_history):
        """
        Calculates Acute:Chronic Workload Ratio (ACWR) and Status.
        activity_history: list of dicts with {'date': 'YYYY-MM-DD', 'load': float, 'focus_type': str}
        """
        today = datetime.now().date()
        
        acute_start = today - timedelta(days=6) # Last 7 days
        chronic_start = today - timedelta(days=27) # Last 28 days
        
        acute_load = 0
        chronic_load_total = 0
        
        # Bucket Accumulation (Chronic 4-week window)
        buckets = {'low': 0, 'high': 0, 'anaerobic': 0}
        
        for activity in activity_history:
            act_date = datetime.strptime(activity['date'], '%Y-%m-%d').date()
            load = activity.get('load', 0)
            focus = activity.get('focus', {}) # This is now {type: total_load, others: 0}
            
            if acute_start <= act_date <= today:
                acute_load += load
                
            if chronic_start <= act_date <= today:
                chronic_load_total += load
                # Accumulate buckets based on the focus dict
                buckets['low'] += focus.get('low', 0)
                buckets['high'] += focus.get('high', 0)
                buckets['anaerobic'] += focus.get('anaerobic', 0)
        
        chronic_load_weekly = chronic_load_total / 4.0 if chronic_load_total > 0 else 1.0
        ratio = acute_load / chronic_load_weekly
        
        # Status Logic
        status = "Recovery"
        color_class = "status-gray"
        description = "Load is very low."

        if ratio > 1.5:
            status = "Overreaching"
            color_class = "status-red"
            description = "High injury risk! Spike in load."
        elif 1.3 <= ratio <= 1.5:
            status = "High Strain"
            color_class = "status-orange"
            description = "Caution: Rapid load increase."
        elif 0.8 <= ratio < 1.3:
            if acute_load > chronic_load_weekly:
                status = "Productive"
                color_class = "status-green"
                description = "Optimal zone. Building fitness."
            else:
                status = "Maintaining"
                color_class = "status-green"
                description = "Load is consistent."
        else:
            status = "Recovery / Detraining"
            color_class = "status-gray"
            description = "Workload is decreasing."
            
        # Optimal Target Ranges (80/20 model approx)
        total_chronic = chronic_load_total
        targets = {
            'low': {'min': total_chronic * 0.70, 'max': total_chronic * 0.90},
            'high': {'min': total_chronic * 0.10, 'max': total_chronic * 0.25}, # widened slightly for flexibility
            'anaerobic': {'min': total_chronic * 0.0, 'max': total_chronic * 0.10}
        }
        
        # Determine Shortages
        feedback = "Balanced! Well done."
        if buckets['low'] < targets['low']['min']:
            feedback = "Shortage: Low Aerobic. You need more easy base miles."
        elif buckets['high'] < targets['high']['min']:
             feedback = "Shortage: High Aerobic. Try a Tempo or Threshold run."
        elif buckets['anaerobic'] < targets['anaerobic']['min'] and total_chronic > 500: # Only suggest anaerobic if base exists
             feedback = "Shortage: Anaerobic. Try some sprints or hill repeats."
        elif buckets['low'] > targets['low']['max']:
             feedback = "Focus: High Volume of Easy work detected."

        return {
            "acute": round(acute_load),
            "chronic": round(chronic_load_weekly),
            "ratio": round(ratio, 2),
            "status": status,
            "css": color_class,
            "desc": description,
            "buckets": buckets,
            "targets": targets,
            "feedback": feedback,
            "total_4w": total_chronic
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
        "monthAvgRHR": 60, "monthAvgHRV": 40,
        # Default Zones
        "zones": {
            "z1_u": 130, 
            "z2_l": 131, "z2_u": 145,
            "z3_l": 146, "z3_u": 160,
            "z4_l": 161, "z4_u": 175,
            "z5_l": 176
        }
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
                data['user_profile'].update({"gender": "Male", "hrMax": 190, "hrRest": 60, "vo2Max": 45})
            if 'monthAvgRHR' not in data.get('user_profile', {}):
                data['user_profile'].update({"monthAvgRHR": 60, "monthAvgHRV": 40})
            # Migration for zones
            if 'zones' not in data.get('user_profile', {}) or 'z1_u' not in data.get('user_profile', {}).get('zones', {}):
                data['user_profile']['zones'] = {
                    "z1_u": 130, 
                    "z2_l": 131, "z2_u": 145,
                    "z3_l": 146, "z3_u": 160,
                    "z4_l": 161, "z4_u": 175,
                    "z5_l": 176
                }
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

def format_sleep(decimal_hours):
    """Converts decimal hours (e.g. 6.83) to '6h 50m' string"""
    if not decimal_hours: return "-"
    hrs = int(decimal_hours)
    mins = int((decimal_hours - hrs) * 60)
    return f"{hrs}h {mins}m"

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

def float_to_hhmm(val):
    """Converts decimal hours 7.5 to string '07:30' for prefilling text inputs"""
    if not val: return ""
    hours = int(val)
    minutes = int((val - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

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
    report = [f"📊 **Training & Physio Report**"]
    report.append(f"📅 {start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}\n")
    
    # Calculate Physio Stats for context
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    
    # 1. FIELD ACTIVITIES & LOAD
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
            
            report.append(f"👟 **ACTIVITIES ({len(period_runs)})**")
            report.append(f"Totals: {total_dist:.1f} km | {format_duration(total_time)}")
            report.append("")
            
            for r in period_runs:
                # Calculate Physio metrics on fly for report
                zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
                trimp, focus = engine.calculate_trimp(float(r['duration']), int(r['avgHr']), zones)
                # Find focus type key where val > 0 or default
                focus_type = next((k for k, v in focus.items() if v > 0), "low")
                te, te_label = engine.get_training_effect(trimp)
                
                line = f"- {r['date'][5:]}: {r['type']} {r['distance']}km @ {format_duration(r['duration'])}"
                
                # Metrics Line
                metrics = []
                if r['distance'] > 0 and r['type'] != 'Ultimate': metrics.append(f"{format_pace(r['duration']/r['distance'])}/km")
                if r['avgHr'] > 0: metrics.append(f"{r['avgHr']}bpm")
                
                line += f" ({', '.join(metrics)})" if metrics else ""
                
                report.append(line)
                
                # Physio & Feel
                physio_info = f"   Load: {int(trimp)} ({focus_type.title()}) | TE: {te} {te_label}"
                if r.get('rpe'): physio_info += f" | RPE: {r['rpe']}"
                if r.get('feel'): physio_info += f" | Feel: {r['feel']}"
                report.append(physio_info)
                
                # Notes
                if r.get('notes'): report.append(f"   📝 {r['notes']}")
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
            report.append("")

    # 3. HEALTH & RECOVERY
    if "Stats" in selected_cats:
        stats = st.session_state.data['health_logs']
        period_stats = [s for s in stats if start_date <= datetime.strptime(s['date'], '%Y-%m-%d').date() <= end_date]
        period_stats.sort(key=lambda x: x['date']) # Sort chronologically
        
        if period_stats:
            report.append(f"❤️ **HEALTH LOG**")
            
            for s in period_stats:
                date_str = s['date'][5:]
                rhr = s.get('rhr', 0)
                hrv = s.get('hrv', 0)
                sleep_dec = s.get('sleepHours', 0)
                sleep_str = format_sleep(sleep_dec)
                
                # Determine readiness for this day based on CURRENT profile baseline
                daily_target = engine.get_daily_target(rhr)
                readiness = daily_target['readiness']
                
                report.append(f"- {date_str}: Sleep: {sleep_str} | HRV: {hrv} | RHR: {rhr} | Readiness: {readiness}")
            report.append("")

    # 4. TRAINING STATUS SNAPSHOT (Based on End Date)
    # Need full history for calculation
    all_runs = st.session_state.data['runs']
    history_data = []
    for r in all_runs:
        zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
        trimp, focus = engine.calculate_trimp(float(r['duration']), int(r['avgHr']), zones)
        history_data.append({'date': r['date'], 'load': trimp, 'focus': focus})
    
    # Calculate status
    status = engine.calculate_training_status(history_data)
    
    report.append(f"📈 **CURRENT STATUS**")
    report.append(f"Status: {status['status']}")
    report.append(f"ACWR: {status['ratio']} (Acute: {status['acute']} / Chronic: {status['chronic']})")
    
    buckets = status['buckets']
    report.append(f"Focus: Low: {int(buckets['low'])} | High: {int(buckets['high'])} | Anaerobic: {int(buckets['anaerobic'])}")

    return "\n".join(report)

def parse_imported_word_data(docx_file):
    # Import logic removed/not needed per request but kept stub for safety if called
    return 0, "Feature disabled"

# --- Sidebar Navigation ---
with st.sidebar:
    st.title(":material/sprint: RunLog Hub")
    # Reordered tabs as requested
    selected_tab = st.radio("Navigate", ["Training Status", "Cardio Training", "Gym", "Plan", "Trends", "Share"], label_visibility="collapsed")
    st.divider()
    
    with st.expander("👤 Athlete Profile"):
        prof = st.session_state.data['user_profile']
        
        # Basic
        c1, c2 = st.columns(2)
        new_weight = c1.number_input("Weight (kg)", value=float(prof.get('weight', 70)), key="prof_weight")
        new_height = c2.number_input("Height (cm)", value=float(prof.get('height', 175)), key="prof_height")
        
        # Physio Params
        gender = st.selectbox("Gender", ["Male", "Female"], index=0 if prof.get('gender','Male') == 'Male' else 1)
        c3, c5 = st.columns(2)
        hr_max = c3.number_input("Max HR", value=int(prof.get('hrMax', 190)))
        vo2 = c5.number_input("VO2 Max", value=float(prof.get('vo2Max', 45)))
        
        # Monthly Averages
        st.markdown("**Monthly Averages**")
        cm1, cm2 = st.columns(2)
        m_rhr = cm1.number_input("Avg RHR", value=int(prof.get('monthAvgRHR', 60)))
        m_hrv = cm2.number_input("Avg HRV", value=int(prof.get('monthAvgHRV', 40)))

        st.markdown("**Heart Rate Zones**")
        cz = prof.get('zones', {})
        
        # Explicit Boundaries
        z1_u = st.number_input("Z1 Upper", value=int(cz.get('z1_u', 130)))
        
        c_z2l, c_z2u = st.columns(2)
        z2_l = c_z2l.number_input("Z2 Lower", value=int(cz.get('z2_l', 131)))
        z2_u = c_z2u.number_input("Z2 Upper", value=int(cz.get('z2_u', 145)))
        
        c_z3l, c_z3u = st.columns(2)
        z3_l = c_z3l.number_input("Z3 Lower", value=int(cz.get('z3_l', 146)))
        z3_u = c_z3u.number_input("Z3 Upper", value=int(cz.get('z3_u', 160)))
        
        c_z4l, c_z4u = st.columns(2)
        z4_l = c_z4l.number_input("Z4 Lower", value=int(cz.get('z4_l', 161)))
        z4_u = c_z4u.number_input("Z4 Upper", value=int(cz.get('z4_u', 175)))
        
        z5_l = st.number_input("Z5 Lower", value=int(cz.get('z5_l', 176)))

        if st.button("Save Profile"):
            st.session_state.data['user_profile'].update({
                'weight': new_weight, 'height': new_height, 'gender': gender,
                'hrMax': hr_max, 'hrRest': m_rhr, 'vo2Max': vo2, # hrRest synced with m_rhr
                'monthAvgRHR': m_rhr, 'monthAvgHRV': m_hrv,
                'zones': {
                    "z1_u": z1_u, 
                    "z2_l": z2_l, "z2_u": z2_u,
                    "z3_l": z3_l, "z3_u": z3_u,
                    "z4_l": z4_l, "z4_u": z4_u,
                    "z5_l": z5_l
                }
            })
            persist()
            st.success("Saved!")

# --- TAB: TRAINING STATUS (LANDING PAGE) ---
if selected_tab == "Training Status":
    st.header(":material/monitor_heart: Training Status")
    
    # 1. Morning Check-in (Top)
    with st.container(border=True):
        c_header, c_date = st.columns([3, 2])
        c_header.subheader("☀️ Morning Update")
        
        # Date picker OUTSIDE the form for dynamic pre-fill
        h_date = c_date.date_input("Log Date", datetime.now(), label_visibility="collapsed")
        
        # Check existing log
        existing_log = next((log for log in st.session_state.data['health_logs'] if log['date'] == str(h_date)), None)
        
        # State management for editing
        if 'edit_morning_date' not in st.session_state:
            st.session_state.edit_morning_date = None
            
        # Are we editing this specific date?
        is_editing = (st.session_state.edit_morning_date == str(h_date))
        
        # VIEW MODE: Log exists and we are NOT editing
        if existing_log and not is_editing:
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Sleep", format_sleep(existing_log['sleepHours']))
            v2.metric("RHR", f"{existing_log['rhr']} bpm")
            v3.metric("HRV", f"{existing_log['hrv']} ms")
            
            with v4:
                st.write("") # Spacer
                col_e, col_d = st.columns(2)
                if col_e.button(":material/edit:", key=f"edit_m_{existing_log['id']}"):
                    st.session_state.edit_morning_date = str(h_date)
                    st.rerun()
                if col_d.button(":material/delete:", key=f"del_m_{existing_log['id']}"):
                    st.session_state.data['health_logs'] = [h for h in st.session_state.data['health_logs'] if h['id'] != existing_log['id']]
                    persist()
                    st.rerun()
                    
        # EDIT/ADD MODE: No log OR we are editing
        else:
            # Defaults
            def_rhr = existing_log['rhr'] if existing_log else 60
            def_hrv = existing_log['hrv'] if existing_log else 40
            def_sleep_str = float_to_hhmm(existing_log['sleepHours']) if existing_log else "07:30"
            
            with st.form("daily_health", clear_on_submit=False):
                c_sleep, c_rhr, c_hrv, c_btn = st.columns(4)
                
                sleep_str = c_sleep.text_input("Sleep (hh:mm)", value=def_sleep_str, placeholder="07:30")
                rhr = c_rhr.number_input("RHR", min_value=30, max_value=150, value=int(def_rhr))
                hrv = c_hrv.number_input("HRV", min_value=0, value=int(def_hrv))
                
                btn_label = "Update Stats" if existing_log else "Log Stats"
                
                # Spacer for vertical alignment
                c_btn.write("") 
                c_btn.write("")
                
                if c_btn.form_submit_button(btn_label, use_container_width=True):
                    # Parse sleep time
                    sleep_dec = parse_time_input(sleep_str)
                    
                    new_h = {"id": existing_log['id'] if existing_log else int(time.time()), 
                             "date": str(h_date), "rhr": rhr, "hrv": hrv, "sleepHours": sleep_dec, "vo2Max": 0}
                    
                    if existing_log:
                        # Update in place
                        idx = next((i for i, h in enumerate(st.session_state.data['health_logs']) if h['id'] == existing_log['id']), -1)
                        if idx != -1: st.session_state.data['health_logs'][idx] = new_h
                        st.session_state.edit_morning_date = None # Exit edit mode
                        st.success("Updated!")
                    else:
                        # Insert new
                        st.session_state.data['health_logs'].insert(0, new_h)
                        st.success("Logged!")
                    
                    persist()
                    st.rerun()
            
            if is_editing:
                if st.button("Cancel Edit"):
                    st.session_state.edit_morning_date = None
                    st.rerun()
    
        # Readiness Indicator using Month Avg from Profile
        # We grab the log for the SELECTED date to show status
        display_log = existing_log if existing_log else (st.session_state.data['health_logs'][0] if st.session_state.data['health_logs'] else None)
        
        if display_log:
            prof = st.session_state.data['user_profile']
            base_rhr = prof.get('monthAvgRHR', 60)
            
            engine = PhysiologyEngine(st.session_state.data['user_profile'])
            target_data = engine.get_daily_target(display_log['rhr'])
            
            st.markdown(f"""
            <div class="daily-target" style="border-left: 6px solid {target_data['color']};">
                <div class="target-header">
                    <span style="color: {target_data['color']};">{target_data['readiness']} Readiness</span>
                    <span style="font-weight:400; color:#64748b; font-size:0.9rem;">• RHR {display_log['rhr']} (Base {base_rhr})</span>
                </div>
                <div style="font-size: 1.2rem; font-weight:700; color:#1e293b;">{target_data['recommendation']}</div>
                <div class="target-load">Target: {target_data['target_load']}</div>
                <div style="font-size: 0.9rem; color:#475569; font-style:italic;">"{target_data['message']}"</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 2. Training Status & Load
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    history_data = []
    runs = st.session_state.data['runs']
    for r in runs:
        zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
        trimp, focus = engine.calculate_trimp(float(r['duration']), int(r['avgHr']), zones)
        # Find focus type key where val > 0 or default
        focus_type = next((k for k, v in focus.items() if v > 0), "low")
        te, te_label = engine.get_training_effect(trimp)
        history_data.append({'date': r['date'], 'load': trimp, 'te': te, 'te_lbl': te_label, 'type': r['type'], 'focus': focus})
    status_data = engine.calculate_training_status(history_data)
    
    with st.container(border=True):
        st.subheader("Physiological Status")
        sc1, sc2 = st.columns([3, 2])
        with sc1:
            st.markdown(f"""<div style="background-color: {status_data['css'] == 'status-green' and '#dcfce7' or status_data['css'] == 'status-red' and '#fee2e2' or status_data['css'] == 'status-orange' and '#ffedd5' or '#f1f5f9'}; padding: 1rem; border-radius: 12px; border: 1px solid #e2e8f0;"><h2 style="margin:0; color: #0f172a;">{status_data['status']}</h2><p style="margin:5px 0 0 0; color: #475569;">{status_data['desc']}</p></div>""", unsafe_allow_html=True)
            st.markdown(f"<div style='margin-top:10px; font-weight:500; color:#4b5563;'>{status_data['feedback']}</div>", unsafe_allow_html=True)
        with sc2:
            ratio_val = status_data['ratio']
            st.metric("Acute:Chronic Ratio", ratio_val, delta=None)
            gauge_html = f"""<div style="height: 10px; width: 100%; background: #e2e8f0; border-radius: 5px; margin-top: 10px; position: relative;"><div style="height: 100%; width: {min(ratio_val/2.0 * 100, 100)}%; background: {'#22c55e' if 0.8 <= ratio_val <= 1.3 else '#ef4444' if ratio_val > 1.5 else '#f97316'}; border-radius: 5px;"></div><div style="position: absolute; top: -5px; left: 50%; height: 20px; width: 2px; background: black;"></div></div><div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: #64748b;"><span>0.0</span><span>1.0</span><span>2.0+</span></div>"""
            st.markdown(gauge_html, unsafe_allow_html=True)
            
    c1, c2 = st.columns(2)
    with c1: st.metric("Acute Load (7d)", int(status_data['acute']))
    with c2: st.metric("Chronic Load (28d)", int(status_data['chronic']))
    
    st.divider()
    st.subheader("Load Focus (4 weeks)")
    buckets = status_data['buckets']
    b_labels = ["Anaerobic (Z5)", "High Aerobic (Z3/Z4)", "Low Aerobic (Z1/Z2)"]
    b_vals = [buckets['anaerobic'], buckets['high'], buckets['low']]
    fig_buckets = px.bar(x=b_vals, y=b_labels, orientation='h', text_auto='.0f', color=b_labels, color_discrete_sequence=["#8b5cf6", "#f97316", "#3b82f6"])
    fig_buckets.update_layout(showlegend=False, xaxis_title="Load", yaxis_title="")
    st.plotly_chart(fig_buckets, use_container_width=True)

# --- TAB: CARDIO TRAINING (Field Runs) ---
elif selected_tab == "Cardio Training":
    st.header(":material/directions_run: Cardio Training")
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    
    # Initialize Engine for this tab
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    
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
            
            scroll_to_top()

    form_label = f":material/edit: Edit Activity" if edit_run_id else ":material/add_circle: Log Activity"
    # Auto collapse if not editing
    expander_state = True if edit_run_id else False

    with st.expander(form_label, expanded=expander_state):
        # Dynamic key suffix
        key_suffix = f"{edit_run_id}" if edit_run_id else "new"

        with st.form("run_form", clear_on_submit=True):
            # Row 1: Date | Type
            c_d, c_t = st.columns([1, 3])
            with c_d:
                st.caption("Date")
                act_date = st.date_input("Date", def_date, label_visibility="collapsed", key=f"date_{key_suffix}")
            with c_t:
                st.caption("Activity Type")
                type_idx = ["Run", "Walk", "Ultimate"].index(def_type) if def_type in ["Run", "Walk", "Ultimate"] else 0
                act_type = st.radio("Type", ["Run", "Walk", "Ultimate"], index=type_idx, key=f"type_{key_suffix}", horizontal=True, label_visibility="collapsed")
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Distance (km)")
                dist_val = float(def_dist) if edit_run_id or def_dist > 0 else None
                dist = st.number_input("Distance", min_value=0.0, step=0.01, value=dist_val, placeholder="0.00", label_visibility="collapsed", key=f"dist_{key_suffix}")
            with c2:
                st.caption("Duration (hh:mm:ss)")
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
            
            st.caption("How did it feel?")
            feel_idx = ["Good", "Normal", "Tired", "Pain"].index(def_feel) if def_feel in ["Good", "Normal", "Tired", "Pain"] else 1
            feel = st.radio("Feel", ["Good", "Normal", "Tired", "Pain"], index=feel_idx, horizontal=True, label_visibility="collapsed", key=f"feel_{key_suffix}")
            
            st.caption("Notes")
            notes = st.text_area("Notes", value=def_notes, placeholder="Easy run, felt strong...", height=3, label_visibility="collapsed", key=f"notes_{key_suffix}")
            
            btn_text = "Update Activity" if edit_run_id else "Save Activity"
            
            if st.form_submit_button(btn_text):
                new_id = int(time.time() * 1000)
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
    
    if 'dash_period' not in st.session_state: st.session_state.dash_period = "Weekly"
    if 'dash_offset' not in st.session_state: st.session_state.dash_offset = 0

    def get_date_range(period, offset):
        today = datetime.now().date()
        if period == "Weekly":
            start_of_week = today - timedelta(days=today.weekday())
            start_date = start_of_week - timedelta(weeks=offset)
            end_date = start_date + timedelta(days=6)
            label = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
        elif period == "Monthly":
            total_months = today.year * 12 + today.month - 1 - offset
            year = total_months // 12
            month = total_months % 12 + 1
            start_date = date(year, month, 1)
            if month == 12: end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else: end_date = date(year, month + 1, 1) - timedelta(days=1)
            label = start_date.strftime("%B %Y")
        elif period == "6 Months":
            current_half = 0 if today.month <= 6 else 1
            total_halves = today.year * 2 + current_half - offset
            year = total_halves // 2
            half = total_halves % 2
            if half == 0: start_date, end_date, label = date(year, 1, 1), date(year, 6, 30), f"H1 {year} (Jan - Jun)"
            else: start_date, end_date, label = date(year, 7, 1), date(year, 12, 31), f"H2 {year} (Jul - Dec)"
        else: 
            target_year = today.year - offset
            start_date, end_date, label = date(target_year, 1, 1), date(target_year, 12, 31), str(target_year)
        return start_date, end_date, label

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
            if c_prev.button("◀", use_container_width=True): st.session_state.dash_offset += 1; st.rerun()
            c_lbl.markdown(f"<div style='text-align: center; padding-top: 5px; font-weight: 600; color: #334155;'>{d_label}</div>", unsafe_allow_html=True)
            if c_next.button("▶", use_container_width=True, disabled=(st.session_state.dash_offset <= 0)): st.session_state.dash_offset -= 1; st.rerun()

    period_runs_df = pd.DataFrame(columns=runs_df.columns)
    if not runs_df.empty:
        runs_df['dt_obj'] = pd.to_datetime(runs_df['date']).dt.date
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
                filtered_df = filtered_df.sort_values(by='dt_obj', ascending=False)
                for idx, row in filtered_df.iterrows():
                    # Calculate Metrics On-The-Fly for Display
                    zones = [float(row.get(f'z{i}', 0)) for i in range(1,6)]
                    trimp, focus = engine.calculate_trimp(float(row['duration']), int(row['avgHr']), zones)
                    # Find focus type key where val > 0 or default
                    focus_type = next((k for k, v in focus.items() if v > 0), "low")
                    te, te_label = engine.get_training_effect(trimp)
                    
                    with st.container(border=True):
                        # Balanced Columns for Symmetry: Date | Type | Stats | Metrics | Actions
                        # Adjusted weights: [1.5, 1.2, 2.5, 2.5, 1]
                        c_date, c_type, c_stats, c_metrics, c_act = st.columns([1.5, 1.2, 2.5, 2.5, 1])
                        
                        icon_map = {"Run": ":material/directions_run:", "Walk": ":material/directions_walk:", "Ultimate": ":material/sports_handball:"}
                        
                        # Date & Type
                        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
                        date_str = date_obj.strftime('%A, %b %d')
                        c_date.markdown(f"**{date_str}**")
                        c_type.markdown(f"{icon_map.get(row['type'], ':material/help:')} {row['type']}")
                        
                        # Main Stats (Dist, Time, Pace)
                        stats_html = f"""
                        <div style="line-height: 1.5;">
                            <span class="history-sub">Dist:</span> <span class="history-value">{row['distance']}km</span><br>
                            <span class="history-sub">Time:</span> <span class="history-value">{format_duration(row['duration'])}</span><br>
                            <span class="history-sub">{'Note' if row['type'] == 'Ultimate' else 'Pace'}:</span> 
                            <span class="history-value">{row.get('notes','-') if row['type']=='Ultimate' else format_pace(row['duration']/row['distance'] if row['distance']>0 else 0)+'/km'}</span>
                        </div>
                        """
                        c_stats.markdown(stats_html, unsafe_allow_html=True)
                        
                        # Detailed Metrics (HR, Load, TE, Feel)
                        metrics_list = []
                        if row['avgHr'] > 0: metrics_list.append(f"<span class='history-sub'>HR:</span> <span class='history-value'>{row['avgHr']}</span>")
                        metrics_list.append(f"<span class='history-sub'>Load:</span> <span class='history-value'>{int(trimp)}</span>")
                        metrics_list.append(f"<span class='history-sub'>TE:</span> <span class='history-value status-badge { 'status-green' if 2<=te<4 else 'status-orange' if te>=4 else 'status-gray' }' style='font-size:0.75rem; padding:1px 6px;'>{te} {te_label.split()[0]}</span>")
                        
                        # Optional metrics
                        extras = []
                        if row.get('cadence', 0) > 0: extras.append(f"Cad: {row['cadence']}")
                        if row.get('power', 0) > 0: extras.append(f"Pwr: {row['power']}")
                        if extras: metrics_list.append(f"<span class='history-sub'>{' | '.join(extras)}</span>")
                        
                        # Feel as Text
                        feel_val = row.get('feel', '')
                        if feel_val: metrics_list.append(f"<span class='history-sub'>Feel:</span> <span class='history-value'>{feel_val}</span>")

                        metrics_html = "<div style='line-height: 1.5;'>" + "<br>".join(metrics_list) + "</div>"
                        c_metrics.markdown(metrics_html, unsafe_allow_html=True)
                        
                        # Actions
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
                            def get_lbl(pct, txt): return txt if pct > 10 else ""
                            
                            bar_html = f"""
                            <div style="display: flex; width: 100%; height: 18px; border-radius: 4px; overflow: hidden; margin-top: 12px; background-color: #f1f5f9;">
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

# --- TAB: IMPORT ---
elif selected_tab == "Import":
    st.header(":material/upload_file: Import Data")
    with st.container(border=True):
        st.info("Upload a Word (.docx) file containing reports in the standard format (e.g., '- MM-DD: Type Dist @ Time').")
        uploaded_file = st.file_uploader("Choose a Word file", type="docx")
        if uploaded_file is not None:
            if st.button("Process Import"):
                count, error = parse_imported_word_data(uploaded_file)
                if error: st.error(f"Error: {error}")
                elif count > 0:
                    st.success(f"Successfully imported {count} activities!")
                    time.sleep(1)
                    st.rerun()
                else: st.warning("No matching activities found in the document.")
