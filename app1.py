import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- CONFIGURATION ---
DB_NAME = "real_estate_mgmt.db"

# --- DATABASE ENGINE ---
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        linked_id TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties (
                        flat_id TEXT PRIMARY KEY,
                        building TEXT,
                        owner_name TEXT,
                        tenant_name TEXT,
                        rent REAL,
                        ewa_limit REAL,
                        lease_end TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        flat_id TEXT,
                        month TEXT,
                        rent_paid REAL,
                        ewa_cost REAL,
                        chiller REAL,
                        other_fees REAL,
                        comments TEXT,
                        FOREIGN KEY(flat_id) REFERENCES properties(flat_id))''')
    
    # Create Default Admin if not exists
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       ('admin', admin_pw, 'admin'))
        
        # Insert Demo Data
        cursor.execute("INSERT OR IGNORE INTO properties VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('DEMO101', 'Demo Tower', 'Owner_John', 'Tenant_Alice', 500.0, 20.0, '2025-12-31'))
        
    conn.commit()
    conn.close()

# --- ROBUST EXCEL IMPORTER (ETL) ---
def import_excel_data(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear non-admin data
    cursor.execute("DELETE FROM properties")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM users WHERE role != 'admin'")

    # 1. Process Master Sheet
    master_df = pd.read_excel(xls, 'Master')
    for _, row in master_df.iterrows():
        flat_id = str(row['Flat'])
        owner = str(row['Owner'])
        tenant = str(row['Tenant']) if pd.notna(row['Tenant']) else "Vacant"
        
        # Date Cleaning
        lease_end_dt = pd.to_datetime(row.get('Lease end'), errors='coerce')
        lease_end_str = lease_end_dt.strftime('%Y-%m-%d') if pd.notna(lease_end_dt) else ""

        cursor.execute("INSERT OR REPLACE INTO properties VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (flat_id, row['Building'], owner, tenant, 
                        row['Rent'], row['EWA limit'], lease_end_str))
        
        # Create Users
        default_pw = hashlib.sha256("password123".encode()).hexdigest()
        
        # Owner User
        owner_uname = f"owner_{owner.lower().replace(' ', '_')}"
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                       (owner_uname, default_pw, 'owner', owner))
        
        # Tenant User (Linked to Flat ID)
        if tenant != "Vacant":
            tenant_uname = f"tenant_{flat_id.lower()}"
            cursor.execute("INSERT OR IGNORE INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                           (tenant_uname, default_pw, 'tenant', flat_id))

    # 2. Process Individual Flat Sheets
    for sheet_name in xls.sheet_names:
        if sheet_name == 'Master': continue
        
        # skiprows=2 handles the metadata rows in your specific files
        df = pd.read_excel(xls, sheet_name, skiprows=2) 
        
        for _, row in df.iterrows():
            # ROBUST DATE PARSING: Handles "Balance:" strings by coercing to NaT
            month_dt = pd.to_datetime(row.get('Month'), errors='coerce')
            if pd.isna(month_dt): 
                continue # Skips "Balance:" rows and header duplicates
                
            month_str = month_dt.strftime('%Y-%m-%d')

            def clean_val(val):
                return float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0

            cursor.execute('''INSERT INTO transactions (flat_id, month, rent_paid, ewa_cost, chiller, other_fees, comments)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (str(sheet_name), month_str, 
                            clean_val(row.get('Rent')), clean_val(row.get('EWA')), 
                            clean_val(row.get('Chiller')), clean_val(row.get('Other fees')), 
                            str(row.get('Comments', ''))))

    conn.commit()
    conn.close()
    return True

