import streamlit as st
import os
import pandas as pd

TEMPLATE_FOLDER = "templates"

# Ensure the templates folder exists at app startup
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

def get_branch_template(branch_code):
    path = os.path.join(TEMPLATE_FOLDER, f"{branch_code}.xlsx")
    return path if os.path.exists(path) else None

def load_template(branch_code):
    template_path = get_branch_template(branch_code)
    if template_path:
        try:
            df = pd.read_excel(template_path)
            return df
        except Exception as e:
            st.error(f"Failed to load template: {e}")
    return pd.DataFrame(columns=["Item", "Value"])

def save_template(branch_code, df):
    path = os.path.join(TEMPLATE_FOLDER, f"{branch_code}.xlsx")
    df.to_excel(path, index=False)
    st.success("Template saved!")

# UI Starts Here
st.set_page_config(page_title="USS Encoding Project", layout="wide")
st.title("USS Encoding Project")

branches = ["AC", "CHMM", "SMS"]
branch = st.selectbox("Select Branch", branches)

# --- File uploader UI for daily files ---
st.markdown("## Upload Daily Files")
uploaded_files = st.file_uploader(
    "Upload the 4 Required Daily Files",
    type=["xlsx", "csv"],
    accept_multiple_files=True
)

# Check all files uploaded and placeholder for processing logic
if uploaded_files and len(uploaded_files) == 4:
    st.success("All 4 files uploaded successfully!")

    import io
    from logic.extract import extract_data

    # Identify uploaded files by prefix
    file_dict = {f.name: f for f in uploaded_files}
    modifier_file = next((f for name, f in file_dict.items() if name.startswith("modifier-sales-")), None)
    item_file = next((f for name, f in file_dict.items() if name.startswith("item-sales-summary-")), None)
    discount_file = next((f for name, f in file_dict.items() if name.startswith("discounts-")), None)
    payment_file = next((f for name, f in file_dict.items() if name.startswith("payment-type-sales-")), None)

    if not all([modifier_file, item_file, discount_file, payment_file]):
        st.error("Missing one or more required files. Please check file names.")
    else:
        # Call extraction logic
        result = extract_data(modifier_file, item_file, discount_file, payment_file, branch)

        # Load and fill template
        template_df = load_template(branch)
        if not template_df.empty:
            filled_df = template_df.copy()
            filled_df["Value"] = filled_df["Item"].apply(
                lambda x: result.get(str(x).strip().lower(), "")
            )
            st.markdown("### Copy-Paste Output Table")
            st.data_editor(
                filled_df,
                use_container_width=True,
                disabled=["Item", "Value"],
                hide_index=True
            )
        else:
            st.warning("Template for selected branch is empty or could not be loaded.")
else:
    st.warning("Please upload exactly 4 .xlsx files to proceed.")

st.markdown("---")

# Load template
df = load_template(branch)

st.subheader(f"Editing Template for Branch: {branch}")

edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={"Item": "Item Name", "Value": "Default Value"}
)


if st.button("Save Changes"):
    save_template(branch, edited_df)
