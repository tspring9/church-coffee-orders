import streamlit as st
import sqlite3
from datetime import datetime
import pytz
from math import ceil

DATABASE = 'database.db'





# --- Helper Function: Connect to DB ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Initialize DB Schema for Orders ---
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

# --- Initialize Menu Options (drinks, milks, flavors) ---
def init_menu_options():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,     -- 'drink', 'milk', or 'flavor'
            label TEXT NOT NULL,
            active INTEGER DEFAULT 1    -- 1 = active, 0 = hidden
        )
    ''')
    conn.commit()

    # Seed defaults only if table is empty
    cursor.execute("SELECT COUNT(*) FROM menu_options")
    if cursor.fetchone()[0] == 0:
        default_options = [
            # Drinks
            ("drink", "Latte"), ("drink", "Cold Brew"), ("drink", "Tea"),
            ("drink", "Standard Coffee"), ("drink", "De-Caf"),
            # Milk
            ("milk", "Whole"), ("milk", "Oat"), ("milk", "Fairlife"), ("milk", "None"),
            # Flavors
            ("flavor", "Caramel"), ("flavor", "Mocha"), ("flavor", "Hazelnut"),
            ("flavor", "Seasonal"), ("flavor", "None")
        ]
        cursor.executemany("INSERT INTO menu_options (category, label) VALUES (?, ?)", default_options)
        conn.commit()

    conn.close()

# --- Initialize both tables at app startup ---
init_db()
init_menu_options()

# --- App Menu Choices ---
menu = ["Place Order", "Customer Display", "New Here?", "🔒 Order Management"]

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

# --- Streamlit App ---
st.title("☕️ Collective Church Coffee Pre-Orders")

# --- Sidebar logo ---
st.sidebar.image("CCO.png", use_container_width=True)
# --- Sidebar menu ---
choice = st.sidebar.radio("Select Page:", menu)

if choice == "Place Order":
    st.header("Place Your Coffee Order")

    from datetime import datetime
    import pytz

    # Get current CST time
    central = pytz.timezone("America/Chicago")
    now = datetime.now(central)

    # Optional: for testing only
    # now = central.localize(datetime(now.year, now.month, now.day, 8, 1))  # Simulated 8:01 AM

    # Show current time
    st.info(f"🕒 Current time (CST): {now.strftime('%I:%M %p')}")

    # Define all slots
    time_slots = ["ASAP", "8:00", "8:10", "8:20", "8:30", "8:40", "8:50", "9:00", "9:10", "9:20", "9:30", "9:40", "9:50", "10:00"]

    # Filter out past slots
    filtered_slots = []
    for t in time_slots:
        if t == "ASAP":
            filtered_slots.append(t)
        else:
            try:
                slot_dt = central.localize(datetime.strptime(t, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                ))
                if slot_dt >= now:
                    filtered_slots.append(t)
            except ValueError:
                st.warning(f"⚠️ Invalid time format: {t}")


    # Order Form
    with st.form(key="order_form"):
        name = st.text_input("Your Name")
        drink = st.selectbox("Drink", ["Latte", "Cold Brew", "Tea", "Standard Coffee", "De-Caf"])
        milk = st.selectbox("Milk Type", ["Whole", "Oat", "Fairlife", "None"])
        flavors = st.selectbox("Flavors", ["Caramel", "Mocha", "Hazelnut", "Seasonal", "None"])
        pickup = st.selectbox("Pickup Time", filtered_slots)
        submit = st.form_submit_button("Submit Order")

    if submit:
        if not name or not drink:
            st.error("Please provide your name and drink.")
        else:
            submit_order(name, drink, milk, flavors, pickup)
            st.success("✅ Your order has been placed!")

elif choice == "🔒 Order Management":
    st.header("Order Management")

    # Sub-tabs for Manage Orders, Reports, Inventory
    subtab = st.radio(
        "Select View:",
        ["Manage Orders", "Reports", "Inventory"],
        horizontal=True
    )

    # ---- Manage Orders sub-tab ----
    if subtab == "Manage Orders":
        if "volunteer_authenticated" not in st.session_state:
            st.session_state.volunteer_authenticated = False

        if not st.session_state.volunteer_authenticated:
            passcode = st.text_input("Enter passcode to manage orders", type="password")
            if passcode == "2021":
                st.session_state.volunteer_authenticated = True
                st.rerun()
            else:
                st.warning("Please enter the correct passcode to access management tools.")
        else:
            orders = get_orders()
            if not orders:
                st.info("No orders yet.")
            else:
                central = pytz.timezone("America/Chicago")
                for row in orders:
                    utc_dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
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

                    col1, col2, col3 = st.columns(3)
                    if col1.button("Mark In Progress", key=f"progress_{row['id']}"):
                        update_status(row['id'], "in_progress")
                        st.rerun()
                    if col2.button("Mark Ready", key=f"ready_{row['id']}"):
                        update_status(row['id'], "ready")
                        st.rerun()
                    if col3.button("Mark Complete", key=f"complete_{row['id']}"):
                        update_status(row['id'], "complete")
                        st.rerun()
                    st.markdown("---")



    # ---- Reports sub-tab ----
    elif subtab == "Reports":
        if not st.session_state.volunteer_authenticated:
            st.warning("Please enter the passcode in 'Manage Orders' to access reports.")
        else:
            st.subheader("📊 Full Order Export")

            orders = get_orders()
            if not orders:
                st.info("No orders yet.")
            else:
                import pandas as pd
                df = pd.DataFrame([dict(row) for row in orders])

                st.dataframe(df)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download All Orders as CSV",
                    csv,
                    "all_orders.csv",
                    "text/csv",
                    key="download-csv"
                )

    # ---- Inventory sub-tab ----
    elif subtab == "Inventory":
        if not st.session_state.volunteer_authenticated:
            st.warning("Please enter the passcode in 'Manage Orders' to access inventory.")
        else:
            st.subheader("📦 Inventory Summary")

            orders = get_orders()
            if not orders:
                st.info("No orders yet.")
            else:
                import collections

                drinks = collections.Counter()
                milks = collections.Counter()
                flavors = collections.Counter()

                for row in orders:
                    if row["status"] in ("complete", "ready", "in_progress", "pending"):
                        drinks[row["drink_type"]] += 1
                        milks[row["milk_type"]] += 1
                        flavors[row["flavors"]] += 1

                st.write("### ☕ Drinks")
                for k, v in drinks.items():
                    st.write(f"- {k}: {v}")

                st.write("### 🥛 Milk Types")
                for k, v in milks.items():
                    st.write(f"- {k}: {v}")

                st.write("### 🍯 Flavors")
                for k, v in flavors.items():
                    st.write(f"- {k}: {v}")


elif choice == "Customer Display":
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
                
elif choice == "New Here?":
    st.header("👋 Welcome to Collective Church!")
    st.write(
        "We're so glad you're here. Check out the resources below to learn more about our community:"
    )

    st.link_button("🙌 I'm New at Collective", "https://www.collectiveomaha.com/im-new")
    st.link_button("🎥 Watch Services Online", "https://www.collectiveomaha.com/watch")

    st.success("Feel free to grab a coffee and make yourself at home! ☕️")

