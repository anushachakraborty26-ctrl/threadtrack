"""
app.py — ThreadTrack interactive dashboard (Streamlit).

The web side of Phase 6. One app, four tabs:
  Order book        — every scored purchase order, filterable and colour-coded
  Score a new order — a live form: enter an order, get its risk instantly
  Portfolio view    — the operations roll-up across the whole order book
  How it works      — the model, the key finding, and the Phase 5 validation

The dashboard reads the pre-scored order dataset (data/scored_pos.csv) and, for
live scoring, calls the rule scorer directly (src/rule_scorer.py).

Run locally:   streamlit run app.py
"""

from datetime import date

import pandas as pd
import streamlit as st

from src.config import FESTIVE_MONTHS, REGIONAL_MONSOON_MONTHS, VENDORS
from src.rule_scorer import score_order

ORDERS_CSV = "data/scored_pos.csv"
CITY_TIERS_CSV = "data/city_tiers.csv"
THEME_CHART = "output/validation_review_themes.png"
RATING_CHART = "output/validation_complaint_by_rating.png"

# fill colours for the Low / Medium / High risk bands
BAND_FILL = {"Low": "#C6EFCE", "Medium": "#FFEB9C", "High": "#FFC7CE"}

# vendor lookup — the new-order form derives cluster, new-vendor status and
# reliability from the chosen vendor (single source of truth: src/config.py)
VENDOR_BY_ID = {v["id"]: v for v in VENDORS}
VENDOR_IDS = [v["id"] for v in VENDORS]

# a first-time vendor — chosen via this sentinel, scored as new and unproven
NEW_VENDOR = "+ Add a new vendor"
NEW_VENDOR_RELIABILITY = 0.75   # no track record yet, so treated as below-average


def vendor_label(vendor_id):
    """Drop-down label for a vendor: id, cluster, and a first-cycle flag.

    Looks across both the config roster and any vendors added live this
    session, so a just-added vendor labels correctly in the drop-down.
    """
    roster = {**VENDOR_BY_ID,
              **{v["id"]: v for v in st.session_state.get("new_vendors", [])}}
    v = roster.get(vendor_id)
    if v is None:               # the "add a new vendor" sentinel — show it as-is
        return vendor_id
    flag = " (first-cycle)" if v["is_new"] else ""
    name = v.get("name", "")
    head = f"{name}, {v['cluster']}" if name else v["cluster"]
    return f"{vendor_id} — {head}{flag}"

st.set_page_config(page_title="ThreadTrack", layout="wide")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

@st.cache_data
def load_orders():
    """Load the scored order dataset once, then keep it in cache."""
    df = pd.read_csv(ORDERS_CSV)
    # the saved bands look like "Low (0-35)"; keep just the first word
    df["delay_risk"] = df["delay_band"].str.split().str[0]
    df["return_risk"] = df["return_band"].str.split().str[0]
    return df


@st.cache_data
def load_city_tiers():
    """Load the city -> delivery-tier classification (used by the new-order form)."""
    cities = pd.read_csv(CITY_TIERS_CSV)
    return dict(zip(cities["city"], cities["tier"]))


def band_of(score):
    """Turn a 0-100 score into a risk band — the project's standard thresholds."""
    if score <= 35:
        return "Low"
    if score <= 65:
        return "Medium"
    return "High"


def season_for(order_date, cluster):
    """Derive the supply-chain season from an order date and the vendor cluster.

    The Indian monsoon reaches the apparel clusters on different timelines, so
    the same date can be 'monsoon' for one cluster and 'normal' for another.
    Festive (Sep-Nov) is national and wins any overlap with monsoon.
    """
    month = order_date.month
    if month in FESTIVE_MONTHS:
        return "festive"
    if month in REGIONAL_MONSOON_MONTHS.get(cluster, []):
        return "monsoon"
    return "normal"


def recommended_action(delay_band, return_band):
    """A plain-English next step, driven by the two risk bands."""
    if delay_band == "High" and return_band == "High":
        return ("Escalate — high delay and return risk. Consider an alternate "
                "vendor, build in a lead-time buffer, and check sizing and "
                "payment terms.")
    if delay_band == "High":
        return "High delay risk — add a lead-time buffer or move to a faster cluster."
    if return_band == "High":
        return "High return risk — tighten sizing guidance; consider a prepaid incentive."
    if delay_band == "Medium" or return_band == "Medium":
        return "Moderate risk — keep this order on the watch list."
    return "Low risk — no action needed."


