import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timedelta, date, timezone
import time
import copy
import re
import math
import calendar
import streamlit.components.v1 as components

# --- Firebase Init ---
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        pass

try:
    db = firestore.client()
except:
    db = None

# --- Configuration & Styling ---
st.set_page_config(
    page_title="RunLog Hub",
    page_icon=":material/sprint:",
    layout="wide",
    initial_sidebar_state="expanded"
)

def setup_page():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
        
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #44403c; }
        .stApp { background-color: #fafaf9; }
        .material-symbols-rounded { font-size: 1.1rem; vertical-align: middle; color: #78716c; }
        h1, h2, h3 { font-weight: 800 !important; letter-spacing: -0.025em; color: #292524; }
        .stCard, [data-testid="stForm"] { background-color: #ffffff; padding: 1.5rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgba(68, 64, 60, 0.05); border: 1px solid #f5f5f4; }
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] > [data-testid="stContainer"] {
            background-color: #ffffff; padding: 1.25rem; border-radius: 0.75rem; border: 1px solid #e7e5e4; margin-bottom: 1.0rem; box-shadow: 0 1px 2px 0 rgba(68, 64, 60, 0.05);
        }
        [data-testid="stMetric"] { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); border: 1px solid #e7e5e4; text-align: center; }
        [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 800; color: #44403c; }
        [data-testid="stMetricLabel"] { font-size: 0.75rem; font-weight: 600; color: #a8a29e; letter-spacing: 0.05em; text-transform: uppercase; }
        .daily-target { background-color: #ffffff; border-radius: 12px; padding: 1.5rem; border: 1px solid #e7e5e4; margin-top: 1rem; }
        .target-header { font-size: 1.1rem; font-weight: 800; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 8px; }
        .target-load { font-size: 1.2rem; font-weight: 700; color: #c2410c; margin: 0.5rem 0; }
        .bio-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: #57534e; border-top: 1px solid #f5f5f4; padding-top: 8px; margin-top: 8px; }
        .bio-item { display: flex; align-items: center; gap: 4px; }
        .cal-day-box { min-height: 80px; display: flex; flex-direction: column; justify-content: flex-start; }
        .cal-activity { font-size: 0.8rem; color: #44403c; display: flex; align-items: center; gap: 4px; margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- Data Persistence Helper ---
DATA_FILE = "run_tracker_data.json"
DEFAULT_DATA = {
    "runs": [], "health_logs": [],
    "user_profile": { "age": 30, "height": 175, "weight": 70, "gender": "Male", "hrMax": 190, "hrRest": 60, "vo2Max": 45, "monthAvgRHR": 60, "monthAvgHRV": 40, "zones": {"z1_u": 130, "z2_l": 131, "z2_u": 145, "z3_l": 146, "z3_u": 160, "z4_l": 161, "z4_u": 175, "z5_l": 176}},
    "cycles": {"macro": "", "meso": "", "micro": ""}, "weekly_plan": {day: {"am": "", "pm": ""} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
}

def load_data():
    data = copy.deepcopy(DEFAULT_DATA)
    if not db:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    local = json.load(f)
                    data.update(local)
            except: pass
        return data

    try:
        runs_ref = db.collection("runs").stream()
        for doc in runs_ref:
            r = doc.to_dict(); r['id'] = doc.id; data["runs"].append(r)
        
        health_ref = db.collection("health_logs").stream()
        for doc in health_ref:
            h = doc.to_dict(); h['id'] = doc.id; data["health_logs"].append(h)
        
        settings_ref = db.collection("settings")
        prof_doc = settings_ref.document("profile").get()
        if prof_doc.exists: data['user_profile'].update(prof_doc.to_dict())
            
        plan_doc = settings_ref.document("plan").get()
        if plan_doc.exists:
            plan_data = plan_doc.to_dict()
            if 'cycles' in plan_data: data['cycles'] = plan_data['cycles']
            if 'weekly_plan' in plan_data: data['weekly_plan'] = plan_data['weekly_plan']

        data["runs"].sort(key=lambda x: x.get('date', ''), reverse=True)
        data["health_logs"].sort(key=lambda x: x.get('date', ''), reverse=True)
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
    return data

def save_data(data):
    with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)

def persist():
    if not db: save_data(st.session_state.data)

# --- Helper Functions ---
def get_malaysia_time():
    return datetime.now(timezone.utc) + timedelta(hours=8)

def format_pace(decimal_min):
    if not decimal_min or decimal_min == 0: return "-"
    mins = int(decimal_min)
    secs = int((decimal_min - mins) * 60)
    return f"{mins}'{secs:02d}\""

def format_duration(decimal_min):
    if not decimal_min: return "00:00:00"
    mins = int(decimal_min)
    secs = int((decimal_min - mins) * 60)
    hrs = mins // 60
    rem_mins = mins % 60
    if hrs > 0: return f"{hrs:02d}:{rem_mins:02d}:{secs:02d}"
    return f"{rem_mins:02d}:{secs:02d}"

def format_sleep(decimal_hours):
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
    except: return 0.0

def float_to_hhmm(val):
    if not val: return ""
    hours = int(val); minutes = int((val - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

def scroll_to_top():
    js = """<script>var body = window.parent.document.querySelector(".main"); if (body) { body.scrollTop = 0; }</script>"""
    components.html(js, height=0)

def get_last_lift_stats(ex_name):
    return None

# --- Physiology Engine ---
class PhysiologyEngine:
    def __init__(self, user_profile):
        self.hr_max = float(user_profile.get('hrMax', 190))
        self.hr_rest = float(user_profile.get('hrRest', 60))
        self.vo2_max = float(user_profile.get('vo2Max', 45))
        self.gender = user_profile.get('gender', 'Male').lower()
        self.hrv_baseline = float(user_profile.get('monthAvgHRV', 40))
        self.zones = user_profile.get('zones', {})

    def classify_activity_load(self, load, avg_hr, zones):
        z4_upper = float(self.zones.get('z4_u', 175))
        time_z5 = zones[4] if len(zones) > 4 else 0
        time_z4 = zones[3] if len(zones) > 3 else 0
        if time_z5 > 5 or (avg_hr > z4_upper): return "anaerobic"
        if time_z4 > 10: return "high"
        return "low"

    def calculate_trimp(self, duration_min, avg_hr=None, zones=None, rpe=None):
        load = 0.0
        focus_scores = {'low': 0, 'high': 0, 'anaerobic': 0}
        
        # 1. Zone-based Calculation (Most Accurate)
        if zones and len(self.zones) > 0 and sum(zones) > 0:
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
                if i <= 1: focus_scores['low'] += segment_load
                elif i <= 3: focus_scores['high'] += segment_load
                else: focus_scores['anaerobic'] += segment_load
        
        # 2. Avg HR Calculation (Backup)
        elif avg_hr and avg_hr > 0:
            hr_reserve = max(0.0, min(1.0, (avg_hr - self.hr_rest) / (self.hr_max - self.hr_rest)))
            exponent = 1.92 if self.gender == 'male' else 1.67
            load = duration_min * hr_reserve * 0.64 * math.exp(exponent * hr_reserve)
            z2_upper = float(self.zones.get('z2_u', 145)); z4_upper = float(self.zones.get('z4_u', 175))
            if avg_hr > z4_upper: focus_scores['anaerobic'] = load
            elif avg_hr > z2_upper: focus_scores['high'] = load
            else: focus_scores['low'] = load
            
        # 3. RPE Calculation (Fallback for missing HR)
        if load == 0 and rpe and rpe > 0:
             # Scale: RPE (1-10) * Duration. 
             # To align with TRIMP (approx 60-80 for 1 hr moderate), we scale RPE.
             # e.g., 60 mins * RPE 4 = 240. 240 * 0.3 = 72 (Reasonable Z2 load)
             load = duration_min * rpe * 0.3
             # Estimate focus based on RPE
             if rpe >= 8: focus_scores['anaerobic'] = load
             elif rpe >= 6: focus_scores['high'] = load
             else: focus_scores['low'] = load

        return load, focus_scores

    def get_daily_target(self, current_rhr, current_hrv=None, current_sleep=0):
        diff = current_rhr - self.hr_rest
        if diff < -2:
            return {"readiness": "High", "recommendation": "Go Hard / Interval Day", "target_load": "Heavy (e.g., Threshold)", "message": "Green light. System primed.", "color": "#65a30d", "bg": "#dcfce7", "rhr_stat": "Good", "hrv_stat": "Normal", "sleep_stat": "Normal"}
        elif diff > 5:
            return {"readiness": "Low", "recommendation": "Active Recovery", "target_load": "Recovery (e.g., 30m easy)", "message": "Red light. Focus on sleep.", "color": "#be123c", "bg": "#fee2e2", "rhr_stat": "High", "hrv_stat": "Low", "sleep_stat": "Poor"}
        else:
            return {"readiness": "Moderate", "recommendation": "Steady State", "target_load": "Maintenance (e.g., Z2)", "message": "Train, but keep controlled.", "color": "#ea580c", "bg": "#ffedd5", "rhr_stat": "Normal", "hrv_stat": "Normal", "sleep_stat": "Normal"}
    
    def get_dynamic_daily_target(self, current_rhr, current_hrv, avg_7d_rhr, avg_7d_hrv):
        if not avg_7d_rhr or not avg_7d_hrv: return self.get_daily_target(current_rhr, current_hrv)
        rhr_z = current_rhr - avg_7d_rhr; hrv_z = current_hrv - avg_7d_hrv
        is_fatigued = (rhr_z > 3) or (hrv_z < -10)
        is_prime = (rhr_z < -2) and (hrv_z > -5)
        if is_fatigued: return {"readiness": "Low", "recommendation": "Recovery / Rest", "target_load": "Light (<40)", "message": f"Fatigue detected vs 7-day trend (RHR +{rhr_z:.1f})", "color": "#be123c", "bg": "#fee2e2"}
        elif is_prime: return {"readiness": "High", "recommendation": "Intervals / Tempo", "target_load": "Heavy (>120)", "message": "Primed. Stats better than recent avg.", "color": "#65a30d", "bg": "#dcfce7"}
        else: return {"readiness": "Moderate", "recommendation": "Base / Aerobic", "target_load": "Normal (60-100)", "message": "Stable. Maintain volume.", "color": "#ea580c", "bg": "#ffedd5"}

    def get_training_effect(self, trimp_score):
        scaling = self.vo2_max * 1.5
        if scaling == 0: return 0.0, "None"
        te = round(min(5.0, trimp_score / scaling), 1)
        label = "Recovery"
        if te >= 1.0 and te < 2.0: label = "Maintaining"
        elif te >= 2.0 and te < 3.0: label = "Productive"
        elif te >= 3.0 and te < 4.0: label = "Improving"
        elif te >= 4.0 and te < 5.0: label = "Highly Improving"
        elif te >= 5.0: label = "Overreaching"
        return te, label

    def calculate_training_status(self, activity_history, reference_date=None):
        today = reference_date if reference_date else get_malaysia_time().date()
        history_series = []
        for i in range(28):
            d = today - timedelta(days=27-i)
            day_acute, day_chronic_total = 0, 0
            d_acute_start, d_chronic_start = d - timedelta(days=6), d - timedelta(days=27)
            for activity in activity_history:
                act_date = datetime.strptime(activity['date'], '%Y-%m-%d').date()
                if act_date > d: continue
                load = activity.get('load', 0)
                if d_acute_start <= act_date <= d: day_acute += load
                if d_chronic_start <= act_date <= d: day_chronic_total += load
            day_chronic = day_chronic_total / 4.0 if day_chronic_total > 0 else 1.0
            ratio = day_acute / day_chronic if day_chronic > 0 else 0
            history_series.append({'date': d, 'acute': day_acute, 'chronic': day_chronic, 'ratio': ratio, 'optimal_min': day_chronic * 0.8, 'optimal_max': day_chronic * 1.3})

        current_status = history_series[-1]
        buckets = {'low': 0, 'high': 0, 'anaerobic': 0}
        chronic_start_today = today - timedelta(days=27)
        for activity in activity_history:
            act_date = datetime.strptime(activity['date'], '%Y-%m-%d').date()
            if act_date > today: continue
            if chronic_start_today <= act_date <= today:
                 focus = activity.get('focus', {})
                 buckets['low'] += focus.get('low', 0)
                 buckets['high'] += focus.get('high', 0)
                 buckets['anaerobic'] += focus.get('anaerobic', 0)

        total_chronic = sum(buckets.values())
        targets = {'low': {'min': total_chronic * 0.70, 'max': total_chronic * 0.90}, 'high': {'min': total_chronic * 0.10, 'max': total_chronic * 0.25}, 'anaerobic': {'min': total_chronic * 0.0, 'max': total_chronic * 0.10}}
        feedback = "Balanced! Well done."
        if buckets['low'] < targets['low']['min']: feedback = "Shortage: Low Aerobic."
        elif buckets['high'] < targets['high']['min']: feedback = "Shortage: High Aerobic."
        elif buckets['anaerobic'] < targets['anaerobic']['min'] and total_chronic > 500: feedback = "Shortage: Anaerobic."
        
        ratio = current_status['ratio']
        if ratio > 1.5: status = "Overreaching"; color_class = "status-red"; description = "High injury risk! Spike in load."
        elif 1.3 <= ratio <= 1.5: status = "High Strain"; color_class = "status-orange"; description = "Caution: Rapid increase."
        elif 0.8 <= ratio < 1.3: status = "Productive"; color_class = "status-green"; description = "Optimal training zone."
        else: status = "Recovery"; color_class = "status-gray"; description = "Workload decreasing."

        return {
            "acute": round(current_status['acute']), "chronic": round(current_status['chronic']),
            "ratio": round(ratio, 2), "status": status, "css": color_class,
            "desc": description, "buckets": buckets, "targets": targets,
            "feedback": feedback, "history": history_series, "total_4w": total_chronic
        }

    def calculate_ewma_status(self, runs, reference_date=None):
        today = reference_date if reference_date else get_malaysia_time().date()
        daily_loads = {}
        for r in runs:
            try:
                d = datetime.strptime(r['date'], '%Y-%m-%d').date()
                if d > today: continue
                zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
                hr = int(r.get('avgHr', 0)) if r.get('avgHr') else 0
                rpe = int(r.get('rpe', 0)) if r.get('rpe') else 0
                trimp, _ = self.calculate_trimp(float(r['duration']), hr, zones, rpe)
                daily_loads[d] = daily_loads.get(d, 0) + trimp
            except: continue

        date_range = [today - timedelta(days=x) for x in range(84)]
        date_range.sort()
        ewma_data = []
        atl, ctl = 0, 0
        k_atl, k_ctl = 2/(7+1), 2/(42+1)
        
        for d in date_range:
            load = daily_loads.get(d, 0)
            if d == date_range[0]: atl = load; ctl = load
            else:
                atl = (load * k_atl) + (atl * (1 - k_atl))
                ctl = (load * k_ctl) + (ctl * (1 - k_ctl))
            ewma_data.append({'date': d, 'load': load, 'atl': atl, 'ctl': ctl, 'tsb': ctl - atl})
        return pd.DataFrame(ewma_data)

# --- Report Generation ---
def generate_report(start_date, end_date, options):
    report = [f"Training & Physio Report"]
    report.append(f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}\n")
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    field_types = []
    if options.get('run'): field_types.append('Run')
    if options.get('walk'): field_types.append('Walk')
    if options.get('ultimate'): field_types.append('Ultimate')
    
    # 1. Summary Header
    runs = st.session_state.data['runs']
    stats = st.session_state.data['health_logs']
    
    period_runs = [r for r in runs if start_date <= datetime.strptime(r['date'], '%Y-%m-%d').date() <= end_date and r['type'] in field_types]
    period_stats = [s for s in stats if start_date <= datetime.strptime(s['date'], '%Y-%m-%d').date() <= end_date]
    
    total_dist = sum(r['distance'] for r in period_runs) if period_runs else 0
    total_time = sum(r['duration'] for r in period_runs) if period_runs else 0
    total_elev = sum(r.get('elevation', 0) for r in period_runs) if period_runs else 0
    avg_rhr = sum(s.get('rhr', 0) for s in period_stats) / len(period_stats) if period_stats else 0
    avg_hrv = sum(s.get('hrv', 0) for s in period_stats) / len(period_stats) if period_stats else 0
    avg_sleep = sum(s.get('sleepHours', 0) for s in period_stats) / len(period_stats) if period_stats else 0
    
    report.append("-" * 40)
    report.append(f"Total Dist: {total_dist:.1f} km")
    report.append(f"Total Time: {format_duration(total_time)}")
    report.append(f"Total Elev: {total_elev} m")
    if avg_rhr: report.append(f"Avg RHR: {int(avg_rhr)} bpm")
    if avg_hrv: report.append(f"Avg HRV: {int(avg_hrv)} ms")
    if avg_sleep: report.append(f"Avg Sleep: {format_sleep(avg_sleep)}")
    report.append("-" * 40)
    report.append("")
    
    if field_types and period_runs:
        report.append(f"ACTIVITIES ({len(period_runs)})")
        period_runs.sort(key=lambda x: x['date'])
        for r in period_runs:
            zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
            trimp, focus = engine.calculate_trimp(float(r['duration']), int(r.get('avgHr', 0)), zones)
            te, te_label = engine.get_training_effect(trimp)
            line = f"- {r['date'][5:]}: {r['type']} {r['distance']}km @ {format_duration(r['duration'])}"
            metrics = []
            if r['distance'] > 0 and r['type'] != 'Ultimate': metrics.append(f"{format_pace(r['duration']/r['distance'])}/km")
            if r.get('avgHr') and r['avgHr'] > 0: metrics.append(f"{r['avgHr']}bpm")
            line += f" ({', '.join(metrics)})" if metrics else ""
            report.append(line)
            details = []
            if options.get('det_physio'):
                # Find dominant focus type for summary
                focus_type = max(focus, key=focus.get) if focus else "low"
                details.append(f"Load: {int(trimp)} ({focus_type.title()}) | TE: {te} {te_label}")
                
            if options.get('det_adv'):
                adv = []
                if r.get('cadence'): adv.append(f"Cad: {r['cadence']}")
                if r.get('power'): adv.append(f"Pwr: {r['power']}")
                if r.get('elevation'): adv.append(f"Elev: {r['elevation']}m")
                if adv: details.append(" | ".join(adv))
            
            if options.get('det_zones'):
                z_strs = []
                for i in range(1,6):
                    val = float(r.get(f'z{i}', 0))
                    if val > 0: z_strs.append(f"Z{i}: {format_duration(val)}")
                if z_strs: details.append(" | ".join(z_strs))
            
            if options.get('det_notes'):
                notes_parts = []
                if r.get('rpe'): notes_parts.append(f"RPE: {r['rpe']}")
                if r.get('feel'): notes_parts.append(f"Feel: {r['feel']}")
                if r.get('notes'): notes_parts.append(f"Note: {r['notes']}")
                if notes_parts: details.append(" | ".join(notes_parts))
            
            if details:
                for d in details:
                    report.append(f"   {d}")
        report.append("")

    if options.get('health') and period_stats:
        report.append(f"HEALTH LOG")
        period_stats.sort(key=lambda x: x['date'])
        for s in period_stats:
            date_str = s['date'][5:]
            sleep_str = format_sleep(s.get('sleepHours', 0))
            daily_target = engine.get_daily_target(s.get('rhr', 0), s.get('hrv'), s.get('sleepHours', 0))
            report.append(f"- {date_str}: Sleep: {sleep_str} | RHR {s.get('rhr')} | HRV {s.get('hrv', '-')} | {daily_target['readiness']}")
    
    # --- Status Snapshot at End of Report Period ---
    if options.get('status'):
        all_runs = st.session_state.data['runs']
        h_data = []
        for r in all_runs:
            zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
            trimp, focus = engine.calculate_trimp(float(r['duration']), int(r.get('avgHr', 0)), zones)
            h_data.append({'date': r['date'], 'load': trimp, 'focus': focus})
        
        status = engine.calculate_training_status(h_data, reference_date=end_date)
        report.append("")
        report.append(f"STATUS (As of {end_date})")
        report.append(f"State: {status['status']}")
        report.append(f"ACWR: {status['ratio']} (Acute: {status['acute']} / Chronic: {status['chronic']})")
        buckets = status['buckets']
        report.append(f"Focus: Low: {int(buckets['low'])} | High: {int(buckets['high'])} | Anaerobic: {int(buckets['anaerobic'])}")
    
    # --- Advanced Status (EWMA) ---
    if options.get('adv_status'):
        all_runs = st.session_state.data['runs']
        df_ewma = engine.calculate_ewma_status(all_runs, reference_date=end_date)
        if not df_ewma.empty:
            current = df_ewma.iloc[-1]
            monotony = df_ewma['load'].tail(7).mean() / df_ewma['load'].tail(7).std() if df_ewma['load'].tail(7).std() > 0 else 0
            
            report.append("")
            report.append(f"ADVANCED STATUS (EWMA as of {end_date})")
            report.append(f"Fitness (CTL): {int(current['ctl'])}")
            report.append(f"Fatigue (ATL): {int(current['atl'])}")
            report.append(f"Form (TSB): {int(current['tsb'])}")
            report.append(f"Monotony (7d): {monotony:.2f}")

    return "\n".join(report)

# --- Sidebar Navigation ---
def render_sidebar():
    with st.sidebar:
        st.title(":material/sprint: RunLog Hub")
        malaysia_time = get_malaysia_time()
        st.caption(f"🇲🇾 {malaysia_time.strftime('%d %b %Y, %H:%M')}")
        
        if db: st.caption("🟢 Connected to Firestore")
        else: st.caption("🟠 Local Storage (Offline)")
             
        selected_tab = st.radio("Navigate", ["Training Status", "Advanced Status (Beta)", "Cardio Training", "Activity Calendar", "Export"], label_visibility="collapsed")
        st.divider()
        with st.expander("👤 Athlete Profile"):
            prof = st.session_state.data['user_profile']
            c1, c2 = st.columns(2)
            new_weight = c1.number_input("Weight (kg)", value=float(prof.get('weight', 70)), key="prof_weight")
            new_height = c2.number_input("Height (cm)", value=float(prof.get('height', 175)), key="prof_height")
            gender = st.selectbox("Gender", ["Male", "Female"], index=0 if prof.get('gender','Male') == 'Male' else 1)
            c3, c5 = st.columns(2)
            hr_max = c3.number_input("Max HR", value=int(prof.get('hrMax', 190)))
            vo2 = c5.number_input("VO2 Max", value=float(prof.get('vo2Max', 45)))
            st.markdown("**Monthly Averages**")
            cm1, cm2 = st.columns(2)
            m_rhr = cm1.number_input("Avg RHR", value=int(prof.get('monthAvgRHR', 60)))
            m_hrv = cm2.number_input("Avg HRV", value=int(prof.get('monthAvgHRV', 40)))
            st.markdown("**Heart Rate Zones**")
            cz = prof.get('zones', {})
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
                new_prof = {
                    'weight': new_weight, 'height': new_height, 'gender': gender,
                    'hrMax': hr_max, 'hrRest': m_rhr, 'vo2Max': vo2, 
                    'monthAvgRHR': m_rhr, 'monthAvgHRV': m_hrv,
                    'zones': {"z1_u": z1_u, "z2_l": z2_l, "z2_u": z2_u, "z3_l": z3_l, "z3_u": z3_u, "z4_l": z4_l, "z4_u": z4_u, "z5_l": z5_l}
                }
                st.session_state.data['user_profile'].update(new_prof)
                if db: db.collection("settings").document("profile").set(new_prof)
                else: save_data(st.session_state.data)
                st.success("Saved!")
        return selected_tab

# --- TAB RENDERERS ---

def render_training_status():
    st.header(":material/monitor_heart: Training Status")
    setup_page()
    with st.container(border=True):
        c_header, c_date = st.columns([3, 2])
        c_header.subheader("☀️ Morning Update")
        h_date = c_date.date_input("Log Date", get_malaysia_time(), label_visibility="collapsed")
        existing_log = next((log for log in st.session_state.data['health_logs'] if log['date'] == str(h_date)), None)
        if 'edit_morning_date' not in st.session_state: st.session_state.edit_morning_date = None
        is_editing = (st.session_state.edit_morning_date == str(h_date))
        prof = st.session_state.data['user_profile']
        base_rhr = prof.get('monthAvgRHR', 60)
        base_hrv = prof.get('monthAvgHRV', 40)
        if existing_log and not is_editing:
            rhr_diff = existing_log['rhr'] - base_rhr
            hrv_diff = existing_log.get('hrv', 40) - base_hrv
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Sleep", format_sleep(existing_log['sleepHours']))
            v2.metric("RHR", f"{existing_log['rhr']}", f"{rhr_diff} bpm", delta_color="inverse")
            v3.metric("HRV", f"{existing_log.get('hrv', '-')}", f"{hrv_diff} ms")
            with v4:
                st.write("")
                col_e, col_d = st.columns(2)
                if col_e.button(":material/edit:", key=f"edit_m_{existing_log['id']}"): st.session_state.edit_morning_date = str(h_date); st.rerun()
                if col_d.button(":material/delete:", key=f"del_m_{existing_log['id']}"):
                    if db: db.collection("health_logs").document(str(existing_log['id'])).delete()
                    st.session_state.data['health_logs'] = [h for h in st.session_state.data['health_logs'] if h['id'] != existing_log['id']]
                    st.rerun()
        else:
            def_rhr = existing_log['rhr'] if existing_log else base_rhr
            def_hrv = existing_log['hrv'] if existing_log else base_hrv
            def_sleep_str = float_to_hhmm(existing_log['sleepHours']) if existing_log else "07:30"
            with st.form("daily_health", clear_on_submit=False):
                c_sleep, c_rhr, c_hrv, c_btn = st.columns(4)
                sleep_str = c_sleep.text_input("Sleep (hh:mm)", value=def_sleep_str, placeholder="07:30")
                rhr = c_rhr.number_input("RHR", min_value=30, max_value=150, value=int(def_rhr))
                hrv = c_hrv.number_input("HRV", min_value=0, value=int(def_hrv))
                btn_label = "Update" if existing_log else "Log"
                c_btn.write(""); c_btn.write("")
                if c_btn.form_submit_button(btn_label, use_container_width=True):
                    sleep_dec = parse_time_input(sleep_str)
                    doc_id = str(existing_log['id']) if existing_log else str(int(time.time()))
                    new_h = {"id": doc_id, "date": str(h_date), "rhr": rhr, "hrv": hrv, "sleepHours": sleep_dec, "vo2Max": 0}
                    if db: db.collection("health_logs").document(doc_id).set(new_h)
                    if existing_log:
                        idx = next((i for i, h in enumerate(st.session_state.data['health_logs']) if str(h['id']) == doc_id), -1)
                        if idx != -1: st.session_state.data['health_logs'][idx] = new_h
                        st.session_state.edit_morning_date = None; st.success("Updated!")
                    else:
                        st.session_state.data['health_logs'].insert(0, new_h); st.success("Logged!")
                    if not db: save_data(st.session_state.data)
                    st.rerun()
            if is_editing:
                if st.button("Cancel Edit"): st.session_state.edit_morning_date = None; st.rerun()
        display_log = existing_log if existing_log else (st.session_state.data['health_logs'][0] if st.session_state.data['health_logs'] else None)
        if display_log:
            engine = PhysiologyEngine(st.session_state.data['user_profile'])
            target_data = engine.get_daily_target(display_log['rhr'], display_log.get('hrv', 40), display_log.get('sleepHours', 0))
            st.markdown(f"""<div class="daily-target" style="border-left: 6px solid {target_data['color']}; background-color: {target_data.get('bg', '#ffffff')};"><div class="target-header"><span style="color: {target_data['color']};">{target_data['readiness']} Readiness</span><span style="font-weight:400; color:#64748b; font-size:0.9rem;">• RHR {display_log['rhr']} (Base {base_rhr})</span></div><div style="font-size: 1.2rem; font-weight:700; color:#1e293b;">{target_data['recommendation']}</div><div class="target-load">Target: {target_data['target_load']}</div><div style="font-size: 0.9rem; color:#475569; font-style:italic;">"{target_data['message']}"</div></div>""", unsafe_allow_html=True)
    st.divider()
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    history_data = []
    runs = st.session_state.data['runs']
    for r in runs:
        zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
        trimp, focus = engine.calculate_trimp(float(r['duration']), int(r['avgHr']), zones)
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
            st.metric("ACWR", ratio_val, delta=None)
            history_df = pd.DataFrame(status_data['history'])
            if not history_df.empty:
                fig_tunnel = go.Figure()
                fig_tunnel.add_trace(go.Scatter(x=history_df['date'], y=history_df['optimal_max'], mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                fig_tunnel.add_trace(go.Scatter(x=history_df['date'], y=history_df['optimal_min'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor='rgba(34, 197, 94, 0.2)', name='Optimal Band'))
                fig_tunnel.add_trace(go.Scatter(x=history_df['date'], y=history_df['acute'], mode='lines+markers', line=dict(color='#0f172a', width=3), name='Acute Load'))
                fig_tunnel.update_layout(title="Chronic vs Acute", xaxis_title="", yaxis_title="Load", margin=dict(l=20, r=20, t=30, b=20), height=200, showlegend=False, plot_bgcolor='white', hovermode="x unified")
                st.plotly_chart(fig_tunnel, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1: st.metric("Acute Load (7d)", int(status_data['acute']))
    with c2: st.metric("Chronic Load (28d)", int(status_data['chronic']))
    st.divider()
    st.subheader("Load Focus (4 weeks)")
    buckets = status_data['buckets']
    targets = status_data['targets']
    max_scale = max(targets['low']['max'], buckets['low'], 1) * 1.2
    def draw_focus_bar(label, current, t_min, t_max, color):
        curr_pct = min((current / max_scale) * 100, 100)
        min_pct = min((t_min / max_scale) * 100, 100)
        max_pct = min((t_max / max_scale) * 100, 100)
        width_pct = max_pct - min_pct
        if current < t_min: status_txt = "Shortage"
        elif current > t_max: status_txt = "Over-focus"
        else: status_txt = "Balanced"
        return f"""<div style="margin-bottom: 12px;"><div class="load-label"><span>{label}</span> <span>{int(current)} <span style="font-weight:400; font-size:0.7rem;">({status_txt})</span></span></div><div class="load-bar-container"><div class="load-bar-target" style="left: {min_pct}%; width: {width_pct}%;"></div><div class="load-bar-fill" style="width: {curr_pct}%; background-color: {color}; opacity: 0.8;"></div></div></div>"""
    st.markdown(draw_focus_bar("Anaerobic (Purple)", buckets['anaerobic'], targets['anaerobic']['min'], targets['anaerobic']['max'], "#8b5cf6"), unsafe_allow_html=True)
    st.markdown(draw_focus_bar("High Aerobic (Orange)", buckets['high'], targets['high']['min'], targets['high']['max'], "#f97316"), unsafe_allow_html=True)
    st.markdown(draw_focus_bar("Low Aerobic (Blue)", buckets['low'], targets['low']['min'], targets['low']['max'], "#3b82f6"), unsafe_allow_html=True)
    st.divider()
    st.subheader("Recovery Trends (7 Days)")
    health_logs = st.session_state.data['health_logs']
    df_health = pd.DataFrame(health_logs)
    if not df_health.empty:
        df_health['date_obj'] = pd.to_datetime(df_health['date'])
        df_7d = df_health.sort_values('date_obj').tail(7)
        col_rhr, col_hrv = st.columns(2)
        with col_rhr:
            fig_rhr = px.line(df_7d, x='date_obj', y='rhr', title="Resting HR", markers=True)
            fig_rhr.update_traces(line_color='#be123c') 
            fig_rhr.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_rhr, use_container_width=True)
        with col_hrv:
            fig_hrv = px.line(df_7d, x='date_obj', y='hrv', title="HRV", markers=True)
            fig_hrv.update_traces(line_color='#65a30d') 
            fig_hrv.update_layout(height=200, margin=dict(l=20, r=20, t=30, b=20), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_hrv, use_container_width=True)

def render_advanced_status():
    st.header(":material/science: Advanced Status (Beta)")
    setup_page()
    
    runs = st.session_state.data['runs']
    health = st.session_state.data['health_logs']
    
    if not runs:
        st.info("Log more activities to see advanced status.")
        return

    # --- Prepare DataFrames ---
    df_runs = pd.DataFrame(runs)
    df_runs['date'] = pd.to_datetime(df_runs['date']).dt.date
    
    # Calculate Load per day
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    daily_loads = {}
    
    for r in runs:
        d = datetime.strptime(r['date'], '%Y-%m-%d').date()
        zones = [float(r.get(f'z{i}', 0)) for i in range(1,6)]
        trimp, _ = engine.calculate_trimp(float(r['duration']), int(r['avgHr']), zones)
        daily_loads[d] = daily_loads.get(d, 0) + trimp
        
    # Fill missing days for EWMA accuracy
    today = get_malaysia_time().date()
    date_range = [today - timedelta(days=x) for x in range(42)] # 6 weeks
    date_range.sort()
    
    ewma_data = []
    atl = 0 # Acute Training Load
    ctl = 0 # Chronic Training Load
    
    # Decay factors (Standard TrainingPeaks constants)
    tau_atl = 7
    tau_ctl = 42
    k_atl = 2 / (tau_atl + 1)
    k_ctl = 2 / (tau_ctl + 1)
    
    # Iterate to build EWMA
    for d in date_range:
        load = daily_loads.get(d, 0)
        # EWMA Formula: EMA_today = (Load * k) + (EMA_yesterday * (1-k))
        if d == date_range[0]: # Init
            atl = load
            ctl = load
        else:
            atl = (load * k_atl) + (atl * (1 - k_atl))
            ctl = (load * k_ctl) + (ctl * (1 - k_ctl))
            
        ewma_data.append({
            'date': d,
            'load': load,
            'atl': atl,
            'ctl': ctl,
            'tsb': ctl - atl # Training Stress Balance
        })
    
    df_ewma = pd.DataFrame(ewma_data)
    current = df_ewma.iloc[-1]
    
    # --- UI: Top Level Metrics ---
    st.subheader("EWMA Training Status")
    c1, c2, c3, c4 = st.columns(4)
    
    # Calculate Deltas (Today vs 7 days ago)
    past_7d = df_ewma.iloc[-8] if len(df_ewma) > 7 else df_ewma.iloc[0]
    
    d_ctl = int(current['ctl'] - past_7d['ctl'])
    d_atl = int(current['atl'] - past_7d['atl'])
    d_tsb = int(current['tsb'] - past_7d['tsb'])
    
    c1.metric("Fitness (CTL)", f"{int(current['ctl'])}", f"{d_ctl}", help="Chronic Training Load (42-day avg). Measures fitness.")
    c2.metric("Fatigue (ATL)", f"{int(current['atl'])}", f"{d_atl}", delta_color="inverse", help="Acute Training Load (7-day avg). Measures tiredness.")
    c3.metric("Form (TSB)", f"{int(current['tsb'])}", f"{d_tsb}", help="Training Stress Balance (Fitness - Fatigue). Positive = Fresh.")
    
    monotony = df_ewma['load'].tail(7).mean() / df_ewma['load'].tail(7).std() if df_ewma['load'].tail(7).std() > 0 else 0
    c4.metric("Monotony", f"{monotony:.1f}", help=">2.0 indicates high injury risk due to lack of variation.")
    
    # --- INSIGHT CARDS ---
    st.write("") # Spacer
    
    # Fitness Insight
    fit_trend = "Maintaining"
    if d_ctl > 2: fit_trend = "Building"
    elif d_ctl < -2: fit_trend = "Declining"
    
    st.info(f"**Fitness (CTL): {fit_trend}**\n\nYour fitness is {fit_trend.lower()} ({d_ctl} change over 7 days). " + 
            ("Great job building volume!" if d_ctl > 0 else "You might be tapering or recovering."))

    # Fatigue Insight
    if current['atl'] > current['ctl'] * 1.3:
         st.warning(f"**High Fatigue Warning**\n\nYour acute load ({int(current['atl'])}) is significantly higher than your fitness ({int(current['ctl'])}). Risk of overuse injury.")

    # Form Insight (The most actionable one)
    tsb = current['tsb']
    if tsb < -30:
        st.error(f"**Form: Overload Warning ({int(tsb)})**\n\nYou are in the 'High Risk' zone. Your fatigue is excessive compared to your fitness. Rest is highly recommended.")
    elif -30 <= tsb < -10:
        st.success(f"**Form: Optimal Training ({int(tsb)})**\n\nYou are in the 'Productive' zone. Accumulating fatigue at a sustainable rate to build fitness.")
    elif -10 <= tsb < 10:
        st.info(f"**Form: Neutral / Fresh ({int(tsb)})**\n\nYou are in the 'Transition' zone. Good for maintenance or race week tapering.")
    elif tsb >= 10:
        st.warning(f"**Form: Detraining Warning ({int(tsb)})**\n\nYou are very fresh, but likely losing fitness. If not tapering for a race, increase training load.")

    # --- Graph: Advanced PMC (Performance Management Chart) ---
    st.divider()
    fig = go.Figure()
    # Chronic Load (Fitness) - Area
    fig.add_trace(go.Scatter(x=df_ewma['date'], y=df_ewma['ctl'], fill='tozeroy', name='Fitness (CTL)', line=dict(color='rgba(34, 197, 94, 0.5)')))
    # Acute Load (Fatigue) - Line
    fig.add_trace(go.Scatter(x=df_ewma['date'], y=df_ewma['atl'], name='Fatigue (ATL)', line=dict(color='#be123c')))
    # Form (TSB) - Bar/Line? Usually area or separate. Let's keep it clean with just CTL/ATL for now as main focus.
    
    fig.update_layout(title="Performance Management Chart (EWMA)", height=350, margin=dict(l=20,r=20,t=40,b=20), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    
    # --- Dynamic Readiness ---
    st.divider()
    st.subheader("Dynamic Readiness (Rolling Baseline)")
    
    if len(health) < 7:
        st.warning("Need at least 7 days of health logs for dynamic baselines.")
    else:
        df_h = pd.DataFrame(health)
        df_h['date'] = pd.to_datetime(df_h['date']).dt.date
        df_h = df_h.sort_values('date')
        
        # Get last 7 days BEFORE today for baseline
        baseline_window = df_h[df_h['date'] < today].tail(7)
        if not baseline_window.empty:
            avg_rhr_7d = baseline_window['rhr'].mean()
            avg_hrv_7d = baseline_window['hrv'].mean()
            
            # Get today's values
            today_log = df_h[df_h['date'] == today]
            if not today_log.empty:
                curr_rhr = today_log.iloc[0]['rhr']
                curr_hrv = today_log.iloc[0]['hrv']
                
                target = engine.get_dynamic_daily_target(curr_rhr, curr_hrv, avg_rhr_7d, avg_7d_hrv=avg_hrv_7d)
                
                st.markdown(f"""
                <div style="background-color: {target['bg']}; padding: 1.5rem; border-radius: 12px; border: 1px solid {target['color']};">
                    <h3 style="color: {target['color']}; margin:0;">{target['readiness']} Readiness</h3>
                    <p style="font-weight: bold; margin: 5px 0;">{target['recommendation']}</p>
                    <p>{target['message']}</p>
                    <hr style="margin: 10px 0; border-color: {target['color']}; opacity: 0.3;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
                        <span><b>Baseline RHR:</b> {avg_rhr_7d:.1f}</span>
                        <span><b>Baseline HRV:</b> {avg_hrv_7d:.1f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Log today's health stats to see dynamic readiness.")

def render_cardio():
    st.header(":material/directions_run: Cardio Training")
    setup_page()
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    engine = PhysiologyEngine(st.session_state.data['user_profile'])
    if 'run_log_success' in st.session_state and st.session_state.run_log_success:
        st.toast("✅ Activity Logged Successfully!")
        st.session_state.run_log_success = False
    edit_run_id = st.session_state.get('edit_run_id', None)
    if 'form_act_type' not in st.session_state: st.session_state.form_act_type = "Run"
    def_type = st.session_state.form_act_type
    def_date = get_malaysia_time()
    def_dist, def_dur, def_hr, def_cad, def_pwr, def_elev = 0.0, 0.0, 0, 0, 0, 0
    def_notes, def_feel, def_rpe = "", "Normal", 5
    def_z1, def_z2, def_z3, def_z4, def_z5 = "", "", "", "", ""
    def_shoe = "Default Shoe"
    
    if edit_run_id:
        run_data = next((r for r in st.session_state.data['runs'] if str(r['id']) == str(edit_run_id)), None)
        if run_data:
            def_type = run_data['type']
            def_date = datetime.strptime(run_data['date'], '%Y-%m-%d').date()
            def_dist = run_data['distance']
            def_dur = run_data['duration']
            def_hr = run_data['avgHr']
            def_cad = run_data.get('cadence', 0)
            def_pwr = run_data.get('power', 0)
            def_elev = run_data.get('elevation', 0)
            def_shoe = run_data.get('shoe_id', 'Default Shoe')
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
    expander_state = True if edit_run_id else False
    with st.expander(form_label, expanded=expander_state):
        key_suffix = f"{edit_run_id}" if edit_run_id else "new"
        with st.form("run_form", clear_on_submit=True):
            c_d, c_t = st.columns([1, 3])
            with c_d:
                st.caption("Date")
                act_date = st.date_input("Date", get_malaysia_time() if not edit_run_id else def_date, label_visibility="collapsed", key=f"date_{key_suffix}")
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
            
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                st.caption("Elevation (m)")
                elev = st.number_input("Elevation", min_value=0, value=int(def_elev), label_visibility="collapsed", key=f"elev_{key_suffix}")
            with c_g2:
                st.write("") # Spacer since shoes are removed

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
            if st.form_submit_button("Update Activity" if edit_run_id else "Save Activity"):
                new_id = str(int(time.time()))
                doc_id = str(edit_run_id) if edit_run_id else new_id
                dist_save = dist if dist is not None else 0.0
                
                run_obj = {
                    "id": doc_id, "date": str(act_date), "type": act_type, "distance": dist_save, 
                    "duration": parse_time_input(dur_str), "avgHr": hr, "rpe": rpe, "feel": feel, 
                    "cadence": cadence, "power": power, "elevation": elev, "shoe_id": "default",
                    "z1": parse_time_input(z1), "z2": parse_time_input(z2), "z3": parse_time_input(z3), 
                    "z4": parse_time_input(z4), "z5": parse_time_input(z5), "notes": notes
                }
                if db: db.collection("runs").document(doc_id).set(run_obj)
                if edit_run_id:
                    idx = next((i for i, r in enumerate(st.session_state.data['runs']) if str(r['id']) == str(edit_run_id)), -1)
                    if idx != -1: st.session_state.data['runs'][idx] = run_obj
                    st.session_state.edit_run_id = None; st.session_state.run_log_success = True
                else:
                    st.session_state.data['runs'].insert(0, run_obj); st.session_state.run_log_success = True
                if not db: save_data(st.session_state.data)
                persist(); st.rerun()
        if edit_run_id:
            if st.button("Cancel Edit"): st.session_state.edit_run_id = None; st.rerun()

    st.markdown("### Dashboard & History")
    if 'dash_period' not in st.session_state: st.session_state.dash_period = "Weekly"
    if 'dash_offset' not in st.session_state: st.session_state.dash_offset = 0
    def get_date_range(period, offset):
        today = get_malaysia_time().date()
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
            end_date = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
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
            new_p = st.selectbox("View Period", ["Weekly", "Monthly", "6 Months", "Yearly"], index=["Weekly", "Monthly", "6 Months", "Yearly"].index(st.session_state.dash_period), label_visibility="collapsed")
            if new_p != st.session_state.dash_period: st.session_state.dash_period = new_p; st.session_state.dash_offset = 0; st.rerun()
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
            else: filtered_df = pd.DataFrame(columns=['distance', 'duration', 'avgHr'])
            
            total_dist = filtered_df['distance'].sum() if not filtered_df.empty else 0
            total_mins = filtered_df['duration'].sum() if not filtered_df.empty else 0
            count = len(filtered_df)
            avg_hr = filtered_df['avgHr'].mean() if not filtered_df.empty and filtered_df['avgHr'].sum() > 0 else 0
            pace_label = "-"
            if total_dist > 0: pace_label = format_pace(total_mins / total_dist) + " /km"
            time_label = f"{int(total_mins // 60)}h {int(total_mins % 60)}m"

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
                    zones = [float(row.get(f'z{i}', 0)) for i in range(1,6)]
                    trimp, focus = engine.calculate_trimp(float(row['duration']), int(row['avgHr']), zones)
                    te, te_label = engine.get_training_effect(trimp)
                    
                    elev = row.get('elevation', 0)
                    
                    with st.container(border=True):
                        c_date, c_type, c_stats, c_metrics, c_act = st.columns([1.5, 1.2, 2.5, 2.5, 1])
                        icon_map = {"Run": ":material/directions_run:", "Walk": ":material/directions_walk:", "Ultimate": ":material/sports_handball:"}
                        date_str = datetime.strptime(row['date'], '%Y-%m-%d').strftime('%A, %b %d')
                        c_date.markdown(f"**{date_str}**")
                        c_type.markdown(f"{icon_map.get(row['type'], ':material/help:')} {row['type']}")
                        stats_html = f"""<div style="line-height: 1.5;"><span class="history-sub">Dist:</span> <span class="history-value">{row['distance']}km</span><br><span class="history-sub">Time:</span> <span class="history-value">{format_duration(row['duration'])}</span><br><span class="history-sub">{'Note' if row['type'] == 'Ultimate' else 'Pace'}:</span> <span class="history-value">{row.get('notes','-') if row['type']=='Ultimate' else format_pace(row['duration']/row['distance'] if row['distance']>0 else 0)+'/km'}</span></div>"""
                        c_stats.markdown(stats_html, unsafe_allow_html=True)
                        metrics_list = []
                        if row.get('avgHr') and row['avgHr'] > 0: metrics_list.append(f"<span class='history-sub'>HR:</span> <span class='history-value'>{row['avgHr']}</span>")
                        metrics_list.append(f"<span class='history-sub'>Load:</span> <span class='history-value'>{int(trimp)}</span>")
                        metrics_list.append(f"<span class='history-sub'>TE:</span> <span class='history-value status-badge { 'status-green' if 2<=te<4 else 'status-orange' if te>=4 else 'status-gray' }' style='font-size:0.75rem; padding:1px 6px;'>{te} {te_label.split()[0]}</span>")
                        extras = []
                        if row.get('cadence', 0) > 0: extras.append(f"Cad: {row['cadence']}")
                        if row.get('power', 0) > 0: extras.append(f"Pwr: {row['power']}")
                        if elev > 0: extras.append(f"Elev: {elev}m") # Elevation
                        if extras: metrics_list.append(f"<span class='history-sub'>{' | '.join(extras)}</span>")
                        
                        # Feel
                        feel_val = row.get('feel', '')
                        bottom_line = []
                        if feel_val: bottom_line.append(f"Feel: {feel_val}")
                        if bottom_line: metrics_list.append(f"<span class='history-sub'>{' | '.join(bottom_line)}</span>")
                        
                        metrics_html = "<div style='line-height: 1.5;'>" + "<br>".join(metrics_list) + "</div>"
                        c_metrics.markdown(metrics_html, unsafe_allow_html=True)
                        with c_act:
                            if st.button(":material/edit:", key=f"ed_{row['id']}_{idx}_{filter_cat}"): st.session_state.edit_run_id = row['id']; st.rerun()
                            if st.button(":material/delete:", key=f"del_{row['id']}_{idx}_{filter_cat}"): 
                                if db: db.collection("runs").document(str(row['id'])).delete()
                                st.session_state.data['runs'] = [r for r in st.session_state.data['runs'] if r['id'] != row['id']]; persist(); st.rerun()
                        z_vals = [row.get(f'z{i}', 0) for i in range(1, 6)]
                        total_z_time = sum(z_vals)
                        if total_z_time > 0:
                            pcts = [(v/total_z_time)*100 for v in z_vals]
                            t_strs = [format_duration(v) if v > 0 else "" for v in z_vals]
                            def get_lbl(pct, txt): return txt if pct > 10 else ""
                            bar_html = f"""<div style="display: flex; width: 100%; height: 18px; border-radius: 4px; overflow: hidden; margin-top: 12px; background-color: #f1f5f9;"><div style="width: {pcts[0]}%; background-color: #1e40af; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[0], t_strs[0])}</div><div style="width: {pcts[1]}%; background-color: #60a5fa; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[1], t_strs[1])}</div><div style="width: {pcts[2]}%; background-color: #facc15; color: black; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[2], t_strs[2])}</div><div style="width: {pcts[3]}%; background-color: #fb923c; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[3], t_strs[3])}</div><div style="width: {pcts[4]}%; background-color: #f87171; color: white; font-size: 10px; display: flex; align-items: center; justify-content: center; overflow: hidden;">{get_lbl(pcts[4], t_strs[4])}</div></div>"""
                            st.markdown(bar_html, unsafe_allow_html=True)
                        if row.get('notes'): st.markdown(f"<div style='margin-top:5px; font-size:0.85rem; color:#475569;'>📝 {row['notes']}</div>", unsafe_allow_html=True)
            else: st.info("No activities found for this category.")

def render_trends():
    st.header(":material/calendar_today: Activity Calendar")
    setup_page()
    
    # Session State for Month Navigation
    if 'cal_date' not in st.session_state:
        st.session_state.cal_date = get_malaysia_time().date().replace(day=1)

    # Navigation UI
    c_prev, c_curr, c_next = st.columns([1, 4, 1])
    if c_prev.button("◀ Prev", use_container_width=True):
        prev_month = st.session_state.cal_date.replace(day=1) - timedelta(days=1)
        st.session_state.cal_date = prev_month.replace(day=1)
        st.rerun()
        
    c_curr.markdown(f"<h3 style='text-align: center; margin:0;'>{st.session_state.cal_date.strftime('%B %Y')}</h3>", unsafe_allow_html=True)
    
    if c_next.button("Next ▶", use_container_width=True):
        next_month = (st.session_state.cal_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        st.session_state.cal_date = next_month
        st.rerun()

    # Data Prep
    year = st.session_state.cal_date.year
    month = st.session_state.cal_date.month
    
    runs = st.session_state.data['runs']
    runs_df = pd.DataFrame(runs)
    if not runs_df.empty:
        runs_df['date_dt'] = pd.to_datetime(runs_df['date']).dt.date
    
    # Calendar Generation (Full Weeks)
    cal = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    
    # Headers
    cols = st.columns([1]*7 + [1.5]) # 7 Days + 1 Summary
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, d in enumerate(days):
        cols[i].markdown(f"<div style='text-align:center; font-weight:bold; color:#78716c'>{d}</div>", unsafe_allow_html=True)
    cols[7].markdown(f"<div style='text-align:center; font-weight:bold; color:#c2410c'>Weekly Stats</div>", unsafe_allow_html=True)
    
    st.divider()

    # Render Weeks
    for week in cal:
        cols = st.columns([1]*7 + [1.5])
        
        w_dist = 0
        w_time = 0
        w_elev = 0
        w_count = 0
        
        for i, current_date in enumerate(week):
            with cols[i]:
                # Check for runs
                day_runs = []
                if not runs_df.empty:
                    day_runs = runs_df[runs_df['date_dt'] == current_date]
                
                # Visual distinction
                is_current_month = current_date.month == month
                text_color = "color:#44403c" if is_current_month else "color:#a8a29e"
                
                # Render Day Cell
                with st.container(border=True):
                    # Highlight today
                    if current_date == get_malaysia_time().date():
                        st.markdown(f"<div style='color:#c2410c; font-weight:bold;'>{current_date.day}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='{text_color}; font-size:0.9em; font-weight:{'600' if is_current_month else '400'}'>{current_date.day}</div>", unsafe_allow_html=True)
                    
                    # Spacer to ensure minimum height
                    st.markdown("""<div style="height:30px"></div>""", unsafe_allow_html=True)
                    
                    if not day_runs.empty:
                         for _, r in day_runs.iterrows():
                            # Minimal display: Icon + Dist
                            icon = "directions_run" if r['type'] == "Run" else "directions_walk" if r['type'] == "Walk" else "sports_handball"
                            st.markdown(f"""
                            <div class="cal-activity">
                                <span class="material-symbols-rounded" style="font-size:14px">{icon}</span>
                                <span style="font-size:0.75rem; font-weight:600;">{r['distance']}k</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Add to totals
                            w_dist += r['distance']
                            w_time += r['duration']
                            w_elev += r.get('elevation', 0)
                            w_count += 1
        
        # Render Summary Column
        with cols[7]:
            if w_count > 0:
                with st.container(border=True):
                    st.markdown(f"**Total: {w_dist:.1f} km**")
                    st.caption(f"Time: {format_duration(w_time)}")
                    if w_elev > 0: st.caption(f"Elev: {w_elev}m")
                    st.caption(f"{w_count} Activities")
            else:
                st.write("")

def render_share():
    st.header(":material/share: Export Data")
    setup_page()
    
    with st.container(border=True):
        st.subheader("Configuration")
        
        c_dates, c_dummy = st.columns([2, 1])
        d_range = c_dates.date_input("Date Range", value=(get_malaysia_time() - timedelta(days=6), get_malaysia_time()), format="YYYY/MM/DD")
        start_r, end_r = (d_range if isinstance(d_range, tuple) and len(d_range) == 2 else (d_range[0], d_range[0])) if isinstance(d_range, tuple) else (d_range, d_range)
        
        st.divider()
        
        st.markdown("**Activity Types**")
        c1, c2, c3 = st.columns(3)
        opt_run = c1.checkbox("Run", value=True)
        opt_walk = c2.checkbox("Walk", value=True)
        opt_ult = c3.checkbox("Ultimate", value=True)
        
        st.markdown("**Data Sections**")
        c4, c5, c6 = st.columns(3)
        opt_health = c4.checkbox("Health Logs", value=True)
        opt_status = c5.checkbox("Training Status", value=True)
        opt_adv = c6.checkbox("Adv. Status (EWMA)", value=True)
        
        st.markdown("**Run Details**")
        c7, c8, c9, c10 = st.columns(4)
        det_physio = c7.checkbox("Physio (HR/Load)", value=True)
        det_adv = c8.checkbox("Cadence & Power", value=True)
        det_zones = c9.checkbox("HR Zones", value=True)
        det_notes = c10.checkbox("Notes & Feel", value=True)
        
        st.divider()
        
        # New: CSV Download Buttons
        runs = st.session_state.data.get('runs', [])
        health = st.session_state.data.get('health_logs', [])
        
        if runs:
            df_runs = pd.DataFrame(runs)
            csv_runs = df_runs.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Activities CSV", data=csv_runs, file_name="activities_export.csv", mime="text/csv")
            
        if health:
            df_health = pd.DataFrame(health)
            csv_health = df_health.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Health CSV", data=csv_health, file_name="health_export.csv", mime="text/csv")
        
        st.divider()
        
        if st.button("📄 Generate Text Report", type="primary"):
            options = {
                'run': opt_run, 'walk': opt_walk, 'ultimate': opt_ult,
                'health': opt_health, 'status': opt_status, 'adv_status': opt_adv,
                'det_physio': det_physio, 'det_adv': det_adv, 'det_zones': det_zones, 'det_notes': det_notes
            }
            report_text = generate_report(start_r, end_r, options)
            st.text_area("Copy this text:", value=report_text, height=500)

# --- Main App Logic ---
def main():
    if 'data' not in st.session_state:
        st.session_state.data = load_data()

    selected_tab = render_sidebar()

    if selected_tab == "Training Status":
        render_training_status()
    elif selected_tab == "Advanced Status (Beta)":
        render_advanced_status()
    elif selected_tab == "Cardio Training":
        render_cardio()
    elif selected_tab == "Activity Calendar":
        render_trends()
    elif selected_tab == "Export":
        render_share()

if __name__ == "__main__":
    main()
