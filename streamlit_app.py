import streamlit as st
import sqlite3
from datetime import datetime
import pytz

DATABASE = 'database.db'





# --- Helper Function: Connect to DB ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize DB Schema ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            drink_type TEXT NOT NULL,
            milk_type TEXT,
            flavors TEXT,
            pickup_time TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- Submit a new order ---
def submit_order(name, drink, milk, flavors, pickup):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (customer_name, drink_type, milk_type, flavors, pickup_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, drink, milk, flavors, pickup))
    conn.commit()
    conn.close()

# --- Get current orders ---
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- Update order status ---
def update_status(order_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    conn.commit()
    conn.close()

# --- Initialize the DB when the app starts ---
init_db()

# --- Streamlit App ---
st.title("☕️ Church Coffee Pre-Orders")

menu = ["Place Order", "View Orders"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Place Order":
    st.header("Place Your Coffee Order")
    with st.form(key="order_form"):
        name = st.text_input("Your Name")
        drink = st.selectbox("Drink", ["Latte", "Drip Coffee", "Tea", "Cappuccino"])
        milk = st.selectbox("Milk Type", ["Whole", "Oat", "Fairlife Milk", "None"])
        flavors = st.selectbox("Flavors", ["Caramel", "Mocha", "Hazelnut", "Seasonal"])
        pickup = st.selectbox("Pickup Time", ["9:30", "9:40", "9:50", "10"])
        submit = st.form_submit_button("Submit Order")
    
    if submit:
        if not name or not drink:
            st.error("Please provide your name and drink.")
        else:
            submit_order(name, drink, milk, flavors, pickup)
            st.success("✅ Your order has been placed!")

elif choice == "View Orders":
    st.header("All Orders")
    orders = get_orders()
    if not orders:
        st.info("No orders yet.")
    else:
        central = pytz.timezone("America/Chicago")

        for row in orders:
            utc_dt = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            utc_dt = pytz.utc.localize(utc_dt)
            central_dt = utc_dt.astimezone(central)
            formatted_time = central_dt.strftime("%Y-%m-%d %I:%M %p %Z")

            st.write(f"**Order ID:** {row['id']}")
            st.write(f"👤 **Name:** {row['customer_name']}")
            st.write(f"☕ **Drink:** {row['drink_type']} with {row['milk_type']} milk")
            st.write(f"🍯 **Flavors:** {row['flavors']}")
            st.write(f"📅 **Placed:** {formatted_time}")
            st.write(f"🔖 **Status:** {row['status']}")

            col1, col2, col3 = st.columns(3)

            if col1.button("Mark In Progress", key=f"progress_{row['id']}"):
                update_status(row['id'], "in_progress")

            if col2.button("Mark Ready", key=f"ready_{row['id']}"):
                update_status(row['id'], "ready")

            if col3.button("Mark Complete", key=f"complete_{row['id']}"):
                update_status(row['id'], "complete")

            st.markdown("---")


