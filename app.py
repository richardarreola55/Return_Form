import streamlit as st
import requests
from datetime import datetime
from typing import List, Dict

st.set_page_config(page_title="Kitted Job Material Return", page_icon="📦", layout="wide")

st.title("📦 Kitted Job Material Return Form")
st.caption("Submit returned materials from a kitted job. Data will POST to your webhook as JSON.")

# --- Sidebar: Webhook configuration ---
with st.sidebar:
    st.header("🔗 Webhook Settings")
    webhook_url = st.text_input("Webhook URL", placeholder="https://your-webhook-endpoint.example.com", help="Paste your n8n / Zapier / Make / custom webhook URL.")
    advanced = st.checkbox("Advanced headers (optional)")
    headers = {}
    if advanced:
        st.write("Add optional headers (e.g., Authorization).")
        # Allow up to 3 custom headers for simplicity
        for i in range(1, 4):
            key = st.text_input(f"Header {i} name", key=f"hdr_key_{i}")
            val = st.text_input(f"Header {i} value", key=f"hdr_val_{i}")
            if key:
                headers[key] = val

# --- Session state for items ---
if "items" not in st.session_state:
    st.session_state.items: List[Dict[str, str]] = [
        {"item_code": "", "description": "", "qty": "", "condition": "Unused"}
    ]

def add_item():
    st.session_state.items.append({"item_code": "", "description": "", "qty": "", "condition": "Unused"})

def remove_item(idx: int):
    if 0 <= idx < len(st.session_state.items):
        st.session_state.items.pop(idx)

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

    # Superintendent dropdown
    super_options = ["Coffee", "Ferguson", "Parada"]
    superintendent = st.selectbox("Superintendent", options=super_options, index=0)

    st.markdown("---")
    st.subheader("2) Returned By")
    col4, col5, col6 = st.columns(3)
    with col4:
        employee_name = st.text_input("Employee Name*", placeholder="Jane Doe")
    with col5:
        department = st.selectbox("Department", ["Production", "Assembly", "Field", "Warehouse", "Other"])
    with col6:
        supervisor = st.text_input("Supervisor")

    st.markdown("---")
    st.subheader("3) Returned Materials")

    # Items table-like editor
    for idx, row in enumerate(st.session_state.items):
        with st.expander(f"Item {idx+1}", expanded=True if idx == 0 else False):
            c1, c2, c3, c4 = st.columns([1.2, 2, 1, 1.2])
            with c1:
                st.session_state.items[idx]["item_code"] = st.text_input("Item Code / Part #", value=row["item_code"], key=f"item_code_{idx}")
            with c2:
                st.session_state.items[idx]["description"] = st.text_input("Description", value=row["description"], key=f"desc_{idx}")
            with c3:
                st.session_state.items[idx]["qty"] = st.text_input("Qty Returned*", value=row["qty"], key=f"qty_{idx}")
            with c4:
                st.session_state.items[idx]["condition"] = st.selectbox("Condition", ["Unused", "Damaged", "Partial"], index=["Unused", "Damaged", "Partial"].index(row["condition"]), key=f"cond_{idx}")
            rem_col, _, _, _ = st.columns(4)
            with rem_col:
                if st.button("Remove Item", key=f"remove_{idx}"):
                    remove_item(idx)
                    st.experimental_rerun()

    st.button("➕ Add another item", on_click=add_item)

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

    submitted = st.form_submit_button("Submit to Webhook")

# --- Submit handler ---
def validate_required():
    errors = []
    if not job_number:
        errors.append("Job / Work Order Number is required.")
    if not date_of_return:
        errors.append("Date of Return is required.")
    if not employee_name:
        errors.append("Employee Name is required.")
    # At least one item with qty
    valid_qty = False
    for it in st.session_state.items:
        q = (it.get("qty") or "").strip()
        if q:
            try:
                # accept ints/floats as text
                float(q)
                valid_qty = True
                break
            except ValueError:
                errors.append(f"Invalid quantity: '{q}'. Use a number.")
    if not valid_qty:
        errors.append("At least one returned item with a numeric quantity is required.")
    if not webhook_url:
        errors.append("Webhook URL is required (see sidebar).")
    return errors

if submitted:
    errs = validate_required()
    if errs:
        for e in errs:
            st.error(e)
    else:
        payload = {
            "meta": {
                "submitted_at": datetime.utcnow().isoformat() + "Z",
                "app": "Kitted Job Material Return",
                "version": "1.1.0"
            },
            "job_info": {
                "job_number": job_number,
                "project_name": project_name,
                "lot_number": lot_number,
                "crew": crew,
                "superintendent": superintendent,
                "original_scheduled_date": str(original_sched_date) if original_sched_date else None,
                "date_of_return": str(date_of_return),
            },
            "returned_by": {
                "employee_name": employee_name,
                "department": department,
                "supervisor": supervisor,
            },
            "items": [
                {
                    "item_code": it.get("item_code", "").strip(),
                    "description": it.get("description", "").strip(),
                    "qty": float(it["qty"]) if (it.get("qty") and it.get("qty").strip()) else 0,
                    "condition": it.get("condition", "Unused"),
                }
                for it in st.session_state.items
                if (it.get("qty") or "").strip()  # include only rows with qty
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
            resp = requests.post(webhook_url, json=payload, headers=headers, timeout=15)
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