def render_result(result):
    """Display a score_order() result: two scores, two bands, reasons, an action."""
    delay, ret = result["delay_score"], result["return_score"]
    delay_band, return_band = band_of(delay), band_of(ret)

    c1, c2 = st.columns(2)
    c1.metric("Delay score", f"{delay} / 100")
    c2.metric("Return score", f"{ret} / 100")

    c1, c2 = st.columns(2)
    for col, label, band in [(c1, "Delay risk", delay_band),
                             (c2, "Return risk", return_band)]:
        message = f"{label}: {band}"
        if band == "High":
            col.error(message)
        elif band == "Medium":
            col.warning(message)
        else:
            col.success(message)

    st.info("Recommended action: " + recommended_action(delay_band, return_band))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Why — delay**")
        for reason in result["delay_reasons"] or ["No factors beyond the baseline."]:
            st.markdown(f"- {reason}")
    with c2:
        st.markdown("**Why — return**")
        for reason in result["return_reasons"] or ["No factors beyond the baseline."]:
            st.markdown(f"- {reason}")


def order_from_row(row):
    """Build a score_order() input dict from a dataset row."""
    return {
        "vendor_is_new": bool(row["vendor_is_new"]),
        "vendor_cluster": row["vendor_cluster"],
        "vendor_reliability": float(row["vendor_reliability"]),
        "fabric_type": row["fabric_type"],
        "order_qty": int(row["order_qty"]),
        "destination_tier": row["destination_tier"],
        "payment_mode": row["payment_mode"],
        "season": row["season"],
    }


# ----------------------------------------------------------------------------
# Page
# ----------------------------------------------------------------------------

st.title("ThreadTrack")
st.caption("Delay and return risk prediction for D2C menswear supply chains")

try:
    orders = load_orders()
except FileNotFoundError:
    st.error(f"Could not find {ORDERS_CSV}. Run the earlier phases first.")
    st.stop()

city_tier = load_city_tiers()      # {city: tier} — the form derives tier from city
city_list = sorted(city_tier)

tab_book, tab_score, tab_portfolio, tab_about = st.tabs(
    ["Order book", "Score a new order", "Portfolio view", "How it works"])

# Orders scored in the "Score a new order" tab — and any vendors added there —
# are kept for the current browser session so they also appear elsewhere.
st.session_state.setdefault("added", [])
st.session_state.setdefault("new_vendors", [])


# --- Tab 1: Order book ------------------------------------------------------

with tab_book:
    st.subheader("Order book")
    st.write("Every purchase order, scored. Filter and sort to find what you need.")

    f1, f2, f3, f4 = st.columns(4)
    cluster_sel = f1.multiselect("Vendor cluster",
                                 sorted(orders["vendor_cluster"].unique()))
    season_sel = f2.multiselect("Season", sorted(orders["season"].unique()))
    delay_sel = f3.multiselect("Delay risk", ["Low", "Medium", "High"])
    return_sel = f4.multiselect("Return risk", ["Low", "Medium", "High"])

    sort_options = {
        "Delay risk: high to low": ("delay_score", False),
        "Delay risk: low to high": ("delay_score", True),
        "Return risk: high to low": ("return_score", False),
        "Return risk: low to high": ("return_score", True),
        "Order date: newest first": ("po_date", False),
        "Order date: oldest first": ("po_date", True),
    }
    sort_choice = st.selectbox("Sort by", list(sort_options))

    if st.session_state["added"]:
        pool = pd.concat([pd.DataFrame(st.session_state["added"]), orders],
                         ignore_index=True)
    else:
        pool = orders
    view = pool.copy()
    if cluster_sel:
        view = view[view["vendor_cluster"].isin(cluster_sel)]
    if season_sel:
        view = view[view["season"].isin(season_sel)]
    if delay_sel:
        view = view[view["delay_risk"].isin(delay_sel)]
    if return_sel:
        view = view[view["return_risk"].isin(return_sel)]
    sort_col, sort_asc = sort_options[sort_choice]
    view = view.sort_values(sort_col, ascending=sort_asc)

    n_added = len(st.session_state["added"])
    extra = f" ({n_added} added by you this session)" if n_added else ""
    st.write(f"Showing **{len(view):,}** of {len(pool):,} orders{extra}.")

    show_cols = ["po_id", "po_date", "vendor_id", "vendor_cluster", "fabric_type",
                 "order_qty", "destination_tier", "payment_mode", "season",
                 "delay_score", "return_score", "delay_risk", "return_risk"]

    def colour_band(value):
        return f"background-color: {BAND_FILL.get(value, '')}"

    st.dataframe(
        view[show_cols].style.map(colour_band, subset=["delay_risk", "return_risk"]),
        width="stretch", hide_index=True, height=430)

    st.divider()
    st.markdown("**Inspect one order**")
    if len(view) > 0:
        picked = st.selectbox("Choose a PO", view["po_id"].tolist())
        row = view[view["po_id"] == picked].iloc[0]
        render_result(score_order(order_from_row(row)))
    else:
        st.write("No orders match the current filters.")


