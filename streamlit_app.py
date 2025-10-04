"""
Dropshipping Product Review Dashboard
Review, approve, and export products to Shopify
"""

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import datetime

# Page config
st.set_page_config(
    page_title="Product Review Dashboard",
    page_icon="🛍️",
    layout="wide"
)

# Google Sheets setup
@st.cache_resource
def get_sheets_service():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    return build('sheets', 'v4', credentials=credentials)

def load_products():
    """Load products from Google Sheets"""
    try:
        service = get_sheets_service()
        sheet_id = st.secrets["PRODUCT_SHEET_ID"]
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Products!A2:P1000'  # Skip header row
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            return pd.DataFrame()
        
        # Create DataFrame
        columns = [
            'date_added', 'product_name', 'category', 'country',
            'overall_score', 'demand_score', 'competition_score',
            'margin_score', 'legal_risk_score', 'price', 'supplier_link',
            'image_url', 'description', 'reasoning', 'status', 'notes'
        ]
        
        df = pd.DataFrame(values, columns=columns)
        
        # Convert score columns to numeric
        score_cols = ['overall_score', 'demand_score', 'competition_score', 
                     'margin_score', 'legal_risk_score']
        for col in score_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading products: {e}")
        return pd.DataFrame()

def update_product_status(row_number, new_status, notes=""):
    """Update product status in Google Sheets"""
    try:
        service = get_sheets_service()
        sheet_id = st.secrets["PRODUCT_SHEET_ID"]
        
        # Update status column (O) and notes column (P)
        row_num = row_number + 2  # +2 because: 1 for header, 1 for 0-based index
        
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f'Products!O{row_num}:P{row_num}',
            valueInputOption='RAW',
            body={'values': [[new_status, notes]]}
        ).execute()
        
        return True
        
    except Exception as e:
        st.error(f"Error updating status: {e}")
        return False

def export_to_shopify_csv(df):
    """Export approved products to Shopify CSV format"""
    shopify_df = pd.DataFrame({
        'Handle': df['product_name'].str.lower().str.replace(' ', '-'),
        'Title': df['product_name'],
        'Body (HTML)': df['description'],
        'Vendor': 'Dropship',
        'Type': df['category'],
        'Tags': df.apply(lambda x: f"{x['category']}, {x['country']}, Score-{x['overall_score']}", axis=1),
        'Published': 'TRUE',
        'Option1 Name': 'Title',
        'Option1 Value': 'Default Title',
        'Variant Price': df['price'].str.replace('$', '').str.replace('N/A', '0'),
        'Variant Inventory Tracker': 'shopify',
        'Variant Inventory Policy': 'deny',
        'Variant Fulfillment Service': 'manual',
        'Variant Requires Shipping': 'TRUE',
        'Image Src': df['image_url'],
        'Status': 'draft'
    })
    
    return shopify_df.to_csv(index=False)

# Dashboard UI
st.title("🛍️ Dropshipping Product Review Dashboard")
st.markdown("Review AI-scored products and approve them for your Shopify store")

# Sidebar filters
st.sidebar.header("Filters")

# Load data
df = load_products()

if df.empty:
    st.warning("No products found. Run the automation first to collect products.")
    st.stop()

# Filter by status
status_filter = st.sidebar.multiselect(
    "Status",
    options=['pending', 'approved', 'rejected'],
    default=['pending']
)

# Filter by country
countries = df['country'].unique().tolist()
country_filter = st.sidebar.multiselect(
    "Country",
    options=countries,
    default=countries
)

# Filter by category
categories = df['category'].unique().tolist()
category_filter = st.sidebar.multiselect(
    "Category",
    options=categories,
    default=categories
)

# Score filter
min_score = st.sidebar.slider(
    "Minimum Overall Score",
    min_value=0,
    max_value=100,
    value=50
)

# Apply filters
filtered_df = df[
    (df['status'].isin(status_filter)) &
    (df['country'].isin(country_filter)) &
    (df['category'].isin(category_filter)) &
    (df['overall_score'] >= min_score)
].copy()

# Sort by score
filtered_df = filtered_df.sort_values('overall_score', ascending=False)

