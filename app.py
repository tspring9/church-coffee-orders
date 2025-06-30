from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
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

# --- Endpoint: Create Order ---
@app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()

    required_fields = ['customer_name', 'drink_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (customer_name, drink_type, milk_type, flavors, pickup_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('customer_name'),
        data.get('drink_type'),
        data.get('milk_type'),
        data.get('flavors'),
        data.get('pickup_time')
    ))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()

    return jsonify({'message': 'Order created', 'order_id': order_id}), 201

# --- Endpoint: Get All Orders ---
@app.route('/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()

    orders = [dict(row) for row in rows]
    return jsonify(orders)

# --- Endpoint: Update Order Status ---
@app.route('/order/<int:order_id>', methods=['PATCH'])
def update_order(order_id):
    data = request.get_json()
    if 'status' not in data:
        return jsonify({'error': 'Missing status field'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (data['status'], order_id))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Order status updated'})

# --- Initialize DB on First Run ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
