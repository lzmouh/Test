import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# --- CONFIGURATION & DATABASE SETUP ---
DB_NAME = "real_estate_mgmt.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        role TEXT,
                        linked_id TEXT)''') # linked_id matches Flat Number or Owner Name
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties (
                        flat_id TEXT PRIMARY KEY,
                        building TEXT,
                        owner_name TEXT,
                        tenant_name TEXT,
                        rent REAL,
                        ewa_limit REAL,
                        lease_end DATE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        flat_id TEXT,
                        month DATE,
                        rent_paid REAL,
                        ewa_cost REAL,
                        chiller REAL,
                        other_fees REAL,
                        comments TEXT,
                        FOREIGN KEY(flat_id) REFERENCES properties(flat_id))''')
    
    # Check if empty - Add Demo Data
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        # Create Admin
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       ('admin', pw, 'admin'))
        
        # Create Demo Property/Owner/Tenant
        cursor.execute("INSERT INTO properties VALUES (?, ?, ?, ?, ?, ?, ?)",
                       ('DEMO101', 'Demo Tower', 'Owner_John', 'Tenant_Alice', 500, 20, '2025-12-31'))
        
        # Create Demo Users
        cursor.execute("INSERT INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                       ('owner_john', pw, 'owner', 'Owner_John'))
        cursor.execute("INSERT INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                       ('tenant_alice', pw, 'tenant', 'DEMO101'))
        
    conn.commit()
    conn.close()

# --- EXCEL PROCESSING LOGIC ---
def import_excel_data(uploaded_file):
    xls = pd.ExcelFile(uploaded_file)
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Clear Demo/Existing Data (except Admin)
    cursor.execute("DELETE FROM properties")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM users WHERE role != 'admin'")

    # 2. Process Master Sheet
    master_df = pd.read_excel(xls, 'Master')
    for _, row in master_df.iterrows():
        # Insert Property
        cursor.execute("INSERT OR REPLACE INTO properties VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (str(row['Flat']), row['Building'], row['Owner'], row['Tenant'], 
                        row['Rent'], row['EWA limit'], row['Lease end']))
        
        # Create Owner User
        owner_user = f"owner_{str(row['Owner']).lower().replace(' ', '')}"
        pw = hashlib.sha256("password123".encode()).hexdigest()
        cursor.execute("INSERT OR IGNORE INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                       (owner_user, pw, 'owner', row['Owner']))
        
        # Create Tenant User
        if pd.notna(row['Tenant']):
            tenant_user = f"tenant_{str(row['Flat']).lower()}"
            cursor.execute("INSERT OR IGNORE INTO users (username, password, role, linked_id) VALUES (?, ?, ?, ?)",
                           (tenant_user, pw, 'tenant', str(row['Flat'])))

    # 3. Process Individual Flat Sheets
    for sheet_name in xls.sheet_names:
        if sheet_name == 'Master': continue
        
        # Read sheet, skipping header rows based on your file structure
        df = pd.read_excel(xls, sheet_name, skiprows=2) 
        # Clean columns to match DB
        for _, row in df.iterrows():
            if pd.isna(row['Month']): continue
            cursor.execute('''INSERT INTO transactions (flat_id, month, rent_paid, ewa_cost, chiller, other_fees, comments)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (sheet_name, str(row['Month']), row.get('Rent', 0), row.get('EWA', 0), 
                            row.get('Chiller', 0), row.get('Other fees', 0), row.get('Comments', '')))

    conn.commit()
    conn.close()
    return True

# --- UI COMPONENTS ---
def login():
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, pw_hash)).fetchone()
        conn.close()
        if user:
            st.session_state['logged_in'] = True
            st.session_state['user'] = dict(user)
            st.rerun()
        else:
            st.sidebar.error("Invalid credentials")

def admin_view():
    st.title("Admin Dashboard")
    
    # Upload Section
    with st.expander("⬆️ Upload Master Excel File"):
        file = st.file_uploader("Choose Excel file", type="xlsx")
        if file and st.button("Process & Populate Database"):
            if import_excel_data(file):
                st.success("Database Updated! Demo data removed, Users created.")

    # Manual Entry
    st.subheader("Property Management")
    conn = get_db_connection()
    props = pd.read_sql_query("SELECT * FROM properties", conn)
    st.dataframe(props, use_container_width=True)
    
    if st.button("➕ Add Manual Flat"):
        st.info("Form to add manual entry would go here.")
    conn.close()

def owner_view():
    owner_name = st.session_state['user']['linked_id']
    st.title(f"Owner Portal: {owner_name}")
    
    conn = get_db_connection()
    # Show only their properties
    my_props = pd.read_sql_query("SELECT * FROM properties WHERE owner_name=?", conn, params=(owner_name,))
    st.write("Your Portfolio")
    st.table(my_props)
    
    # Financial Summary
    flat_ids = my_props['flat_id'].tolist()
    if flat_ids:
        placeholders = ','.join(['?'] * len(flat_ids))
        trans = pd.read_sql_query(f"SELECT * FROM transactions WHERE flat_id IN ({placeholders})", conn, params=flat_ids)
        st.subheader("Revenue History")
        st.line_chart(trans.set_index('month')['rent_paid'])
    conn.close()

def tenant_view():
    flat_id = st.session_state['user']['linked_id']
    st.title(f"Tenant Portal: Flat {flat_id}")
    
    conn = get_db_connection()
    # Show lease details
    lease = conn.execute("SELECT * FROM properties WHERE flat_id=?", (flat_id,)).fetchone()
    col1, col2 = st.columns(2)
    col1.metric("Monthly Rent", f"{lease['rent']} BHD")
    col2.metric("EWA Limit", f"{lease['ewa_limit']} BHD")

    # Show transactions and EWA Excess
    trans = pd.read_sql_query("SELECT * FROM transactions WHERE flat_id=?", conn, params=(flat_id,))
    if not trans.empty:
        trans['Total_EWA'] = trans['ewa_cost'] + trans['chiller']
        trans['Excess'] = trans['Total_EWA'] - lease['ewa_limit']
        trans['Excess'] = trans['Excess'].apply(lambda x: x if x > 0 else 0)
        st.subheader("Payment & Utility History")
        st.dataframe(trans[['month', 'rent_paid', 'Total_EWA', 'Excess', 'comments']])
    conn.close()

# --- MAIN APP FLOW ---
def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login()
        st.info("Welcome. Please login to access your property portal.\nDefault Admin: admin / admin123")
    else:
        role = st.session_state['user']['role']
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        if role == 'admin':
            admin_view()
        elif role == 'owner':
            owner_view()
        elif role == 'tenant':
            tenant_view()

if __name__ == "__main__":
    main()