# --- Tab 2: Score a new order ----------------------------------------------

with tab_score:
    st.subheader("Score a new order")
    st.write("Enter an order you are about to place — score it, then confirm or "
             "discard it. The score is a go / no-go aid, not an automatic booking.")

    # the vendor roster = the 12 from config + any added live this session
    session_vendors = st.session_state["new_vendors"]
    vendor_by_id = {**VENDOR_BY_ID, **{v["id"]: v for v in session_vendors}}
    vendor_ids = VENDOR_IDS + [v["id"] for v in session_vendors]

    # vendor selection sits outside the form so the new-vendor fields can appear live
    vendor_choice = st.selectbox("Vendor", vendor_ids + [NEW_VENDOR],
                                 format_func=vendor_label)
    new_name, new_cluster = "", "Tirupur"
    if vendor_choice == NEW_VENDOR:
        c1, c2 = st.columns(2)
        new_name = c1.text_input("New vendor name (optional)",
                                 placeholder="e.g. Sri Lakshmi Garments")
        new_cluster = c2.selectbox("New vendor — cluster",
                                   ["Tirupur", "Bengaluru", "Ludhiana", "Delhi NCR"])
        st.caption("A first-time vendor is unproven — it automatically carries the "
                   "first-cycle risk and an assumed below-average reliability until it "
                   "builds a delivery track record. Confirming the order registers it "
                   "on your roster for next time.")

    with st.form("new_order"):
        c1, c2, c3 = st.columns(3)
        fabric = c1.selectbox("Fabric", ["knit", "woven"])
        qty = c2.number_input("Order quantity", min_value=1, value=200, step=10)
        city = c3.selectbox("Destination city", city_list)

        c1, c2, _ = st.columns(3)
        payment = c1.selectbox("Payment mode", ["COD", "Prepaid"])
        order_date = c2.date_input("Order date", value=date.today())

        st.caption("Season — normal, monsoon or festive — is derived from the order "
                   "date and the vendor's cluster; you do not set it by hand.")

        submitted = st.form_submit_button("Score this order")

    if submitted:
        if vendor_choice == NEW_VENDOR:
            nums = [int(x[1:]) for x in vendor_ids
                    if x.startswith("V") and x[1:].isdigit()]
            new_id = f"V{max(nums) + 1:02d}" if nums else "V01"
            new_vendor = {
                "id": new_id,
                "name": new_name.strip(),
                "cluster": new_cluster,
                "primary_fabric": fabric,
                "reliability": NEW_VENDOR_RELIABILITY,
                "size": "small",
                "is_new": True,
            }
            v_is_new, v_cluster, v_rel = True, new_cluster, NEW_VENDOR_RELIABILITY
            book_vendor_id = new_id
        else:
            new_vendor = None
            v = vendor_by_id[vendor_choice]
            v_is_new, v_cluster, v_rel = v["is_new"], v["cluster"], v["reliability"]
            book_vendor_id = vendor_choice
        tier = city_tier[city]              # tier comes from the destination city
        season = season_for(order_date, v_cluster)   # season follows date + cluster
        order = {
            "vendor_is_new": v_is_new,
            "vendor_cluster": v_cluster,
            "vendor_reliability": v_rel,
            "fabric_type": fabric,
            "order_qty": int(qty),
            "destination_city": city,
            "destination_tier": tier,
            "payment_mode": payment,
            "season": season,
        }
        # score it, but hold it as "pending" — nothing is booked until confirmed
        st.session_state["pending"] = {
            "order": order,
            "result": score_order(order),
            "place": f"{city} ({tier})",
            "po_date": order_date.strftime("%Y-%m-%d"),
            "vendor_id": book_vendor_id,
            "new_vendor": new_vendor,
        }
        st.session_state.pop("last", None)   # a fresh score clears the old result
        st.rerun()

    # --- the decision step: score shown first, then confirm or discard --------
    if "pending" in st.session_state:
        pending = st.session_state["pending"]
        o = pending["order"]
        st.divider()
        st.markdown(
            f"**Scored order** — {pending['vendor_id']} · {o['fabric_type']} · "
            f"{o['order_qty']:,} pcs · {o['payment_mode']} · {pending['place']} · "
            f"{pending['po_date']}, {o['season']} season")
        render_result(pending["result"])

        st.divider()
        st.markdown("**Place this order?**")
        st.caption("Confirm to add it to the Order book, or discard it. This is the "
                   "go / no-go call the score is meant to support.")
        new_v = pending["new_vendor"]
        if new_v:
            named = f" — {new_v['name']}" if new_v["name"] else ""
            st.caption(f"Confirming also adds **{new_v['id']}{named}** "
                       f"({new_v['cluster']}) to your vendor roster, so you can pick "
                       "it directly next time.")

        c1, c2, _ = st.columns([1, 1, 2])
        confirm = c1.button("Confirm — place the order", type="primary",
                            width="stretch")
        discard = c2.button("Discard", width="stretch")

        if confirm:
            if new_v:
                st.session_state["new_vendors"].append(new_v)
            result = pending["result"]
            po_id = f"NEW-{len(st.session_state['added']) + 1:03d}"
            st.session_state["added"].append({
                "po_id": po_id,
                "po_date": pending["po_date"],
                "vendor_id": pending["vendor_id"],
                **pending["order"],
                "delay_score": result["delay_score"],
                "return_score": result["return_score"],
                "delay_risk": band_of(result["delay_score"]),
                "return_risk": band_of(result["return_score"]),
            })
            vendor_note = ""
            if new_v:
                named = f" — {new_v['name']}" if new_v["name"] else ""
                vendor_note = (f" Vendor {new_v['id']}{named} is now on your "
                               "roster for future orders.")
            st.session_state["last"] = {
                "score": result,
                "po_id": po_id,
                "place": pending["place"],
                "vendor_note": vendor_note,
            }
            st.session_state.pop("pending", None)
            st.rerun()

        if discard:
            st.session_state.pop("pending", None)
            st.rerun()

    elif "last" in st.session_state:
        last = st.session_state["last"]
        st.divider()
        st.success(f"{last['place']} — confirmed and added to the Order book "
                   f"as {last['po_id']}.{last.get('vendor_note', '')}")
        render_result(last["score"])