# Stats
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Products", len(df))
with col2:
    st.metric("Pending Review", len(df[df['status'] == 'pending']))
with col3:
    st.metric("Approved", len(df[df['status'] == 'approved']))
with col4:
    avg_score = df['overall_score'].mean()
    st.metric("Avg Score", f"{avg_score:.0f}/100")

st.markdown("---")

# Export approved products
if len(df[df['status'] == 'approved']) > 0:
    st.subheader("📤 Export Approved Products")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"{len(df[df['status'] == 'approved'])} products ready to export")
    with col2:
        approved_df = df[df['status'] == 'approved']
        csv = export_to_shopify_csv(approved_df)
        st.download_button(
            label="Download Shopify CSV",
            data=csv,
            file_name=f"shopify_products_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    st.markdown("---")

# Display products
st.subheader(f"📦 Products ({len(filtered_df)} found)")

if len(filtered_df) == 0:
    st.info("No products match your filters. Try adjusting the filters in the sidebar.")
else:
    for idx, row in filtered_df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                # Display image or placeholder
                if row['image_url'] and row['image_url'] != '':
                    st.image(row['image_url'], width=150)
                else:
                    st.write("📦")
            
            with col2:
                st.markdown(f"### {row['product_name']}")
                st.markdown(f"**Category:** {row['category']} | **Country:** {row['country']} | **Price:** {row['price']}")
                
                # Score badges
                score_col1, score_col2, score_col3, score_col4, score_col5 = st.columns(5)
                with score_col1:
                    color = "🟢" if row['overall_score'] >= 70 else "🟡" if row['overall_score'] >= 50 else "🔴"
                    st.metric("Overall", f"{row['overall_score']}/100", delta=color)
                with score_col2:
                    st.metric("Demand", f"{row['demand_score']}/100")
                with score_col3:
                    st.metric("Competition", f"{row['competition_score']}/100")
                with score_col4:
                    st.metric("Margin", f"{row['margin_score']}/100")
                with score_col5:
                    risk_color = "🟢" if row['legal_risk_score'] <= 30 else "🟡" if row['legal_risk_score'] <= 60 else "🔴"
                    st.metric("Legal Risk", f"{row['legal_risk_score']}/100", delta=risk_color)
                
                # Description and reasoning
                with st.expander("View Details"):
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**AI Reasoning:** {row['reasoning']}")
                    if row['supplier_link']:
                        st.markdown(f"**Supplier Link:** [{row['supplier_link']}]({row['supplier_link']})")
                    st.markdown(f"**Date Added:** {row['date_added']}")
                    if row['notes']:
                        st.markdown(f"**Notes:** {row['notes']}")
            
            with col3:
                st.markdown(f"**Status:** {row['status'].upper()}")
                
                # Action buttons
                if row['status'] == 'pending':
                    if st.button("✅ Approve", key=f"approve_{idx}"):
                        if update_product_status(idx, 'approved'):
                            st.success("Approved!")
                            st.rerun()
                    
                    if st.button("❌ Reject", key=f"reject_{idx}"):
                        if update_product_status(idx, 'rejected'):
                            st.success("Rejected!")
                            st.rerun()
                
                elif row['status'] == 'approved':
                    if st.button("↩️ Revert", key=f"revert_approve_{idx}"):
                        if update_product_status(idx, 'pending'):
                            st.success("Reverted to pending!")
                            st.rerun()
                
                elif row['status'] == 'rejected':
                    if st.button("↩️ Revert", key=f"revert_reject_{idx}"):
                        if update_product_status(idx, 'pending'):
                            st.success("Reverted to pending!")
                            st.rerun()
                
                # Add notes
                notes = st.text_input("Notes", value=row['notes'], key=f"notes_{idx}", label_visibility="collapsed")
                if st.button("💾 Save Note", key=f"save_note_{idx}"):
                    if update_product_status(idx, row['status'], notes):
                        st.success("Note saved!")
                        st.rerun()
            
            st.markdown("---")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("""
This dashboard helps you review AI-scored dropshipping products before adding them to your Shopify store.

**Workflow:**
1. Bot collects products daily
2. AI scores each product
3. You review and approve/reject
4. Export approved products to Shopify
""")
