"""AeroRecover - Agentic Recovery Console (Enterprise MVP). No real APIs are called."""
import hashlib
import html
import time
import streamlit as st

st.set_page_config(page_title="AeroRecover | Recovery Console", page_icon="✈️", layout="wide")

THRESHOLD = 5000
STAGES = ["idle", "orch_run", "p1_run", "p1_wait_reply", "p1_done", "p2_run", "await_human", "approving", "done"]
FORCE_MAJEURE = {"fog", "weather", "security"}

# ------------------------------------------------------------------
# Enterprise UI CSS (No AI-look, high-end SaaS feel)
# ------------------------------------------------------------------
CSS = """<style>
/* Base App Styling */
.stApp { background: #F8FAFC; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1200px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0F172A; border-right: 1px solid #1E293B; }
[data-testid="stSidebar"] * { color: #F8FAFC !important; }
[data-testid="stSidebar"] .stButton>button { background: #EAB308; color: #0F172A !important; font-weight: 700; border: none; }
[data-testid="stSidebar"] .stButton>button:hover { background: #CA8A04; }

/* Typography */
h1, h2, h3 { color: #0F172A; font-family: 'Inter', sans-serif; font-weight: 700; }
p, li, div { font-family: 'Inter', sans-serif; color: #334155; }

/* Cards */
.card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.card-header { font-size: 0.85rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
.val-large { font-size: 1.8rem; font-weight: 800; color: #0F172A; line-height: 1.2; }

/* Status Badges */
.badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
.badge-green { background: #DCFCE7; color: #166534; border: 1px solid #BBF7D0; }
.badge-orange { background: #FFEDD5; color: #9A3412; border: 1px solid #FED7AA; }
.badge-blue { background: #DBEAFE; color: #1E40AF; border: 1px solid #BFDBFE; }

/* Action Boxes */
.alert-success { background: #F0FDF4; border-left: 4px solid #22C55E; padding: 16px; border-radius: 6px; margin: 16px 0; }
.alert-warn { background: #FFFBEB; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 6px; margin: 16px 0; }
.alert-info { background: #EFF6FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 6px; margin: 16px 0; }

/* WhatsApp UI (Cleaner, less cartoony) */
.wa-container { background: #E5DDD5; border-radius: 12px; overflow: hidden; margin: 16px 0; border: 1px solid #D1D5DB; }
.wa-header { background: #075E54; color: white; padding: 12px 16px; font-weight: 600; font-size: 0.95rem; display: flex; align-items: center; }
.wa-body { padding: 16px; }
.wa-msg { max-width: 85%; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; font-size: 0.9rem; line-height: 1.4; background: #FFF; box-shadow: 0 1px 1px rgba(0,0,0,0.1); }
.wa-msg.out { background: #DCF8C6; margin-left: auto; }
.wa-time { font-size: 0.65rem; color: #64748B; text-align: right; margin-top: 4px; }

/* Tables */
.data-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.data-table th { text-align: left; padding: 12px; border-bottom: 1px solid #E2E8F0; color: #64748B; font-weight: 600; }
.data-table td { padding: 12px; border-bottom: 1px solid #E2E8F0; }
.data-table tr:last-child td { border-bottom: none; }

/* Hide standard Streamlit UI clutter */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------
# Logic & Math (Deterministic)
# ------------------------------------------------------------------
def inr(n): return f"₹{n:,}"

def fare_difference(new_fare, credit): return new_fare - credit

def dgca_compensation(block_min, cause):
    slab = 5000 if block_min <= 60 else 7500 if block_min <= 120 else 10000
    return slab, (0 if cause in FORCE_MAJEURE else slab)

def hitl_gate(diff, same_cabin, ssr):
    if ssr: return "HUMAN", "Medical / SSR case"
    if not same_cabin: return "HUMAN", "Cabin change"
    if diff < THRESHOLD: return "AUTO", "Within auto-execute limit"
    return "HUMAN", "Fare difference above threshold"

# ------------------------------------------------------------------
# Mock Data
# ------------------------------------------------------------------
def opts(rows): return [dict(flight=f, dep=d, arr=a, fare=x, cabin="Economy", note=n) for f, d, a, x, n in rows]

P1 = dict(name="Rohan Mehta", first="Rohan", pnr="R7K2MQ", loyalty="Gold", route="DEL → BOM",
          orig="SJ 2145 · 06:10", orig_fare=5200, cabin="Economy", ssr=False, block=130, cause="fog",
          options=opts([("SJ 887", "10:45", "12:55", 8700, "Earliest arrival"),
                        ("NV 312", "12:10", "14:20", 9100, "Partner · bag included"),
                        ("AX 640", "14:30", "16:40", 10400, "Latest arrival")]))

P2 = dict(name="Ananya Iyer", first="Ananya", pnr="B9T4QX", loyalty="Platinum", route="DEL → BLR",
          orig="SJ 6309 · 07:00", orig_fare=6000, cabin="Economy", ssr=False, block=170, cause="fog",
          options=opts([("SJ 819", "11:30", "14:15", 13500, "Earliest arrival · last seats"),
                        ("NV 466", "13:05", "15:50", 14200, "Partner · bag included"),
                        ("AX 731", "15:40", "18:25", 15900, "Latest arrival")]))

QUEUE = [("R7K2MQ", "Rohan Mehta", "DEL → BOM", 92), ("B9T4QX", "Ananya Iyer", "DEL → BLR", 88),
         ("M3P8LD", "Vikram Rao", "DEL → HYD", 74), ("K5X1ZN", "Sana Qureshi", "DEL → CCU", 69),
         ("T2W6HC", "Arjun Nair", "DEL → GOI", 61)]

def resolve(p):
    o = p["options"][0]
    diff = fare_difference(o["fare"], p["orig_fare"])
    slab, pay = dgca_compensation(p["block"], p["cause"])
    route, why = hitl_gate(diff, o["cabin"] == p["cabin"], p["ssr"])
    sig = hashlib.sha256(f"{p['pnr']}|{o['flight']}|{diff}".encode()).hexdigest()[:10]
    return dict(p=p, o=o, diff=diff, slab=slab, pay=pay, route=route, why=why, sig=sig)

# ------------------------------------------------------------------
# State Management
# ------------------------------------------------------------------
ss = st.session_state
if "stage" not in ss:
    ss.stage = "idle"
    ss.pax = {"p1": resolve(P1), "p2": resolve(P2)}
    ss.p1_choice = None

idx = STAGES.index(ss.stage)
r1, r2 = ss.pax["p1"], ss.pax["p2"]

def go(stage):
    ss.stage = stage

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='color:#EAB308;'>✈️ AeroRecover</h2>", unsafe_allow_html=True)
    st.markdown("---")
    st.checkbox("⚡ Fast mode (skip delays)", key="fast")
    st.button("↺ Reset Simulation", on_click=go, args=("idle",), use_container_width=True)
    st.markdown("---")
    st.markdown("**System Status:** Operational")
    st.markdown(f"**HITL Threshold:** {inr(THRESHOLD)}")
    st.caption("Simulation only. No real GDS, PSS or WhatsApp APIs are called.")

# ------------------------------------------------------------------
# Main Dashboard Header
# ------------------------------------------------------------------
st.markdown("<h1 style='margin-bottom:0;'>Recovery Operations Console</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#64748B; font-size:1.1rem;'>Agentic recovery layer for Delhi (DEL) · governed execution</p>", unsafe_allow_html=True)

# KPI Row
kp_col1, kp_col2, kp_col3, kp_col4 = st.columns(4)
with kp_col1:
    st.markdown(f'<div class="card"><div class="card-header">Stranded PNRs</div><div class="val-large">{"312" if idx >= 2 else "—"}</div><div style="font-size:0.8rem; color:#64748B;">Triage-scored</div></div>', unsafe_allow_html=True)
with kp_col2:
    st.markdown(f'<div class="card"><div class="card-header">Auto-resolved</div><div class="val-large">{"1" if idx >= 4 else "0"}</div><div style="font-size:0.8rem; color:#64748B;">Under {inr(THRESHOLD)}</div></div>', unsafe_allow_html=True)
with kp_col3:
    st.markdown(f'<div class="card"><div class="card-header">Awaiting Human</div><div class="val-large">{"1" if ss.stage == "await_human" else "0"}</div><div style="font-size:0.8rem; color:#64748B;">Above {inr(THRESHOLD)}</div></div>', unsafe_allow_html=True)
with kp_col4:
    st.markdown(f'<div class="card"><div class="card-header">Avg Handling Time</div><div class="val-large">{"3m 27s" if idx >= 8 else "—"}</div><div style="font-size:0.8rem; color:#64748B;">Baseline: 45-90m</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------
# Workflow Logic
# ------------------------------------------------------------------
if idx == 0:
    st.markdown('<div class="alert-info"><b>Scenario:</b> It is 06:00 IST and dense fog has closed Delhi airport. Trigger the disruption to watch AeroRecover recover passengers.</div>', unsafe_allow_html=True)
    st.button("🌫️ Trigger Fog Disruption at DEL", on_click=go, args=("orch_run",), type="primary")
else:
    st.markdown('<div class="alert-warn"><b>ACTIVE DISRUPTION:</b> Dense fog at DEL (VIDP) · CAT-III suspended · 47 departures affected</div>', unsafe_allow_html=True)

# -- Phase 1: Orchestrator --
if idx >= 1:
    st.markdown("### 1. Orchestrator & Triage")
    if ss.stage == "orch_run":
        with st.spinner("Orchestrator Agent: Matching 47 cancelled flights against PNR store..."):
            time.sleep(1 if not ss.get("fast") else 0.1)
        go("p1_run")
        st.rerun()
    else:
        # Professional Data Table
        table_html = '<div class="card"><table class="data-table"><tr><th>Priority</th><th>PNR</th><th>Passenger</th><th>Route</th><th>Status</th></tr>'
        for i, (pnr, n, rt, sc) in enumerate(QUEUE, 1):
            status = '<span class="badge badge-blue">Traced</span>' if i <= 2 else '<span class="badge badge-green">Parallel</span>'
            table_html += f'<tr><td><b>{sc}</b></td><td>{pnr}</td><td>{n}</td><td>{rt}</td><td>{status}</td></tr>'
        table_html += '</table></div>'
        st.markdown(table_html, unsafe_allow_html=True)

# -- Phase 2 & 3: Passengers --
if idx >= 2:
    c1, c2 = st.columns(2, gap="large")

    # PASSENGER 1 (WhatsApp Interactive Flow)
    with c1:
        st.markdown("### 2. Passenger 1 (Auto-Execution)")
        st.markdown(f'<div class="card"><b>{P1["name"]}</b> <span class="badge badge-blue">Gold</span> <span class="badge badge-orange">Cancelled</span><br><span style="color:#64748B; font-size:0.9rem;">PNR {P1["pnr"]} · {P1["route"]}</span></div>', unsafe_allow_html=True)
        
        if ss.stage == "p1_run":
            with st.spinner("Agents calculating options & DGCA rules..."):
                time.sleep(1.5 if not ss.get("fast") else 0.1)
            go("p1_wait_reply")
            st.rerun()
            
        elif ss.stage == "p1_wait_reply":
            st.markdown(f'<div class="alert-success"><b>✅ AUTO-EXECUTION TRIGGERED</b><br>Fare diff {inr(r1["diff"])} is below {inr(THRESHOLD)}. No human needed. Sending WhatsApp options.</div>', unsafe_allow_html=True)
            
            # WhatsApp UI
            wa_html = f'''
            <div class="wa-container">
                <div class="wa-header">💬 AeroRecover Concierge</div>
                <div class="wa-body">
                    <div class="wa-msg">Hi {P1['first']} 👋 Your flight {P1['orig']} is cancelled due to fog.<br><br>I found options for you:<br><b>1.</b> Rebook SJ 887 (10:45 AM) for {inr(r1['diff'])} diff.<br><b>2.</b> Full DGCA Refund.<br><b>3.</b> Hotel + Next day flight.<br><br>Reply with a number to confirm.</div>
                </div>
            </div>
            '''
            st.markdown(wa_html, unsafe_allow_html=True)
            
            # The Interactive Buttons
            st.write("**Simulate Passenger Reply:**")
            b1, b2, b3 = st.columns(3)
            if b1.button("Reply: 1", key="reply1", use_container_width=True):
                ss.p1_choice = "1"
                go("p1_done")
                st.rerun()
            if b2.button("Reply: 2", key="reply2", use_container_width=True):
                ss.p1_choice = "2"
                go("p1_done")
                st.rerun()
            if b3.button("Reply: 3", key="reply3", use_container_width=True):
                ss.p1_choice = "3"
                go("p1_done")
                st.rerun()
                
        elif idx >= 4:
            with st.expander("🔍 View AI Agent Thinking Log"):
                st.code(f"Rebooking Agent: Querying GDS...\nFare Agent: fare_diff(8700, 5200) = 3500\nHITL Policy: 3500 < 5000 -> AUTO\nPSS API: Ticket reissued.")
            
            if ss.p1_choice == "1":
                st.markdown(f'<div class="alert-success"><b>✅ TICKET REISSUED</b><br>Passenger selected option 1. Fare collected: {inr(r1["diff"])}.</div>', unsafe_allow_html=True)
                success_msg = f"✅ <b>Confirmed!</b> You are rebooked on SJ 887 (10:45 AM).<br>Fare difference {inr(r1['diff'])} charged.<br>🍽️ ₹500 meal voucher added."
            elif ss.p1_choice == "2":
                st.markdown(f'<div class="alert-success"><b>✅ REFUND PROCESSED</b><br>Passenger opted for DGCA full refund.</div>', unsafe_allow_html=True)
                success_msg = f"✅ <b>Refund Initiated.</b> Your original fare of {inr(5200)} will hit your account in 5-7 days."
            else:
                st.markdown(f'<div class="alert-success"><b>✅ HOTEL VOUCHER ISSUED</b><br>Passenger opted for hotel + next-day flight.</div>', unsafe_allow_html=True)
                success_msg = f"✅ <b>Hotel Booked.</b> We've booked the Airport Marriott for tonight. Your new flight is tomorrow at 10:00 AM."
            
            # Final WhatsApp
            wa_final = f'''
            <div class="wa-container">
                <div class="wa-header">💬 AeroRecover Concierge</div>
                <div class="wa-body">
                    <div class="wa-msg out">Reply: {ss.p1_choice}</div>
                    <div class="wa-msg">{success_msg}</div>
                </div>
            </div>
            '''
            st.markdown(wa_final, unsafe_allow_html=True)

    # PASSENGER 2 (Human-in-the-Loop Flow)
    if idx >= 5:
        with c2:
            st.markdown("### 3. Passenger 2 (Human Escalation)")
            st.markdown(f'<div class="card"><b>{P2["name"]}</b> <span class="badge badge-blue">Platinum</span> <span class="badge badge-orange">Cancelled</span><br><span style="color:#64748B; font-size:0.9rem;">PNR {P2["pnr"]} · {P2["route"]}</span></div>', unsafe_allow_html=True)
            
            if ss.stage == "p2_run":
                with st.spinner("Agents calculating options & DGCA rules..."):
                    time.sleep(1.5 if not ss.get("fast") else 0.1)
                go("await_human")
                st.rerun()
                
            elif ss.stage in ("await_human", "approving"):
                st.markdown(f'<div class="alert-warn"><b>⏸ HUMAN APPROVAL REQUIRED</b><br>Fare difference {inr(r2["diff"])} breaches {inr(THRESHOLD)} threshold.</div>', unsafe_allow_html=True)
                
                # Resolution Pack
                pack_html = f'''
                <div class="card" style="border-left: 4px solid #EAB308;">
                    <div class="card-header">Resolution Pack Generated</div>
                    <table class="data-table">
                        <tr><td><b>Recommended Flight</b></td><td>SJ 819 · 11:30 → 14:15</td></tr>
                        <tr><td><b>Fare Math</b></td><td>₹13,500 - ₹6,000 credit = <b>{inr(r2["diff"])}</b></td></tr>
                        <tr><td><b>DGCA Entitlement</b></td><td>Force Majeure (Fog) - No cash comp.</td></tr>
                        <tr><td><b>Risk Flags</b></td><td>Platinum Tier · 2 seats left</td></tr>
                    </table>
                </div>
                '''
                st.markdown(pack_html, unsafe_allow_html=True)
                
                if ss.stage == "await_human":
                    st.button("✅ Approve & Execute Ticket", on_click=go, args=("approving",), type="primary", use_container_width=True)
                else:
                    with st.spinner("Executing booking via PSS API..."):
                        time.sleep(1)
                    go("done")
                    st.rerun()
                    
            elif idx >= 8:
                st.markdown(f'<div class="alert-success"><b>✅ APPROVED & EXECUTED</b><br>Human agent approved {inr(r2["diff"])} fare diff.</div>', unsafe_allow_html=True)
                wa_final2 = f'''
                <div class="wa-container">
                    <div class="wa-header">💬 AeroRecover Concierge</div>
                    <div class="wa-body">
                        <div class="wa-msg">Hi {P2['first']}, a specialist has confirmed your new flight.</div>
                        <div class="wa-msg">✅ <b>Confirmed!</b> You are on SJ 819 (11:30 AM).<br>Fare difference {inr(r2['diff'])} charged.<br>🍯 ₹500 voucher added.</div>
                    </div>
                </div>
                '''
                st.markdown(wa_final2, unsafe_allow_html=True)

# -- Phase 4: Summary --
if ss.stage == "done":
    st.markdown("---")
    st.markdown("### Run Summary")
    st.markdown('<div class="alert-success"><b>🏁 2 of 2 passengers recovered.</b><br>Passenger 1 resolved in 2m 41s (Auto). Passenger 2 resolved in 4m 12s (Human Approved). Manual baseline: 45-90 mins.</div>', unsafe_allow_html=True)
