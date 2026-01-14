import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Kitted Job Material Status", page_icon="📦", layout="wide")

st.title("📦 Kitted Job Material Status Form")
st.caption("Report returned materials, no-pickup situations, or rescheduled jobs.")

# Fixed webhook URL
webhook_url = "https://luis7fc.app.n8n.cloud/webhook/ffd78965-ead2-47a3-b1e2-b709c559653e"

# Superintendent → email mapping
SUPER_EMAILS = {
    "Coffee":    "mcoffee@citadelrs.com",
    "Ferguson":  "bferguson@citadelrs.com",
    "Parada":    "iparada@citadelrs.com",
}

# ────────────────────────────────────────────────
#               Main Form
# ────────────────────────────────────────────────
with st.form("kitted_job_status_form", clear_on_submit=False):

    st.subheader("0) Type of Event")
    event_type = st.selectbox(
        "What happened with the kitted materials?",
        options=[
            "Materials Returned (crew brought back)",
            "Not Picked Up (crew never took them)",
            "Rescheduled / Pushed Out"
        ],
        index=0,
        help="This selection changes which dates & wording appear below"
    )

    st.markdown("---")
    st.subheader("1) Job Information")

    col1, col2, col3 = st.columns(3)
    with col1:
        job_number = st.text_input("Job / Work Order Number*", placeholder="WO-123456")
        lot_number = st.text_input("Lot Number", placeholder="Lot-001")
    with col2:
        project_name = st.text_input("Customer / Project Name")
        crew = st.text_input("Crew", placeholder="Crew A / Installer Team 3")
    with col3:
        original_sched_date = st.date_input("Original Scheduled Date*", value=datetime.now().date())

        # Conditional date fields
        if "Returned" in event_type:
            event_date = st.date_input("Date Materials Returned*", value=datetime.now().date())
        elif "Not Picked Up" in event_type:
            event_date = st.date_input("Date Not Picked Up*", value=datetime.now().date())
        else:  # Rescheduled
            event_date = st.date_input("New Scheduled Date*", value=datetime.now().date())

    superintendent = st.selectbox("Superintendent", options=list(SUPER_EMAILS.keys()), index=0)

    st.markdown("---")
    st.subheader("2) Reported By")
    col4, col5 = st.columns(2)
    with col4:
        employee_name = st.text_input("Employee Name*", placeholder="Jane Doe")
    with col5:
        department = st.selectbox("Department", ["Field", "Warehouse", "Other"])

    st.markdown("---")
    st.subheader("3) Details & Notes")

    # Dynamic label for reason
    reason_label = {
        "Materials Returned": "Reason for Return",
        "Not Picked Up": "Reason Not Picked Up / Explanation",
        "Rescheduled / Pushed Out": "Reason for Reschedule / Delay"
    }[event_type.split(" (")[0]]

    reason = st.text_area(reason_label, height=110)

    issues = st.text_area("Any Issues / Additional Comments", height=90)

    st.markdown("---")
    st.subheader("4) Warehouse Acknowledgment (optional – receiving / kitting staff)")
    col7, col8 = st.columns(2)
    with col7:
        received_by = st.text_input("Received / Processed By")
    with col8:
        use_processed_date = st.checkbox("Provide Date Processed")
        date_processed = None
        if use_processed_date:
            date_processed = st.date_input("Date Processed", value=datetime.now().date())

    submitted = st.form_submit_button("Submit", use_container_width=True, type="primary")

# ────────────────────────────────────────────────
#               Validation & Submit
# ────────────────────────────────────────────────
if submitted:
    errors = []
    if not job_number.strip():
        errors.append("Job / Work Order Number is required.")
    if not employee_name.strip():
        errors.append("Employee Name is required.")
    if not original_sched_date:
        errors.append("Original Scheduled Date is required.")
    if not event_date:
        errors.append("Event date is required.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        to_email = SUPER_EMAILS.get(superintendent)

        # Normalize event type for payload & email
        event_map = {
            "Materials Returned": "returned",
            "Not Picked Up": "not_picked_up",
            "Rescheduled / Pushed Out": "rescheduled"
        }
        event_key = event_map[event_type.split(" (")[0]]

        payload = {
            "meta": {
                "submitted_at": datetime.utcnow().isoformat() + "Z",
                "app": "Kitted Job Material Status",
                "version": "1.3.0"
            },
            "routing": {
                "superintendent": superintendent,
                "to_email": to_email,
            },
            "event": {
                "type": event_key,
                "type_readable": event_type,
                "date": str(event_date),
            },
            "job_info": {
                "job_number": job_number.strip(),
                "project_name": project_name.strip(),
                "lot_number": lot_number.strip(),
                "crew": crew.strip(),
                "original_scheduled_date": str(original_sched_date),
            },
            "reported_by": {
                "employee_name": employee_name.strip(),
                "department": department,
            },
            "notes": {
                "reason": reason.strip(),
                "issues": issues.strip(),
            },
            "warehouse_ack": {
                "processed_by": received_by.strip(),
                "date_processed": str(date_processed) if date_processed else None,
            }
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            if 200 <= resp.status_code < 300:
                st.success("Submitted successfully ✅")
                with st.expander("Payload (JSON)"):
                    st.code(payload, language="json")
                with st.expander("Webhook response"):
                    try:
                        st.json(resp.json())
                    except:
                        st.text(resp.text)
            else:
                st.error(f"Webhook error – status {resp.status_code}")
                with st.expander("Response"):
                    st.text(resp.text)
        except requests.exceptions.RequestException as ex:
            st.error(f"Could not reach webhook: {ex}")
