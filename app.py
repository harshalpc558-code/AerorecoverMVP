"""AeroRecover - Agentic Recovery Console (mock MVP). No real APIs are called."""
import hashlib
import html
import time

import streamlit as st

st.set_page_config(page_title="AeroRecover | Recovery Console", page_icon="✈️", layout="wide")

THRESHOLD = 5000
STAGES = ["idle", "orch_run", "p1_run", "p1_wait_reply", "p1_choice", "p2_run", "await_human", "approving", "done"]
FORCE_MAJEURE = {"fog", "weather", "security"}

CSS = """<style>
.stApp{background:#0B192C;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2rem;max-width:1280px;}
[data-testid="stSidebar"]{background:#081322;border-right:1px solid #1E3A5F;}
.stApp, .stApp label, .stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li{color:#F1F5F9;}
.hero{font-size:2.1rem;font-weight:800;color:#EAB308;}
.sub{color:#CBD5E1;margin-bottom:1rem;}
.sec{color:#EAB308;font-weight:800;font-size:1.05rem;margin:1.2rem 0 .6rem;border-bottom:2px solid #EAB308;padding-bottom:4px;}
.card{background:#fff;border-radius:14px;padding:14px 16px;margin-bottom:12px;box-shadow:0 4px 14px rgba(0,0,0,.35);}
.stApp .card, .stApp .card *{color:#0B192C;}
.stApp .card .amber, .amber{color:#B45309;font-weight:800;}
.stApp .card .kl{font-size:.75rem;font-weight:700;color:#475569;}
.kv{font-size:1.8rem;font-weight:800;}
.stApp .card .ks{font-size:.75rem;color:#64748B;}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.72rem;font-weight:800;background:#E2E8F0;margin-left:4px;}
.chip.o{background:#FFEDD5;}
.chip.g{background:#DCFCE7;}
.ok{background:#16A34A;border-left:8px solid #14532D;border-radius:12px;padding:12px 16px;margin:10px 0;font-weight:700;}
.stApp .ok, .stApp .ok *{color:#fff;}
.warn{background:#F97316;border-left:8px solid #9A3412;border-radius:12px;padding:12px 16px;margin:10px 0;font-weight:700;}
.stApp .warn, .stApp .warn *{color:#1F1300;}
.banner{background:#EAB308;border-radius:12px;padding:10px 16px;margin:6px 0 10px;font-weight:700;}
.stApp .banner, .stApp .banner *{color:#0B192C;}
.opt{display:flex;gap:10px;align-items:center;padding:8px 10px;border-radius:10px;border:1px solid #E2E8F0;margin:6px 0;font-size:.88rem;}
.opt.best{border:2px solid #EAB308;background:#FEF9C3;}
.fl{flex:1;}
.pk{display:flex;gap:10px;padding:6px 0;border-bottom:1px solid #E2E8F0;font-size:.88rem;}
.pk b{min-width:110px;}
.log{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.82rem;}
.ll{padding:3px 0;border-bottom:1px dashed #E2E8F0;}
.stApp .card .tag{display:inline-block;background:#0B192C;color:#EAB308;padding:1px 8px;border-radius:6px;margin-right:8px;font-size:.72rem;font-weight:800;}
.lh{font-weight:800;margin-bottom:6px;}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:#EAB308;margin-right:8px;animation:pulse 1s infinite;}
@keyframes pulse{0%,100%{opacity:.25}50%{opacity:1}}
.wa{background:#E5DDD5;border-radius:14px;overflow:hidden;margin-bottom:12px;box-shadow:0 4px 14px rgba(0,0,0,.35);}
.wah{background:#075E54;padding:10px 14px;font-weight:700;}
.stApp .wah, .stApp .wah *{color:#fff;}
.wab{padding:10px 12px;}
.b{width:fit-content;max-width:88%;padding:8px 10px;border-radius:10px;margin:6px 0;font-size:.9rem;line-height:1.35;background:#fff;}
.b.out{background:#DCF8C6;margin-left:auto;}
.stApp .wa .b, .stApp .wa .b *{color:#111827;}
.stApp .wa .bt{font-size:.65rem;text-align:right;color:#6B7280;}
[data-testid="stExpander"]{background:#fff;border-radius:12px;border:0;margin-bottom:12px;}
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] summary *{color:#0B192C !important;font-weight:700;}
.stApp [data-testid="stExpander"] .card{box-shadow:none;padding:4px;}
.stButton>button{background:#EAB308;border:0 !important;border-radius:10px;padding:.7rem 1.2rem;width:100%;}
.stButton>button p{color:#0B192C !important;font-weight:800;}
.stButton>button:hover{background:#FACC15;}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Deterministic "symbolic" tools. The LLM never does this arithmetic.
# ------------------------------------------------------------------
def inr(n):
    return f"₹{n:,}"


def fare_difference(new_fare, credit):
    return new_fare - credit


def dgca_compensation(block_min, cause):
    """CAR Sec 3, Series M, Part IV slabs; extraordinary circumstances = no cash compensation."""
    slab = 5000 if block_min <= 60 else 7500 if block_min <= 120 else 10000
    return slab, (0 if cause in FORCE_MAJEURE else slab)


def hitl_gate(diff, same_cabin, ssr):
    if ssr:
        return "HUMAN", "Medical / SSR case"
    if not same_cabin:
        return "HUMAN", "Cabin change"
    if diff < THRESHOLD:
        return "AUTO", "Within auto-execute limit"
    return "HUMAN", "Fare difference above threshold"


# ------------------------------------------------------------------
# Mock data (fictional carriers SJ / NV / AX)
# ------------------------------------------------------------------
def opts(rows):
    return [dict(flight=f, dep=d, arr=a, fare=x, cabin="Economy", note=n) for f, d, a, x, n in rows]


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
ORCH = [("Orchestrator", "NOTAM received: dense fog at VIDP (DEL), CAT-III ops suspended."),
        ("Orchestrator", "Matching 47 cancelled / delayed departures against the PNR store ..."),
        ("Triage Agent", "Scoring PNRs on urgency, loyalty, connection risk and entitlement ..."),
        ("Triage Agent", "312 stranded PNRs identified. Priority queue built, auto vs human flag set per PNR."),
        ("Orchestrator", "Dispatching Rebook, Fare + DGCA and Care agents in parallel ...")]


def resolve(p):
    o = p["options"][0]
    diff = fare_difference(o["fare"], p["orig_fare"])
    slab, pay = dgca_compensation(p["block"], p["cause"])
    route, why = hitl_gate(diff, o["cabin"] == p["cabin"], p["ssr"])
    sig = hashlib.sha256(f"{p['pnr']}|{o['flight']}|{diff}".encode()).hexdigest()[:10]
    return dict(p=p, o=o, diff=diff, slab=slab, pay=pay, route=route, why=why, sig=sig)


def thinking_log(r):
    p, o = r["p"], r["o"]
    cmp_ = "<" if r["diff"] < THRESHOLD else "≥"
    L = [("Rebooking Agent", f"Querying mock GDS for {p['route']} · {p['cabin']} · 08:00-16:00 ..."),
         ("Rebooking Agent", "GDS returned 14 itineraries. 3 compliant options after fare-bucket, baggage and seat checks."),
         ("Rebooking Agent", f"Rank #1: {o['flight']} · {o['dep']} → {o['arr']} · {inr(o['fare'])}"),
         ("RAG Agent", "Querying DGCA CAR Section 3, Series M, Part IV ... policy index v2026.10, freshness check passed."),
         ("Fare Agent · Python", f"fare_difference(new={inr(o['fare'])}, credit={inr(p['orig_fare'])}) = {inr(r['diff'])}  [deterministic, no LLM math]"),
         ("RAG Agent", f"dgca_compensation(block={p['block']} min, cause='{p['cause']}') → slab {inr(r['slab'])}, payable {inr(r['pay'])} (force majeure). Refund option {inr(p['orig_fare'])}. Refund calculated."),
         ("Care Agent", f"Meal voucher {inr(500)} eligible, queued for partner API."),
         ("HITL Policy Gate", f"Cabin match · diff {inr(r['diff'])} {cmp_} {inr(THRESHOLD)} · SSR/medical: none → {r['route']}")]
    if r["route"] == "AUTO":
        L += [("PSS Write API", f"Reissue ticket on {o['flight']} · idempotency key {r['sig']} · status HK confirmed."),
              ("Communications", "WhatsApp confirmation sent with e-ticket."),
              ("Audit Agent", f"Ledger entry #{r['sig']} appended (tamper-evident).")]
    else:
        L += [("Orchestrator", "Execution PAUSED. Building Resolution Pack for human approval."),
              ("Communications", "Holding message sent to passenger on WhatsApp.")]
    return L


def approve_log(r):
    o = r["o"]
    return [("Human Agent", "Duty Manager reviewed the Resolution Pack and clicked Approve."),
            ("PSS Write API", f"Reissue ticket on {o['flight']} · idempotency key {r['sig']} · status HK confirmed."),
            ("Fare Agent · Python", f"Charging {inr(r['diff'])} via payment gateway · reconciled."),
            ("Care Agent", f"Meal voucher {inr(500)} issued."),
            ("Communications", "WhatsApp confirmation and e-ticket sent."),
            ("Audit Agent", f"Ledger entry #{r['sig']} appended with approver and policy version.")]


# ------------------------------------------------------------------
# UI helpers
# ------------------------------------------------------------------
def md(h):
    st.markdown(h, unsafe_allow_html=True)


def pause(s):
    time.sleep(s * (0.2 if st.session_state.get("fast") else 1))


def go(stage):
    st.session_state.stage = stage


def kpi(label, value, sub):
    return f'<div class="card"><div class="kl">{label}</div><div class="kv">{value}</div><div class="ks">{sub}</div></div>'


def log_html(lines, title=None):
    head = f'<div class="lh"><span class="dot"></span>{title} is thinking ...</div>' if title else ""
    rows = "".join(f'<div class="ll"><span class="tag">{html.escape(a)}</span>{html.escape(t)}</div>' for a, t in lines)
    return f'<div class="card log">{head}{rows}</div>'


def stream(title, lines, delay=0.85):
    slot, shown = st.empty(), []
    for ln in lines:
        shown.append(ln)
        slot.markdown(log_html(shown, title), unsafe_allow_html=True)
        pause(delay)
    slot.empty()


def pax_card(r):
    p = r["p"]
    return (f'<div class="card"><b style="font-size:1.1rem">{p["name"]}</b><span class="chip">{p["loyalty"]}</span>'
            f'<span class="chip o">CANCELLED</span><div>PNR <b>{p["pnr"]}</b> · {p["route"]}</div>'
            f'<div class="ks">{p["orig"]} · paid {inr(p["orig_fare"])} · {p["cabin"]}</div></div>')


def options_html(r):
    rows = ""
    for i, o in enumerate(r["p"]["options"], 1):
        best = " best" if i == 1 else ""
        tag = '<span class="chip g">Selected</span>' if i == 1 else ""
        rows += (f'<div class="opt{best}"><b>#{i}</b><span class="fl"><b>{o["flight"]}</b> · {o["dep"]} → {o["arr"]}'
                 f'<br><span class="ks">{o["note"]}</span></span><b>{inr(o["fare"])}</b>{tag}</div>')
    return f'<div class="card"><div class="amber">GDS options (ranked by arrival, fare, baggage)</div>{rows}</div>'


def pack_html(r):
    p, o = r["p"], r["o"]
    rows = [("Escalation", f"Fare difference {inr(r['diff'])} ≥ {inr(THRESHOLD)} threshold"),
            ("Recommended", f"{o['flight']} · {o['dep']} → {o['arr']} · {o['cabin']}"),
            ("Fare math", f"{inr(o['fare'])} − {inr(p['orig_fare'])} credit = <b>{inr(r['diff'])}</b> (Python, pre-calculated)"),
            ("DGCA check", f"CAR 3-M-IV slab {inr(r['slab'])} · payable {inr(r['pay'])} (fog = force majeure)"),
            ("Entitlements", f"Meal voucher {inr(500)} · full-refund alternative {inr(p['orig_fare'])}"),
            ("Risk flags", f"{p['loyalty']} loyalty · no SSR/medical · 2 seats left, hold 15 min"),
            ("Checks", "Policy ✓ · Inventory ✓ · Permissions ✓")]
    body = "".join(f'<div class="pk"><b>{k}</b><span>{v}</span></div>' for k, v in rows)
    return f'<div class="card"><div class="amber">📦 RESOLUTION PACK · {p["pnr"]}</div>{body}</div>'


def wa_html(msgs):
    b = "".join(f'<div class="b {k}">{t}<div class="bt">{ts}</div></div>' for k, t, ts in msgs)
    return f'<div class="wa"><div class="wah">💬 WhatsApp · passenger’s phone</div><div class="wab">{b}</div></div>'


# ------------------------------------------------------------------
# State
# ------------------------------------------------------------------
ss = st.session_state
if "stage" not in ss:
    ss.stage = "idle"
    ss.pax = {"p1": resolve(P1), "p2": resolve(P2)}
    ss.p1_choice = None
idx = STAGES.index(ss.stage)
r1, r2 = ss.pax["p1"], ss.pax["p2"]

with st.sidebar:
    md('<div class="hero" style="font-size:1.5rem">✈️ AeroRecover</div>')
    st.checkbox("⚡ Fast demo mode", key="fast")
    st.button("↺ Reset demo", key="reset", on_click=go, args=("idle",))
    st.markdown("**Neuro-symbolic design**\n\nThe LLM routes and explains. Python tools calculate every fare, refund and DGCA entitlement.\n\n"
                f"**HITL rule**\n\nAuto-execute below {inr(THRESHOLD)}. Medical, SSR or {inr(THRESHOLD)} and above goes to a human with a Resolution Pack.")
    st.caption("Simulation only. No real GDS, PSS or WhatsApp calls are made.")

md('<div class="hero">✈️ AeroRecover · Recovery Operations Console</div>'
   '<div class="sub">Agentic recovery layer for Delhi (DEL) · governed execution, human approval on edge cases</div>')

kp = [("Stranded PNRs", "312" if idx >= 2 else "—", "Triage-scored by the Orchestrator"),
      ("Auto-resolved", "1" if idx >= 4 else "0", f"Under {inr(THRESHOLD)}, no human touch"),
      ("Awaiting human", "1" if ss.stage == "await_human" else "0", f"{inr(THRESHOLD)} and above, or SSR / medical"),
      ("Avg handling time", "3 min 27 s" if idx >= 8 else "—", "Illustrative · manual baseline 45-90 min")]
for col, (a, b, s) in zip(st.columns(4), kp):
    col.markdown(kpi(a, b, s), unsafe_allow_html=True)

if idx == 0:
    md('<div class="card"><div class="amber">Scenario</div>It is 06:00 IST and dense fog has closed Delhi airport. '
       'Hundreds of passengers are stranded and the call centre is about to collapse. '
       'Trigger the disruption to watch AeroRecover recover two passengers: one automatically, one with human approval.</div>')
    st.button("🌫️ Trigger Fog Disruption at DEL", key="trigger", on_click=go, args=("orch_run",))
else:
    md('<div class="banner">🌫️ ACTIVE DISRUPTION · Dense fog at DEL (VIDP) · CAT-III suspended · 47 departures affected</div>')

# ---- 1. Orchestrator
if idx >= 1:
    md('<div class="sec">1 · Orchestrator Agent: detect and triage</div>')
    if ss.stage == "orch_run":
        stream("Orchestrator Agent", ORCH)
        go("p1_run")
        st.rerun()
    else:
        rows = "".join(
            f'<div class="opt"><b>#{i}</b><span class="fl"><b>{n}</b> · {pnr} · {rt}</span>Priority <b>{sc}</b>'
            f'<span class="chip {"g" if i <= 2 else ""}">{"Traced below" if i <= 2 else "Parallel batch"}</span></div>'
            for i, (pnr, n, rt, sc) in enumerate(QUEUE, 1))
        md(f'<div class="card"><div class="amber">Prioritised recovery queue · top 5 of 312</div>{rows}</div>')
        with st.expander("🧠 Agent Thinking Process: Orchestrator", expanded=False):
            md(log_html(ORCH))

# ---- 2 and 3. Passengers
if idx >= 2:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        md('<div class="sec">2 · Passenger 1: auto-execution</div>')
        md(pax_card(r1))
        
        if ss.stage == "p1_run":
            stream("Rebooking · Fare · Care agents", thinking_log(r1))
            go("p1_wait_reply")
            st.rerun()
            
        elif ss.stage == "p1_wait_reply":
            with st.expander("🧠 Agent Thinking Process: Passenger 1", expanded=False):
                md(log_html(thinking_log(r1)))
            md(options_html(r1))
            md(f'<div class="ok">✅ AUTO-EXECUTED · fare difference {inr(r1["diff"])} is below {inr(THRESHOLD)} · sending options</div>')
            o = r1["o"]
            md(wa_html([("in", f"Hi {P1['first']} 👋 Your flight {P1['orig'].split(' · ')[0]} ({P1['route']}) is cancelled due to dense fog at Delhi.<br><br>Please reply with a number:<br><b>1.</b> Rebook on {o['flight']} ({o['dep']}) for {inr(r1['diff'])} diff.<br><b>2.</b> Full DGCA Refund ({inr(P1['orig_fare'])}).<br><b>3.</b> Hotel + Next day flight.", "08:46")]))
            
            st.write("**Simulate Passenger Reply (WhatsApp Concierge):**")
            b1, b2, b3 = st.columns(3)
            if b1.button("Reply: 1", key="reply1", use_container_width=True): ss.p1_choice = "1"; go("p1_choice"); st.rerun()
            if b2.button("Reply: 2", key="reply2", use_container_width=True): ss.p1_choice = "2"; go("p1_choice"); st.rerun()
            if b3.button("Reply: 3", key="reply3", use_container_width=True): ss.p1_choice = "3"; go("p1_choice"); st.rerun()
            
        else:
            with st.expander("🧠 Agent Thinking Process: Passenger 1", expanded=False):
                md(log_html(thinking_log(r1)))
            md(options_html(r1))
            
            o = r1["o"]
            if ss.p1_choice == "1":
                md(f'<div class="ok">✅ TICKET REISSUED · option 1 selected · {inr(r1["diff"])} charged</div>')
                final_msg = f"✅ <b>You’re rebooked</b> on {o['flight']} · {o['dep']} → {o['arr']} (Economy).<br>Fare difference {inr(r1['diff'])} charged to your saved card.<br>🍽️ {inr(500)} meal voucher added. New e-ticket attached."
            elif ss.p1_choice == "2":
                md(f'<div class="ok">✅ REFUND PROCESSED · DGCA full refund elected</div>')
                final_msg = f"✅ <b>Refund Initiated.</b> Your original fare of {inr(P1['orig_fare'])} will be credited to your account within 5-7 business days per DGCA rules."
            else:
                md(f'<div class="ok">✅ HOTEL VOUCHER ISSUED · next day flight assigned</div>')
                final_msg = f"✅ <b>Hotel Booked.</b> We have booked the Airport Marriott for tonight. Your new flight departs tomorrow at 10:00 AM. Voucher attached."

            md(wa_html([("in", f"Hi {P1['first']} 👋 Your flight {P1['orig'].split(' · ')[0]} ({P1['route']}) is cancelled due to dense fog at Delhi.<br><br>Please reply with a number:<br><b>1.</b> Rebook on {o['flight']} ({o['dep']}) for {inr(r1['diff'])} diff.<br><b>2.</b> Full DGCA Refund ({inr(P1['orig_fare'])}).<br><b>3.</b> Hotel + Next day flight.", "08:46"),
                        ("out", f"Reply: {ss.p1_choice}", "08:47"),
                        ("in", final_msg, "08:47")]))

    # Passenger 2 Logic
    if idx >= 4:
        with c2:
            md('<div class="sec">3 · Passenger 2: human escalation</div>')
            md(pax_card(r2))
            o = r2["o"]
            
            # --- THIS IS THE NEW GATE ---
            if ss.stage == "p1_choice":
                st.write("")
                st.write("")
                if st.button("▶ Proceed to Passenger 2", type="primary", use_container_width=True):
                    go("p2_run")
                    st.rerun()
                    
            elif ss.stage == "p2_run":
                stream("Rebooking · Fare · Care agents", thinking_log(r2))
                go("await_human")
                st.rerun()
                
            else:
                with st.expander("🧠 Agent Thinking Process: Passenger 2", expanded=False):
                    md(log_html(thinking_log(r2)))
                md(options_html(r2))
                hold = ("in", f"Hi {P2['first']} 👋 Your flight {P2['orig'].split(' · ')[0]} ({P2['route']}) is cancelled due to dense fog. "
                              f"We found a seat on {o['flight']} ({o['dep']} → {o['arr']}). A fare difference of {inr(r2['diff'])} applies, "
                              "so a specialist is confirming it now. You’ll hear from us in minutes.", "08:49")
                if ss.stage in ("await_human", "approving"):
                    md(f'<div class="warn">⏸ AI PAUSED · fare difference {inr(r2["diff"])} is above {inr(THRESHOLD)} · human approval required</div>')
                    md('<div class="sec" style="margin-top:.4rem">Human Agent Approval Dashboard</div>')
                    md(pack_html(r2))
                    if ss.stage == "await_human":
                        st.button("✅ Approve & Execute", key="approve", on_click=go, args=("approving",))
                    else:
                        stream("Execution agents", approve_log(r2))
                        go("done")
                        st.rerun()
                    md(wa_html([hold]))
                else:
                    with st.expander("📦 Resolution Pack (approved)", expanded=False):
                        md(pack_html(r2))
                    md(f'<div class="ok">✅ APPROVED BY HUMAN AND EXECUTED · {inr(r2["diff"])} fare difference · full audit trail</div>')
                    md(wa_html([hold,
                                ("in", f"✅ <b>Confirmed!</b> You’re on {o['flight']} · {o['dep']} → {o['arr']} (Economy).<br>Fare difference {inr(r2['diff'])} charged.<br>🍽️ {inr(500)} meal voucher added.", "08:52"),
                                ("out", "Perfect, thank you!", "08:52")]))

# ---- 4. Wrap-up
if ss.stage == "done":
    md('<div class="sec">4 · Run summary</div>')
    md('<div class="ok">🏁 2 of 2 traced passengers recovered · Passenger 1 in about 2 min 41 s (fully automatic) · '
       'Passenger 2 in about 4 min 12 s (including the human click) · manual baseline is 45-90 min</div>')
    with st.expander("🔒 Immutable audit ledger", expanded=False):
        md(log_html([("Ledger", f"#{r1['sig']} · {P1['pnr']} · AUTO · {inr(r1['diff'])} · policy v2026.10"),
                     ("Ledger", f"#{r2['sig']} · {P2['pnr']} · HUMAN-APPROVED · {inr(r2['diff'])} · policy v2026.10")]))

st.caption("Illustrative simulation built for the AeroRecover case. All flights, fares and passengers are fictional.")
