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

    # Orders table
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

    # 🔹 Add drizzle_type column if it doesn't exist yet
    cursor.execute("PRAGMA table_info(orders)")
    cols = [row[1] for row in cursor.fetchall()]
    if "drizzle_type" not in cols:
        cursor.execute("ALTER TABLE orders ADD COLUMN drizzle_type TEXT")

    conn.commit()
    conn.close()

def init_menu_options():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1) Ensure table exists with correct base columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            label TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            UNIQUE(category, label)
        )
    ''')
    conn.commit()

    # 2) Safety: ensure sort_order column exists (old DB compatibility)
    cursor.execute("PRAGMA table_info(menu_options)")
    cols = [row[1] for row in cursor.fetchall()]
    if "sort_order" not in cols:
        cursor.execute("ALTER TABLE menu_options ADD COLUMN sort_order INTEGER DEFAULT 0")
        conn.commit()

    # 2b) Add espresso/cold brew targeting columns (old DB compatibility)
    cursor.execute("PRAGMA table_info(menu_options)")
    cols = [row[1] for row in cursor.fetchall()]
    
    if "espresso_enabled" not in cols:
        cursor.execute("ALTER TABLE menu_options ADD COLUMN espresso_enabled INTEGER DEFAULT 1")
        conn.commit()
    
    if "cold_brew_enabled" not in cols:
        cursor.execute("ALTER TABLE menu_options ADD COLUMN cold_brew_enabled INTEGER DEFAULT 1")
        conn.commit()
    
    # Optional safety: ensure existing flavor rows get defaults if nulls exist
    cursor.execute("""
        UPDATE menu_options
        SET espresso_enabled = COALESCE(espresso_enabled, 1),
            cold_brew_enabled = COALESCE(cold_brew_enabled, 1)
        WHERE category = 'flavor'
    """)
    conn.commit()


    # 3) Seed defaults only if table is empty
    cursor.execute("SELECT COUNT(*) FROM menu_options")
    if cursor.fetchone()[0] == 0:
        default_options = [
            # Drinks
            ("drink", "Please select a drink", 0),
            ("drink", "Latte", 1),
            ("drink", "Macchiato", 2),
            ("drink", "Cold Brew", 3),
            ("drink", "Americano", 4),

            # Milk
            ("milk", "Please select a milk option", 0),
            ("milk", "1%", 1),
            ("milk", "Almond", 2),
            ("milk", "Fairlife", 3),
            ("milk", "None", 99),

            # Flavors (syrups)
            ("flavor", "Please select a flavor", 0),
            ("flavor", "Vanilla", 1),
            ("flavor", "Hazelnut", 2),
            ("flavor", "Mocha", 3),
            ("flavor", "None", 99),

            # Drizzles
            ("drizzle", "Please select a drizzle", 0),
            ("drizzle", "Chocolate Drizzle", 1),
            ("drizzle", "Caramel Drizzle", 2),
            ("drizzle", "None", 99),
        ]

        cursor.executemany(
            "INSERT OR IGNORE INTO menu_options (category, label, sort_order) VALUES (?, ?, ?)",
            default_options
        )
        conn.commit()

    conn.close()



# --- Initialize both tables at app startup ---
init_db()
init_menu_options()

# --- App Menu Choices ---
menu = ["Place Order", "Customer Display", "New Here?", "🔒 Order Management"]

if "page" not in st.session_state:
    st.session_state.page = "Place Order"

st.sidebar.radio(
    "Select Page:",
    menu,
    key="page"   # <-- this binds the widget to st.session_state.page automatically
)

choice = st.session_state.page


# --- Submit a new order ---
def submit_order(name, drink, milk, flavors, drizzle):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (customer_name, drink_type, milk_type, flavors, drizzle_type, pickup_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, drink, milk, flavors, drizzle, "ASAP"))
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
    
def get_active_menu_items(category, drink_type=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Only flavors are drink-dependent
    if category == "flavor" and drink_type:
        drink_key = (drink_type or "").strip().lower()
        if drink_key == "cold brew":
            cursor.execute("""
                SELECT label
                FROM menu_options
                WHERE category = 'flavor'
                  AND active = 1
                  AND cold_brew_enabled = 1
                ORDER BY sort_order ASC
            """)
        else:
            # Espresso-based drinks: Latte, Macchiato, Americano, etc.
            cursor.execute("""
                SELECT label
                FROM menu_options
                WHERE category = 'flavor'
                  AND active = 1
                  AND espresso_enabled = 1
                ORDER BY sort_order ASC
            """)
    else:
        cursor.execute("""
            SELECT label
            FROM menu_options
            WHERE category = ?
              AND active = 1
            ORDER BY sort_order ASC
        """, (category,))

    rows = cursor.fetchall()
    conn.close()
    return [row["label"] for row in rows]


# --- Streamlit App ---
st.title("☕️ Collective Church Coffee Pre-Orders")

# --- Sidebar logo ---
st.sidebar.image("CCO.png", use_container_width=True)
# --- App Menu Choices ---
menu = ["Place Order", "Customer Display", "New Here?", "🔒 Order Management"]

choice = st.session_state.page


if choice == "Place Order":
    st.header("Place Your Coffee Order")

    central = pytz.timezone("America/Chicago")
    now = datetime.now(central)
    st.info(f"🕒 Current time (CST): {now.strftime('%I:%M %p')}")

    # ✅ Drink selection OUTSIDE the form so flavor list updates immediately
    drink = st.selectbox("Drink", get_active_menu_items("drink"), key="drink_choice")

    with st.form(key="order_form"):
        name = st.text_input("Your Name")

        milk = st.selectbox("Milk Type", get_active_menu_items("milk"))
        flavors = st.selectbox(
            "Flavor (syrup)",
            get_active_menu_items("flavor", drink_type=drink),
        )
        drizzle = st.selectbox("Drizzle (topping)", get_active_menu_items("drizzle"))

        submit = st.form_submit_button("Submit Order")

    if submit:
        if not name.strip():
            st.error("Please provide your name.")
        elif drink.startswith("Please") or milk.startswith("Please"):
            st.error("Please select a drink and milk type before submitting.")
        else:
            submit_order(name, drink, milk, flavors, drizzle)

            st.session_state.page = "Customer Display"
            st.rerun()




    # Sub-tabs for Manage Orders, Reports, Inventory, Menu Settings

elif choice == "🔒 Order Management":
    st.header("Order Management")

    # Sub-tabs for Manage Orders, Reports, Inventory, Menu Settings
    subtab = st.radio(
        "Select View:",
        ["Manage Orders", "Reports", "Inventory", "Menu Settings"],
        horizontal=True
    )

    # ---- Manage Orders sub-tab ----
    if subtab == "Manage Orders":
        if "volunteer_authenticated" not in st.session_state:
            st.session_state.volunteer_authenticated = False
    
        # ✅ Track whether completed orders are visible
        if "show_completed_orders" not in st.session_state:
            st.session_state.show_completed_orders = False
    
        # -------------------------
        # 1) Login gate
        # -------------------------
        if not st.session_state.volunteer_authenticated:
            passcode = st.text_input("Enter passcode to manage orders", type="password")
            if passcode == "2021":
                st.session_state.volunteer_authenticated = True
                st.rerun()
            else:
                st.warning("Please enter the correct passcode to access management tools.")
    
        # -------------------------
        # 2) Authenticated view
        # -------------------------
        else:
            # ✅ Hide/Unhide completed orders button
            btn_label = (
                "Unhide completed orders"
                if not st.session_state.show_completed_orders
                else "Hide completed orders"
            )
            if st.button(btn_label):
                st.session_state.show_completed_orders = not st.session_state.show_completed_orders
                st.rerun()
    
            orders = get_orders()
    
            # ✅ Filter out completed/cancelled unless toggled on
            if not st.session_state.show_completed_orders:
                orders = [o for o in orders if o["status"] not in ("complete", "cancelled")]
    
            if not orders:
                if st.session_state.show_completed_orders:
                    st.info("No orders yet.")
                else:
                    st.info("No active orders (completed orders are hidden).")
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
                    st.write(f"🍫 **Drizzle:** {row['drizzle_type']}")
                    st.write(f"📅 **Placed:** {formatted_time}")
                    st.write(f"🔖 **Status:** {row['status']}")
    
                    col1, col2, col3 = st.columns(3)
                    if col1.button("Mark In Progress", key=f"progress_{row['id']}"):
                        update_status(row["id"], "in_progress")
                        st.rerun()
                    if col2.button("Mark Ready", key=f"ready_{row['id']}"):
                        update_status(row["id"], "ready")
                        st.rerun()
                    if col3.button("Mark Complete", key=f"complete_{row['id']}"):
                        update_status(row["id"], "complete")
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
            st.subheader("📦 Inventory / Usage Overview")

            orders = get_orders()
            if not orders:
                st.info("No orders yet.")
            else:
                import pandas as pd
                df = pd.DataFrame([dict(row) for row in orders])

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### ☕ Drinks Used")
                    drink_summary = (
                        df.groupby("drink_type")
                          .size()
                          .reset_index(name="Total Orders")
                          .sort_values("Total Orders", ascending=False)
                    )
                    st.dataframe(drink_summary, use_container_width=True)

                    st.markdown("### 🥛 Milk Types Used")
                    milk_summary = (
                        df.groupby("milk_type")
                          .size()
                          .reset_index(name="Total Uses")
                          .sort_values("Total Uses", ascending=False)
                    )
                    st.dataframe(milk_summary, use_container_width=True)

                with col2:
                    st.markdown("### 🍯 Flavors (Syrups) Used")
                    flavor_summary = (
                        df.groupby("flavors")
                          .size()
                          .reset_index(name="Total Uses")
                          .sort_values("Total Uses", ascending=False)
                    )
                    st.dataframe(flavor_summary, use_container_width=True)

                    st.markdown("### 🍫 Drizzles Used")
                    drizzle_summary = (
                        df.groupby("drizzle_type")
                          .size()
                          .reset_index(name="Total Uses")
                          .sort_values("Total Uses", ascending=False)
                    )
                    st.dataframe(drizzle_summary, use_container_width=True)

    # ---- Menu Settings sub-tab ----
    elif subtab == "Menu Settings":
        if not st.session_state.volunteer_authenticated:
            st.warning("Please enter the passcode in 'Manage Orders' to access menu settings.")
        else:
            tab_choice = st.radio(
                "What would you like to manage?",
                ["Menu Items"],
                horizontal=True
            )
    
            # =========================
            # MENU ITEMS
            # =========================
            if tab_choice == "Menu Items":
                st.subheader("🧾 Menu Editor")
    
                # --- Add New Item ---
                st.markdown("### ➕ Add a New Menu Item")
                with st.form(key="add_menu_item_form"):
                    new_label = st.text_input("Item Name")
                    new_category = st.selectbox("Category", ["drink", "milk", "flavor", "drizzle"])
                    add_item = st.form_submit_button("Add to Menu")
    
                    if add_item:
                        if not new_label.strip():
                            st.error("Item name cannot be empty.")
                        else:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            try:
                                # append to bottom of category
                                cur.execute(
                                    "SELECT COALESCE(MAX(sort_order), 0) FROM menu_options WHERE category = ?",
                                    (new_category,),
                                )
                                max_sort = cur.fetchone()[0]
    
                                cur.execute(
                                    "INSERT INTO menu_options (category, label, sort_order) VALUES (?, ?, ?)",
                                    (new_category, new_label.strip(), max_sort + 1),
                                )
                                conn.commit()
                                st.success(f"✅ Added '{new_label}' to {new_category}s!")
                                st.rerun()
    
                            except sqlite3.IntegrityError:
                                st.warning("⚠️ This item already exists.")
                            finally:
                                conn.close()
    
                # --- Edit Existing Menu Items ---
                st.markdown("### ✅ Edit Existing Menu Items")
    
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM menu_options ORDER BY category, sort_order, label")
                rows = cursor.fetchall()
                conn.close()
    
                for row in rows:
                    # FLAVORS: Available + Espresso + Cold Brew
                    if row["category"] == "flavor":
                        col1, col2, col3, col4, col5 = st.columns([2.2, 1.4, 1.2, 1.2, 1.2])
    
                        with col1:
                            st.write(f"**{row['label']}**")
                        with col2:
                            st.write(f"Category: {row['category']}")
    
                        with col3:
                            active_val = st.checkbox(
                                "Available",
                                value=bool(row["active"]),
                                key=f"menu_active_{row['id']}",
                            )
    
                        with col4:
                            espresso_val = st.checkbox(
                                "Espresso",
                                value=bool(row["espresso_enabled"]),
                                key=f"menu_espresso_{row['id']}",
                            )
    
                        with col5:
                            cold_val = st.checkbox(
                                "Cold Brew",
                                value=bool(row["cold_brew_enabled"]),
                                key=f"menu_cold_{row['id']}",
                            )
    
                        if (
                            active_val != bool(row["active"])
                            or espresso_val != bool(row["espresso_enabled"])
                            or cold_val != bool(row["cold_brew_enabled"])
                        ):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                """
                                UPDATE menu_options
                                SET active = ?,
                                    espresso_enabled = ?,
                                    cold_brew_enabled = ?
                                WHERE id = ?
                                """,
                                (int(active_val), int(espresso_val), int(cold_val), row["id"]),
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()
    
                    # EVERYTHING ELSE: just Available
                    else:
                        col1, col2, col3 = st.columns([2.2, 1.6, 1.2])
    
                        with col1:
                            st.write(f"**{row['label']}**")
                        with col2:
                            st.write(f"Category: {row['category']}")
    
                        with col3:
                            active_val = st.checkbox(
                                "Available",
                                value=bool(row["active"]),
                                key=f"menu_active_{row['id']}",
                            )
    
                        if active_val != bool(row["active"]):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE menu_options SET active = ? WHERE id = ?",
                                (int(active_val), row["id"]),
                            )
                            conn.commit()
                            conn.close()
                            st.rerun()


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