# --- Tab 3: Portfolio view --------------------------------------------------

with tab_portfolio:
    st.subheader("Portfolio view")
    st.write("The whole order book at a glance — for planning and vendor management.")

    total = len(orders)
    high_delay = int((orders["delay_risk"] == "High").sum())
    high_return = int((orders["return_risk"] == "High").sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Orders", f"{total:,}")
    m2.metric("High delay risk", f"{high_delay / total * 100:.0f}%")
    m3.metric("High return risk", f"{high_return / total * 100:.0f}%")
    m4.metric("Avg delay / return",
              f"{orders['delay_score'].mean():.0f} / {orders['return_score'].mean():.0f}")

    st.divider()
    order = ["Low", "Medium", "High"]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Orders by delay risk**")
        st.bar_chart(orders["delay_risk"].value_counts().reindex(order).fillna(0))
    with c2:
        st.markdown("**Orders by return risk**")
        st.bar_chart(orders["return_risk"].value_counts().reindex(order).fillna(0))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Average delay score by vendor cluster**")
        st.bar_chart(orders.groupby("vendor_cluster")["delay_score"].mean())
    with c2:
        st.markdown("**Average return score by season**")
        st.bar_chart(orders.groupby("season")["return_score"].mean())


# --- Tab 4: How it works ----------------------------------------------------

with tab_about:
    st.subheader("How it works")
    st.markdown(
        "ThreadTrack scores every purchase order for two risks — **delay** and "
        "**return** — using two methods that cover each other's weaknesses:")
    st.markdown(
        "- **A rule-based scorer** — 15 transparent, hand-weighted supply chain "
        "factors. Every score can be explained, line by line.\n"
        "- **A machine learning model** — an XGBoost classifier that learns "
        "patterns from thousands of past orders.\n"
        "- **A performance-weighted hybrid** blends the two and flags the orders "
        "where they disagree for a human to review.")

    st.divider()
    st.markdown("### The key finding — delays are predictable, returns are not")
    st.markdown(
        "The delay model scores an AUC of **0.855** (strong); the return model "
        "scores **0.578** (weak). This is not a flaw — it is the finding. A delay "
        "is caused by order-time factors the model can see. A return is caused by "
        "post-purchase factors — does it fit, is the quality right — that do not "
        "yet exist when the order is placed.")

    st.divider()
    st.markdown("### Validation — checked against real customers")
    st.markdown(
        "1,189 real Snitch customer reviews were classified into supply chain "
        "themes and held up against the model. Two independent sources — a "
        "benchmark-calibrated model and the unfiltered voice of real customers — "
        "point at the same problems. Independent agreement like that is the "
        "opposite of circular reasoning.")
    c1, c2 = st.columns(2)
    with c1:
        st.image(THEME_CHART, width="stretch")
    with c2:
        st.image(RATING_CHART, width="stretch")
