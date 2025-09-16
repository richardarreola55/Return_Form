
import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict

st.set_page_config(page_title="Kitted Job Material Return", page_icon="📦", layout="wide")

st.title("📦 Kitted Job Material Return Form")
st.caption("Submit returned materials from a kitted job. Data will POST to your webhook as JSON.")

# Fixed webhook URL (no sidebar input)
webhook_url = "https://luis7fc.app.n8n.cloud/webhook/ffd78965-ead2-47a3-b1e2-b709c559653e"

# Superintendent -> email mapping
SUPER_EMAILS = {
    "Coffee": "mcoffee@citadelrs.com",
    "Ferguson": "bferguson@citadelrs.com",
    "Parada": "iparada@citadelrs.com",
}

# --- Session state for items (use dict-style keys to avoid clashing with .items() method) ---
if "items" not in st.session_state:
    st.session_state["items"] = [
        {"item_code": "", "description": "", "qty": "", "condition": "Unused"}
    ]

def add_item():
    st.session_state["items"].append({"item_code": "", "description": "", "qty": "", "condition": "Unused"})

def remove_item(idx: int):
    if 0 <= idx < len(st.session_state["items"]):
        st.session_state["items"].pop(idx)

# --- Form ---
with st.form("kitted_return_form", clear_on_submit=False):
    st.subheader("1) Job Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        job_number = st.text_input("Job / Work Order Number*", placeholder="WO-123456")
        lot_number = st.text_input("Lot Number", placeholder="Lot-001")
    with col2:
        project_name = st.text_input("Customer / Project Name")
        crew = st.text_input("Crew", placeholder="Crew A / Installer Team 3")
    with col3:
        date_of_return = st.date_input("Date of Return*", value=datetime.now().date())
        original_sched_date = st.date_input("Original Scheduled Date", value=datetime.now().date())

    super_options = ["Coffee", "Ferguson", "Parada"]
    superintendent = st.selectbox("Superintendent", options=super_options, index=0)

    st.markdown("---")
    st.subheader("2) Returned By")
    col4, col5 = st.columns(2)
    with col4:
        employee_name = st.text_input("Employee Name*", placeholder="Jane Doe")
    with col5:
        department = st.selectbox("Department", ["Production", "Assembly", "Field", "Warehouse", "Other"])

    
    st.markdown("---")
    st.subheader("4) Additional Notes")
    reason_for_return = st.text_area("Reason for Return")
    issues_identified = st.text_area("Any Issues Identified")

    st.markdown("---")
    st.subheader("5) Warehouse Acknowledgment (optional - for receiving staff)")
    col7, col8 = st.columns(2)
    with col7:
        received_by = st.text_input("Received By")
    with col8:
        use_processed_date = st.checkbox("Provide Date Processed")
        date_processed = None
        if use_processed_date:
            date_processed = st.date_input("Date Processed", value=datetime.now().date())

    # Submit button (explicit)
    submitted = st.form_submit_button("Submit to Webhook")

# --- Validation & Submit handler ---
def validate_required():
    errors = []
    if not job_number:
        errors.append("Job / Work Order Number is required.")
    if not date_of_return:
        errors.append("Date of Return is required.")
    if not employee_name:
        errors.append("Employee Name is required.")
    # Validate at least one numeric quantity
    valid_qty = False
    for it in st.session_state["items"]:
        q = (it.get("qty") or "").strip()
        if q:
            try:
                float(q)
                valid_qty = True
                break
            except ValueError:
                errors.append(f"Invalid quantity: '{q}'. Use a number.")
    if not valid_qty:
        errors.append("At least one returned item with a numeric quantity is required.")
    if not webhook_url:
        errors.append("Webhook URL is not configured.")
    return errors

if submitted:
    errs = validate_required()
    if errs:
        for e in errs:
            st.error(e)
    else:
        to_email = SUPER_EMAILS.get(superintendent, None)

        payload = {
            "meta": {
                "submitted_at": datetime.utcnow().isoformat() + "Z",
                "app": "Kitted Job Material Return",
                "version": "1.2.0"
            },
            "routing": {
                "superintendent": superintendent,
                "to_email": to_email,
            },
            "job_info": {
                "job_number": job_number,
                "project_name": project_name,
                "lot_number": lot_number,
                "crew": crew,
                "original_scheduled_date": str(original_sched_date) if original_sched_date else None,
                "date_of_return": str(date_of_return),
            },
            "returned_by": {
                "employee_name": employee_name,
                "department": department
            },
            "items": [
                {
                    "item_code": it.get("item_code", "").strip(),
                    "description": it.get("description", "").strip(),
                    "qty": float(it["qty"]) if (it.get("qty") and it.get("qty").strip()) else 0.0,
                    "condition": it.get("condition", "Unused"),
                }
                for it in st.session_state["items"]
                if (it.get("qty") or "").strip()
            ],
            "notes": {
                "reason_for_return": reason_for_return,
                "issues_identified": issues_identified,
            },
            "warehouse_ack": {
                "received_by": received_by,
                "date_processed": str(date_processed) if date_processed else None,
            }
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            ok = 200 <= resp.status_code < 300
            if ok:
                st.success("Submitted successfully to webhook ✅")
                with st.expander("Payload sent (JSON)"):
                    st.code(payload, language="json")
                with st.expander("Webhook response"):
                    try:
                        st.json(resp.json())
                    except Exception:
                        st.text(resp.text)
            else:
                st.error(f"Webhook responded with status {resp.status_code}")
                with st.expander("Response body"):
                    st.text(resp.text)
        except requests.exceptions.RequestException as ex:
            st.error(f"Failed to reach webhook: {ex}")
