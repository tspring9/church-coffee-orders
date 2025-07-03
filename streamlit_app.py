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
st.title("☕️ Collective Church Coffee Pre-Orders")

# --- If Volunteer View, require passcode ---
volunteer_authenticated = False



# Read URL parameters
query_params = st.experimental_get_query_params()
mode = query_params.get("mode", ["customer"])[0]

# Initialize volunteer auth state
if "volunteer_authenticated" not in st.session_state:
    st.session_state.volunteer_authenticated = False

# Determine which view
if mode == "volunteer":
    # Prompt for passcode if not authenticated
    if not st.session_state.volunteer_authenticated:
        st.sidebar.write("🔒 **Volunteer Login**")
        passcode = st.sidebar.text_input("Enter passcode:", type="password")
        if passcode == "2021":
            st.session_state.volunteer_authenticated = True
            st.sidebar.success("Volunteer mode enabled!")
    # If authenticated, show volunteer menu
    if st.session_state.volunteer_authenticated:
        menu = ["View Orders", "Customer Display"]
    else:
        menu = []
else:
    # Default: Customer menu
    menu = ["Place Order", "Customer Display"]

# --- Sidebar logo ---
st.sidebar.image("CCO.png", use_column_width=True)
# --- Sidebar menu ---
if menu:
    choice = st.sidebar.radio("Select Page:", menu)
else:
    choice = None

if choice == "Place Order":
    st.header("Place Your Coffee Order")
    with st.form(key="order_form"):
        name = st.text_input("Your Name")
        drink = st.selectbox("Drink", ["Latte", "Cold Brew", "Tea", "Standard Coffee", "De-Caf"])
        milk = st.selectbox("Milk Type", ["Whole", "Oat", "Fairlife", "None"])
        flavors = st.selectbox("Flavors", ["Caramel", "Mocha", "Hazelnut", "Seasonal", "None"])
        pickup = st.selectbox("Pickup Time", ["9:30", "9:40", "9:50", "10"])
        submit = st.form_submit_button("Submit Order")
    
    if submit:
        if not name or not drink:
            st.error("Please provide your name and drink.")
        else:
            submit_order(name, drink, milk, flavors, pickup)
            st.success("✅ Your order has been placed!")

elif choice == "Manage Orders":
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
            st.write(f"📅 **Pickup at:** {row['pickup_time']}")
            st.write(f"🔖 **Status:** {row['status']}")

            if volunteer_authenticated:
                col1, col2, col3 = st.columns(3)

                if col1.button("Mark In Progress", key=f"progress_{row['id']}"):
                    update_status(row['id'], "in_progress")

                if col2.button("Mark Ready", key=f"ready_{row['id']}"):
                    update_status(row['id'], "ready")

                if col3.button("Mark Complete", key=f"complete_{row['id']}"):
                    update_status(row['id'], "complete")
            else:
                st.warning("🔒 You do not have access to manage orders.")

            st.markdown("---")

elif choice == "Order Display":
    st.header("📢 Customer Order Display")

    orders = get_orders()
    if not orders:
        st.info("No orders yet.")
    else:
        # Prepare lists by status
        ordered = []
        preparing = []
        ready = []

        central = pytz.timezone("America/Chicago")

        for row in orders:
            if row['status'] in ("complete", "cancelled"):
                continue  # Skip these

            # Convert timestamp
            utc_dt = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            utc_dt = pytz.utc.localize(utc_dt)
            central_dt = utc_dt.astimezone(central)
            formatted_time = central_dt.strftime("%I:%M %p")

            card = f"**{row['customer_name']}**\n\n☕ {row['drink_type']}\n🕒 {formatted_time}"

            if row['status'] == "pending":
                ordered.append(card)
            elif row['status'] == "in_progress":
                preparing.append(card)
            elif row['status'] == "ready":
                ready.append(card)

        # Display 3 columns
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("📝 Ordered")
            if ordered:
                for o in ordered:
                    st.info(o)
            else:
                st.write("No orders")

        with col2:
            st.subheader("👨‍🍳 Being Prepared")
            if preparing:
                for p in preparing:
                    st.warning(p)
            else:
                st.write("No orders")

        with col3:
            st.subheader("✅ Ready")
            if ready:
                for r in ready:
                    st.success(r)
            else:
                st.write("No orders")