# --- VIEWS ---
def admin_view():
    st.title("🏢 Real Estate Admin")
    
    # 1. Excel Management
    with st.expander("📊 Database Management"):
        file = st.file_uploader("Upload 'Real Estate Master.xlsx'", type="xlsx")
        if file and st.button("Sync Excel to Database"):
            with st.spinner("Processing..."):
                import_excel_data(file)
            st.success("Database Rebuilt! Demo data replaced with Excel data.")

    # 2. Property Table with Selection
    conn = get_db_connection()
    props_df = pd.read_sql_query("SELECT * FROM properties", conn)
    
    st.subheader("Properties List")
    st.info("💡 Click on a row to view the monthly financial breakdown below.")
    
    # The New Click-to-Select Feature
    selection = st.dataframe(
        props_df, 
        on_select="rerun", 
        selection_mode="single-row",
        use_container_width=True
    )

    # 3. Detailed Inspector
    if selection and len(selection.selection.rows) > 0:
        idx = selection.selection.rows[0]
        selected_flat = props_df.iloc[idx]['flat_id']
        
        st.divider()
        st.subheader(f"🔍 Monthly Analysis: Flat {selected_flat}")
        
        trans_df = pd.read_sql_query(
            "SELECT month, rent_paid, ewa_cost, chiller, other_fees, comments FROM transactions WHERE flat_id = ? ORDER BY month DESC", 
            conn, params=(selected_flat,)
        )
        
        if not trans_df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Income", f"{trans_df['rent_paid'].sum():.2f} BHD")
            c2.metric("Avg EWA", f"{trans_df['ewa_cost'].mean():.2f} BHD")
            c3.metric("Lease End", props_df.iloc[idx]['lease_end'])

            st.line_chart(trans_df.set_index('month')[['rent_paid', 'ewa_cost']])
            st.dataframe(trans_df, use_container_width=True)
        else:
            st.warning("No transaction history found for this unit.")
    
    conn.close()

def owner_view():
    owner_name = st.session_state['user']['linked_id']
    st.title(f"🏠 Owner Portal: {owner_name}")
    conn = get_db_connection()
    
    # View Portfolio
    my_props = pd.read_sql_query("SELECT * FROM properties WHERE owner_name=?", conn, params=(owner_name,))
    st.subheader("Your Properties")
    st.dataframe(my_props, use_container_width=True)
    
    # Financial Aggregation
    flat_ids = my_props['flat_id'].tolist()
    if flat_ids:
        placeholders = ','.join(['?'] * len(flat_ids))
        all_trans = pd.read_sql_query(f"SELECT * FROM transactions WHERE flat_id IN ({placeholders})", conn, params=flat_ids)
        st.subheader("Monthly Performance (Total Portfolio)")
        if not all_trans.empty:
            pivot = all_trans.groupby('month')[['rent_paid', 'ewa_cost']].sum()
            st.area_chart(pivot)
    conn.close()

def tenant_view():
    flat_id = st.session_state['user']['linked_id']
    st.title(f"🔑 Tenant Portal: Flat {flat_id}")
    conn = get_db_connection()
    
    prop = conn.execute("SELECT * FROM properties WHERE flat_id=?", (flat_id,)).fetchone()
    trans = pd.read_sql_query("SELECT * FROM transactions WHERE flat_id=? ORDER BY month DESC", conn, params=(flat_id,))
    
    # EWA Excess Calculation
    col1, col2 = st.columns(2)
    col1.metric("Current Rent", f"{prop['rent']} BHD")
    col2.metric("EWA Limit", f"{prop['ewa_limit']} BHD")

    if not trans.empty:
        trans['Total EWA'] = trans['ewa_cost'] + trans['chiller']
        trans['Excess Due'] = (trans['Total EWA'] - prop['ewa_limit']).clip(lower=0)
        st.subheader("Utility & Payment History")
        st.dataframe(trans[['month', 'rent_paid', 'Total EWA', 'Excess Due', 'comments']], use_container_width=True)
    
    conn.close()

# --- AUTHENTICATION ---
def main():
    st.set_page_config(page_title="Real Estate Pro", layout="wide")
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.sidebar.title("🔐 Login")
        u = st.sidebar.text_input("Username")
        p = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            hash_p = hashlib.sha256(p.encode()).hexdigest()
            conn = get_db_connection()
            user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hash_p)).fetchone()
            conn.close()
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user'] = dict(user)
                st.rerun()
            else:
                st.sidebar.error("Invalid Login")
        st.info("Admin Default: `admin` / `admin123` \n\nExcel Users Default: `username` / `password123` ")
    else:
        # User Sidebar
        st.sidebar.success(f"Logged in as {st.session_state['user']['username']}")
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        # Router
        role = st.session_state['user']['role']
        if role == 'admin': admin_view()
        elif role == 'owner': owner_view()
        elif role == 'tenant': tenant_view()

if __name__ == "__main__":
    main()
