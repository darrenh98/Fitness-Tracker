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

# Custom CSS to mimic the slate/minimalist look
st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
    }
    .stCard {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        border: 1px solid #e2e8f0;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
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
    "user_profile": {"age": 30, "height": 175, "weight": 70, "heightUnit": "cm", "weightUnit": "kg"},
    "cycles": {"macro": "", "meso": "", "micro": ""},
    "weekly_plan": {day: {"am": "", "pm": ""} for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']}
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
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

# --- Helper Functions ---
def format_pace(decimal_min):
    if not decimal_min or decimal_min == 0:
        return "-"
    mins = int(decimal_min)
    secs = int((decimal_min - mins) * 60)
    return f"{mins}'{secs:02d}\""

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
    st.markdown("Minimalist Tracking Edition")
    
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
        st.markdown("**Macrocycle (Annual)**")
        macro = st.text_area("Annual Goal", value=st.session_state.data['cycles']['macro'], height=100, key="txt_macro")
        if macro != st.session_state.data['cycles']['macro']:
            st.session_state.data['cycles']['macro'] = macro
            persist()

    with c2:
        st.markdown("**Mesocycle (Block)**")
        meso = st.text_area("Block Focus", value=st.session_state.data['cycles']['meso'], height=100, key="txt_meso")
        if meso != st.session_state.data['cycles']['meso']:
            st.session_state.data['cycles']['meso'] = meso
            persist()

    with c3:
        st.markdown("**Microcycle (Week)**")
        micro = st.text_area("Weekly Focus", value=st.session_state.data['cycles']['micro'], height=100, key="txt_micro")
        if micro != st.session_state.data['cycles']['micro']:
            st.session_state.data['cycles']['micro'] = micro
            persist()

    st.subheader("Weekly Schedule")
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # We use columns to display the week grid
    cols = st.columns(7)
    for i, day in enumerate(days):
        with cols[i]:
            st.caption(day.upper())
            am_val = st.text_input("AM", value=st.session_state.data['weekly_plan'][day]['am'], key=f"am_{day}", placeholder="Rest")
            pm_val = st.text_input("PM", value=st.session_state.data['weekly_plan'][day]['pm'], key=f"pm_{day}", placeholder="Rest")
            
            # Save on change logic (simplified for streamlit, saves on every interaction if key changes)
            if (am_val != st.session_state.data['weekly_plan'][day]['am'] or 
                pm_val != st.session_state.data['weekly_plan'][day]['pm']):
                st.session_state.data['weekly_plan'][day]['am'] = am_val
                st.session_state.data['weekly_plan'][day]['pm'] = pm_val
                persist()

# --- TAB: FIELD (RUNS) ---
elif selected_tab == "Field (Runs)":
    st.header("👟 Field Activities")
    
    # Prepare data for dashboard (always load data first)
    runs_df = pd.DataFrame(st.session_state.data['runs'])
    
    # --- DASHBOARD SECTION (Always Visible) ---
    st.subheader("📊 Dashboard")
    
    # Filter Logic
    filter_type = st.radio("Activity Filter:", ["All", "Run", "Walk", "Ultimate"], horizontal=True, label_visibility="visible")
    
    # Filter Data based on selection
    if not runs_df.empty:
        if filter_type != "All":
            filtered_df = runs_df[runs_df['type'] == filter_type]
        else:
            filtered_df = runs_df
    else:
        # Empty dataframe structure if no data exists
        filtered_df = pd.DataFrame(columns=['distance', 'duration', 'avgHr'])

    # Calculations (Defaults to 0 if empty)
    total_dist = filtered_df['distance'].sum() if not filtered_df.empty else 0
    total_mins = filtered_df['duration'].sum() if not filtered_df.empty else 0
    count = len(filtered_df)
    avg_hr = filtered_df['avgHr'].mean() if not filtered_df.empty and filtered_df['avgHr'].sum() > 0 else 0
    
    # Pace Calculation (Time / Distance)
    if total_dist > 0:
        avg_pace_val = total_mins / total_dist
        pace_label = format_pace(avg_pace_val) + " /km"
    else:
        pace_label = "-"
    
    # Format Time (Decimal mins to HH:MM)
    t_hours = int(total_mins // 60)
    t_mins = int(total_mins % 60)
    time_label = f"{t_hours}h {t_mins}m"

    # Stats Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Dist", f"{total_dist:.1f} km")
    m2.metric("Total Time", time_label)
    m3.metric("Avg Pace", pace_label)
    m4.metric("Avg HR", f"{int(avg_hr)} bpm")
    m5.metric("Count", count)

    st.divider()

    # --- LOGGING FORM (Dropdown/Expander) ---
    with st.expander("➕ Log Activity", expanded=False):
        with st.form("run_form"):
            # Row 1: Basic Info
            c1, c2, c3, c4 = st.columns(4)
            act_type = c1.selectbox("Type", ["Run", "Walk", "Ultimate"])
            act_date = c2.date_input("Date", datetime.now())
            dist = c3.number_input("Distance (km)", min_value=0.0, step=0.01)
            dur_str = c4.text_input("Duration (hh:mm:ss)", placeholder="01:30:00")
            
            # Row 2: Heart Rate & Zones
            st.caption("Heart Rate Zones (Time in mm:ss)")
            rc1, rc2, rc3, rc4, rc5, rc6 = st.columns(6)
            hr = rc1.number_input("Avg HR", min_value=0)
            z1 = rc2.text_input("Zone 1", placeholder="00:00")
            z2 = rc3.text_input("Zone 2", placeholder="00:00")
            z3 = rc4.text_input("Zone 3", placeholder="00:00")
            z4 = rc5.text_input("Zone 4", placeholder="00:00")
            z5 = rc6.text_input("Zone 5", placeholder="00:00")
            
            # Row 3: Notes
            notes = st.text_input("Notes")
            
            submitted = st.form_submit_button("Save Activity")
            if submitted:
                new_run = {
                    "id": int(time.time()),
                    "date": str(act_date),
                    "type": act_type,
                    "distance": dist,
                    "duration": parse_time_input(dur_str),
                    "avgHr": hr,
                    "z1": parse_time_input(z1),
                    "z2": parse_time_input(z2),
                    "z3": parse_time_input(z3),
                    "z4": parse_time_input(z4),
                    "z5": parse_time_input(z5),
                    "notes": notes
                }
                st.session_state.data['runs'].insert(0, new_run)
                persist()
                st.success("Activity Logged!")
                st.rerun()

    # --- HISTORY TABLE ---
    if not runs_df.empty:
        st.subheader("History")
        
        # Format for display
        display_df = filtered_df.copy()
        if not display_df.empty:
            display_df['duration_fmt'] = display_df['duration'].apply(format_pace)
            # Display Columns
            display_df = display_df[['date', 'type', 'distance', 'duration_fmt', 'avgHr', 'notes']]
            display_df.columns = ['Date', 'Type', 'Dist (km)', 'Time', 'HR', 'Notes']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Delete functionality
            with st.expander("Manage Data"):
                run_to_delete = st.selectbox("Select entry to delete", options=runs_df['id'], format_func=lambda x: f"{x} (ID)")
                if st.button("Delete Entry"):
                    st.session_state.data['runs'] = [r for r in st.session_state.data['runs'] if r['id'] != run_to_delete]
                    persist()
                    st.rerun()

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
                st.markdown(f"**{r['name']}**")
                st.caption(" • ".join(r['exercises']))
                if st.button("Delete", key=f"del_rout_{r['id']}"):
                    st.session_state.data['routines'] = [x for x in st.session_state.data['routines'] if x['id'] != r['id']]
                    persist()
                    st.rerun()

    with tab_log:
        routine_opts = {r['name']: r for r in st.session_state.data['routines']}
        selected_r_name = st.selectbox("Select Routine", list(routine_opts.keys()))
        
        if selected_r_name:
            sel_routine = routine_opts[selected_r_name]
            st.subheader(f"Logging: {sel_routine['name']}")
            
            with st.form("gym_log"):
                log_date = st.date_input("Date", datetime.now())
                
                # Dynamic inputs for exercises
                exercises_data = []
                for ex in sel_routine['exercises']:
                    st.markdown(f"**{ex}**")
                    c1, c2, c3 = st.columns(3)
                    w = c1.text_input(f"Weight ({ex})", placeholder="100, 100, 100", help="Comma separated for sets")
                    r = c2.text_input(f"Reps ({ex})", placeholder="10, 8, 8", help="Comma separated for sets")
                    
                    exercises_data.append({"name": ex, "weights": w, "reps": r})
                
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
            st.metric("Total Volume Lifted", f"{total_vol_all/1000:.1f}k kg")
            
            for s in sessions:
                with st.expander(f"{s['date']} - {s['routineName']} (Vol: {s.get('totalVolume',0)}kg)"):
                    for ex in s['exercises']:
                        st.markdown(f"**{ex['name']}**: {len(ex['sets'])} sets")
                    if st.button("Delete Session", key=f"del_sess_{s['id']}"):
                        st.session_state.data['gym_sessions'] = [x for x in st.session_state.data['gym_sessions'] if x['id'] != s['id']]
                        persist()
                        st.rerun()
        else:
            st.info("No gym sessions logged.")

# --- TAB: NUTRITION ---
elif selected_tab == "Nutrition":
    st.header("🥗 Nutrition Log")
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Add Meal")
        with st.form("food_form"):
            f_date = st.date_input("Date", datetime.now())
            meal = st.text_input("Meal Name", placeholder="Chicken Rice")
            cal = st.number_input("Calories", min_value=0)
            prot = st.number_input("Protein (g)", min_value=0)
            carbs = st.number_input("Carbs (g)", min_value=0)
            fat = st.number_input("Fat (g)", min_value=0)
            
            if st.form_submit_button("Add Meal"):
                new_food = {
                    "id": int(time.time()),
                    "date": str(f_date),
                    "meal": meal,
                    "calories": cal,
                    "protein": prot,
                    "carbs": carbs,
                    "fat": fat
                }
                st.session_state.data['nutrition_logs'].insert(0, new_food)
                persist()
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
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calories", t_cal)
        col2.metric("Protein", f"{t_pro}g")
        col3.metric("Carbs", f"{t_carb}g")
        col4.metric("Fat", f"{t_fat}g")
        
        # History
        st.subheader("Recent Meals")
        nut_df = pd.DataFrame(st.session_state.data['nutrition_logs'])
        if not nut_df.empty:
            st.dataframe(nut_df[['date', 'meal', 'calories', 'protein', 'carbs', 'fat']], use_container_width=True, hide_index=True)
        else:
            st.info("No meals logged.")

# --- TAB: STATS (HEALTH) ---
elif selected_tab == "Stats":
    st.header("❤️ Physiological Stats")
    
    with st.expander("➕ Log Health Stats"):
        with st.form("health_form"):
            h_date = st.date_input("Date", datetime.now())
            rhr = st.number_input("Resting HR", min_value=30, max_value=150)
            hrv = st.number_input("HRV (ms)", min_value=0)
            vo2 = st.number_input("VO2 Max", min_value=0.0, step=0.1)
            sleep = st.number_input("Sleep (hrs)", min_value=0.0, step=0.1)
            
            if st.form_submit_button("Log Stats"):
                new_h = {
                    "id": int(time.time()),
                    "date": str(h_date),
                    "rhr": rhr,
                    "hrv": hrv,
                    "vo2Max": vo2,
                    "sleepHours": sleep
                }
                st.session_state.data['health_logs'].insert(0, new_h)
                persist()
                st.rerun()

    health_df = pd.DataFrame(st.session_state.data['health_logs'])
    
    if not health_df.empty:
        # Ensure date is datetime for sorting
        health_df['date'] = pd.to_datetime(health_df['date'])
        health_df = health_df.sort_values(by='date')
        
        # Charts
        c1, c2 = st.columns(2)
        
        with c1:
            fig_hrv = px.line(health_df, x='date', y='hrv', title="HRV Trends", markers=True)
            fig_hrv.update_traces(line_color='#22c55e')
            st.plotly_chart(fig_hrv, use_container_width=True)
            
        with c2:
            fig_sleep = px.bar(health_df, x='date', y='sleepHours', title="Sleep Duration")
            fig_sleep.update_traces(marker_color='#6366f1')
            st.plotly_chart(fig_sleep, use_container_width=True)
            
        c3, c4 = st.columns(2)
        with c3:
            fig_rhr = px.line(health_df, x='date', y='rhr', title="Resting Heart Rate", markers=True)
            fig_rhr.update_traces(line_color='#ef4444')
            st.plotly_chart(fig_rhr, use_container_width=True)
            
        with c4:
            fig_vo2 = px.line(health_df, x='date', y='vo2Max', title="VO2 Max", markers=True)
            fig_vo2.update_traces(line_color='#3b82f6')
            st.plotly_chart(fig_vo2, use_container_width=True)
            
    else:
        st.info("No health stats logged yet.")
