import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- CONFIGURATION ---
DB_NAME = "real_estate_advanced.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tables (Users, Properties, Transactions)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, linked_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS properties (flat_id TEXT PRIMARY KEY, building TEXT, owner_name TEXT, tenant_name TEXT, rent REAL, ewa_limit REAL, lease_end TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, flat_id TEXT, month TEXT, rent_paid REAL, ewa_cost REAL, chiller REAL, other_fees REAL, comments TEXT)''')
    
    # Default Admin
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', pw, 'admin'))
    conn.commit()
    conn.close()

# --- ANALYTICS HELPERS ---
def get_trimmed_data(df):
    """Filters dataframe to only show data up to the current month."""
    if df.empty: return df
    df['month_dt'] = pd.to_datetime(df['month'])
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return df[df['month_dt'] <= current_month].sort_values('month_dt', ascending=False)

# --- VIEWS ---

def admin_analytics(conn):
    st.title("📊 Portfolio Executive Analytics")
    
    # KPIs
    df_prop = pd.read_sql_query("SELECT * FROM properties", conn)
    df_trans = get_trimmed_data(pd.read_sql_query("SELECT * FROM transactions", conn))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Properties", len(df_prop))
    col2.metric("Total Revenue", f"{df_trans['rent_paid'].sum():,.0f} BHD")
    col3.metric("Avg Occ. Rate", f"{(df_prop['tenant_name'] != 'Vacant').mean()*100:.1f}%")
    
    # EWA Leakage (Where costs exceed limits)
    merged = df_trans.merge(df_prop[['flat_id', 'ewa_limit']], on='flat_id')
    merged['ewa_total'] = merged['ewa_cost'] + merged['chiller']
    leakage = merged[merged['ewa_total'] > merged['ewa_limit']]
    col4.metric("EWA Alerts", len(leakage), delta_color="inverse")

    st.divider()
    
    # Revenue Growth Chart
    st.subheader("Monthly Revenue vs Utility Expenses")
    monthly_trend = df_trans.groupby('month')[['rent_paid', 'ewa_cost', 'chiller']].sum().reset_index()
    fig = px.line(monthly_trend, x='month', y=['rent_paid', 'ewa_cost', 'chiller'], 
                  title="Portfolio Cashflow Trend", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

def owner_analytics(conn, owner_name):
    st.title(f"📈 Investor Report: {owner_name}")
    
    # Get Data
    df_prop = pd.read_sql_query("SELECT * FROM properties WHERE owner_name=?", conn, params=(owner_name,))
    flat_ids = df_prop['flat_id'].tolist()
    
    if not flat_ids:
        st.warning("No properties found for this owner.")
        return

    placeholders = ','.join(['?'] * len(flat_ids))
    df_trans = get_trimmed_data(pd.read_sql_query(f"SELECT * FROM transactions WHERE flat_id IN ({placeholders})", conn, params=flat_ids))
    
    # Analytics Header
    total_rent = df_trans['rent_paid'].sum()
    total_costs = df_trans['ewa_cost'].sum() + df_trans['chiller'].sum() + df_trans['other_fees'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Gross Income", f"{total_rent:,.2f} BHD")
    c2.metric("Total Expenses", f"{total_costs:,.2f} BHD")
    c3.metric("Net Cashflow", f"{(total_rent - total_costs):,.2f} BHD")

    # Property Performance Comparison
    st.subheader("Income by Property")
    prop_perf = df_trans.groupby('flat_id')['rent_paid'].sum().reset_index()
    fig = px.bar(prop_perf, x='flat_id', y='rent_paid', color='flat_id', title="Revenue per Unit")
    st.plotly_chart(fig, use_container_width=True)

def tenant_analytics(conn, flat_id):
    st.title(f"👤 Tenant Portal | Flat {flat_id}")
    
    prop = conn.execute("SELECT * FROM properties WHERE flat_id=?", (flat_id,)).fetchone()
    df_trans = get_trimmed_data(pd.read_sql_query("SELECT * FROM transactions WHERE flat_id=?", conn, params=(flat_id,)))
    
    # Gauge Chart for EWA Consumption
    latest_ewa = (df_trans.iloc[0]['ewa_cost'] + df_trans.iloc[0]['chiller']) if not df_trans.empty else 0
    limit = prop['ewa_limit']
    
    st.subheader("Latest Utility Consumption vs Limit")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = latest_ewa,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"Current EWA+Chiller (Limit: {limit})"},
        delta = {'reference': limit, 'increasing': {'color': "red"}, 'decreasing': {'color': "green"}},
        gauge = {
            'axis': {'range': [0, limit * 2]},
            'steps': [
                {'range': [0, limit], 'color': "lightgreen"},
                {'range': [limit, limit * 2], 'color': "pink"}],
            'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': limit}}))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Your Billing History")
    st.dataframe(df_trans[['month', 'rent_paid', 'ewa_cost', 'chiller', 'comments']], use_container_width=True)

# --- MAIN APP ---
def main():
    init_db()
    if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        # [Standard Login Code here - see previous response]
        show_login_ui()
    else:
        role = st.session_state['user']['role']
        conn = get_db_connection()
        
        if st.sidebar.button("Logout"):
            st.session_state['logged_in'] = False
            st.rerun()

        if role == 'admin':
            menu = st.sidebar.selectbox("Navigation", ["Analytics Dashboard", "Data Import", "Property List"])
            if menu == "Analytics Dashboard": admin_analytics(conn)
            elif menu == "Data Import": show_import_ui() # (Function from previous code)
            else: show_property_list(conn)
            
        elif role == 'owner':
            owner_analytics(conn, st.session_state['user']['linked_id'])
            
        elif role == 'tenant':
            tenant_analytics(conn, st.session_state['user']['linked_id'])
        
        conn.close()

def show_login_ui():
    st.title("🏠 Real Estate Management System")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            # Check DB (simplified for example)
            conn = get_db_connection()
            hash_p = hashlib.sha256(p.encode()).hexdigest()
            user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (u, hash_p)).fetchone()
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user'] = dict(user)
                st.rerun()
            else: st.error("Invalid credentials")

if __name__ == "__main__":
    main()
