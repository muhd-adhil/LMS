import sqlite3
from tabulate import tabulate
from datetime import datetime

# Connect to Database
conn = sqlite3.connect("lms.db")
cur = conn.cursor()

# Global Variables to track who is logged in
current_user = None
current_user_id = None

# --- DATABASE SETUP ---
def register_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        leave_balance INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leave_request(
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id INTEGER,
        start_date TEXT,
        end_date TEXT,
        reason TEXT,
        status TEXT,
        FOREIGN KEY('emp_id') REFERENCES employees(emp_id)
    );""")
    conn.commit()

register_db()

# --- ADMIN FUNCTIONS ---
def add_admin():
    """Utility function to manually add an Admin (Manager)"""
    print("\n--- 🛡️ Create Admin Account ---")
    username = input("Set Admin Username: ").strip()
    password = input("Set Admin Password: ").strip()
    
    # We force the role to be 'manager' here
    role = 'manager'
    leave_balance = 15 # Database requires a value, even if managers don't use it
    
    if username and password:
        try:
            cur.execute(
                "INSERT INTO employees (username, password, role, leave_balance) VALUES (?, ?, ?, ?)",
                (username, password, role, leave_balance)
            )
            conn.commit()
            print(f"✅ Success: Admin '{username}' created! You can now login.")
        except sqlite3.IntegrityError:
            print("❌ Error: Username already exists.")
    else:
        print("❌ Error: Username and password cannot be empty.")

def create_user():
    print("\n--- ➕ Create New User ---")
    username = input("Enter a user name : ").strip()
    password = input("Enter Your Password : ").strip()
    role = input("Enter role (employee/manager): ").strip().lower()
    
   
    leave_balance = 15

    if username and password:
        try:
            cur.execute(
                """INSERT INTO employees (username, password, role, leave_balance) VALUES (?, ?, ?, ?)""",
                (username, password, role, leave_balance),
            )
            conn.commit()
            print("SUCCESS: User created successfully.")
        except sqlite3.IntegrityError:
            print("ERROR: Username already exists.")
    else:
        print("ERROR: Username and password cannot be empty.")

def read_user():
    print("\n--- 👥 All Users ---")
    users = cur.execute("SELECT emp_id, username, role, leave_balance FROM employees;").fetchall()
    if users:
        header = ["ID", "USERNAME", "ROLE", "BALANCE"]
        print(tabulate(users, headers=header, tablefmt="double_grid"))
    else:
        print("No users found.")

def update_user():
    print("\n--- ✏️ Update User ---")
    read_user()
    target_username = input("Enter the username to update: ")

    # Check if user exists
    user = cur.execute("SELECT * FROM employees WHERE username=?;", (target_username,)).fetchone()
    
    if not user:
        print("ERROR: User not found.")
        return

    
    print("1. 🔑 Change Password")
    print("2. 👔 Change Role")
    print("3. 💰 Change Leave Balance")
    choice = input("Select choice: ")

    if choice == "1":
        new_pass = input("Enter new password: ")
        cur.execute("UPDATE employees SET password = ? WHERE username=?;", (new_pass, target_username))
        print("Password updated.")
        
    elif choice == "2":
        new_role = input("Enter new role: ")
        cur.execute("UPDATE employees SET role = ? WHERE username=?;", (new_role, target_username))
        print("Role updated.")

    elif choice == "3":
        new_bal = int(input("Enter new balance: "))
        cur.execute("UPDATE employees SET leave_balance = ? WHERE username=?;", (new_bal, target_username))
        print("Balance updated.")
    
    conn.commit()

def delete_user():
    read_user()
    username = input("Enter the username to remove: ")
    if input(f"Are you sure you want to delete {username}? (yes/no): ").lower() == 'yes':
        cur.execute("DELETE FROM employees WHERE username=?;", (username,))
        conn.commit()
        print("User deleted.")
    else:
        print("Deletion cancelled.")

def manage_leave_requests():
    """Admin Function to Approve/Reject and Deduct Balance"""
    print("\n--- 📩 Pending Requests ---")
    
    # Show pending requests 
    query = """
    SELECT lr.request_id, e.username, lr.start_date, lr.end_date, lr.reason, lr.status 
    FROM leave_request lr 
    LEFT JOIN employees e ON lr.emp_id = e.emp_id
    WHERE LOWER(lr.status) = 'pending'
    """
    requests = cur.execute(query).fetchall()
    
    if not requests:
        print("No pending requests found.")
        return

    
    cleaned_requests = []
    for r in requests:
        r_list = list(r)
        if r_list[1] is None: 
            r_list[1] = "UNKNOWN USER (Deleted?)"
        cleaned_requests.append(r_list)

    print(tabulate(cleaned_requests, headers=["Req ID", "User", "Start", "End", "Reason", "Status"], tablefmt="grid"))
    
    req_id = input("\nEnter Request ID to process (or '0' to back): ")
    if req_id == '0': return

    action = input("Approve (a) or Reject (r)? : ").lower()
    
    if action == 'a':
        # --- LOGIC TO DEDUCT BALANCE ---
        
        
        details = cur.execute("SELECT emp_id, start_date, end_date FROM leave_request WHERE request_id=?", (req_id,)).fetchone()
        
        if details:
            emp_id_to_deduct = details[0]
            start_str = details[1]
            end_str = details[2]
            
            
            try:
                d1 = datetime.strptime(start_str, "%Y-%m-%d")
                d2 = datetime.strptime(end_str, "%Y-%m-%d")
                days_to_deduct = (d2 - d1).days + 1
                
                
                cur.execute("UPDATE leave_request SET status='Approved' WHERE request_id=?", (req_id,))
                
                
                cur.execute("UPDATE employees SET leave_balance = leave_balance - ? WHERE emp_id=?", (days_to_deduct, emp_id_to_deduct))
                
                conn.commit()
                print(f"✅ SUCCESS: Request Approved. {days_to_deduct} days deducted from employee's balance.")
                
            except ValueError:
                print("Error calculating dates. Database date format might be wrong.")
        else:
            print("Error: Request ID not found.")
            
    elif action == 'r':
        cur.execute("UPDATE leave_request SET status='Rejected' WHERE request_id=?", (req_id,))
        conn.commit()
        print("🚫 Request Rejected.")

# --- EMPLOYEE FUNCTIONS ---

def leave_request():
    global current_user_id
    print("\n--- 📝 Apply for Leave ---")
    balance_row = cur.execute("SELECT leave_balance FROM employees WHERE emp_id=?", (current_user_id,)).fetchone()
    if balance_row:
        current_balance = balance_row[0]
        print(f"💰 Available Balance: {current_balance} Days")
        print("-" * 30)
    else:
        print("Error: Could not fetch balance.")
        return
    start_date = input("Start date (DD-MM-YYYY) : ")
    end_date = input("End date (DD-MM-YYYY) : ")
    reason = input("Reason : ")

    
    if not start_date or not end_date or not reason:
        print("Error: All fields required.")
        return

    try:
        d1 = datetime.strptime(start_date, "%d-%m-%Y")
        d2 = datetime.strptime(end_date, "%d-%m-%Y")
        
        if d1 > d2:
            print("Error: End date cannot be before Start date.")
            return
        if d1.date() < datetime.now().date():
            print("Error: Cannot apply in the past.")
            return
            
        
        db_start = d1.strftime("%Y-%m-%d")
        db_end = d2.strftime("%Y-%m-%d")
        
        
        days = (d2 - d1).days + 1
        balance_row = cur.execute("SELECT leave_balance FROM employees WHERE emp_id=?", (current_user_id,)).fetchone()
        
       
        if not balance_row:
            print("Error: User not found.")
            return

        current_balance = balance_row[0]
        
        if days > current_balance:
            print(f"Error: Insufficient balance. You have {current_balance} days, but requested {days}.")
            return

    except ValueError:
        print("Error: Invalid Date Format. Use DD-MM-YYYY.")
        return

    # Insert
    cur.execute(
        "INSERT INTO leave_request (emp_id, start_date, end_date, reason, status) VALUES (?, ?, ?, ?, 'Pending')",
        (current_user_id, db_start, db_end, reason)
    )
    conn.commit()
    print("Success: Leave Request Submitted.")

def view_my_requests():
    """SHOWS HISTORY + CURRENT BALANCE"""
    global current_user_id
    print("\n--- 📜 My Leave History ---")

    # 1. Fetch Balance
    balance_row = cur.execute("SELECT leave_balance FROM employees WHERE emp_id=?", (current_user_id,)).fetchone()
    if balance_row:
        print(f"\n💰 YOUR CURRENT BALANCE: {balance_row[0]} Days")
        print("-" * 30)

    # 2. Fetch Requests
    data = cur.execute("SELECT start_date, end_date, reason, status FROM leave_request WHERE emp_id=?", (current_user_id,)).fetchall()
    
    if data:
        print(tabulate(data, headers=["Start", "End", "Reason", "Status"], tablefmt="simple"))
    else:
        print("No history found.")

def cancel_request():
    global current_user_id
    print("\n--- 🚫 Cancel Pending Request ---")
    data = cur.execute("SELECT request_id, start_date, end_date, status FROM leave_request WHERE emp_id=? AND status='Pending'", (current_user_id,)).fetchall()
    
    if not data:
        print("No pending requests to cancel.")
        return

    print(tabulate(data, headers=["ID", "Start", "End", "Status"], tablefmt="simple"))
    
    req_id = input("Enter ID to cancel: ")
    cur.execute("DELETE FROM leave_request WHERE request_id=? AND emp_id=?", (req_id, current_user_id))
    conn.commit()
    print("Request Cancelled.")

# --- MENUS ---

def admin_menu():
    while True:
        print("\n=== 🛠️ ADMIN DASHBOARD ===")
        print("1. ➕ Add User")
        print("2. 👥 List Users")
        print("3. ✏️ Update User")
        print("4. 🗑️ Remove User")
        print("5. ✅ Manage Leave Requests (Approve/Reject)")
        print("6. 🚪 LOGOUT")
        
        choice = input("Choice: ")
        
        if choice == "1": create_user()
        elif choice == "2": read_user()
        elif choice == "3": update_user()
        elif choice == "4": delete_user()
        elif choice == "5": manage_leave_requests()
        elif choice == "6": break
        else: print("Invalid Choice")

def employee_menu():
    while True:
        print(f"\n=== 👤 EMPLOYEE DASHBOARD (User ID: {current_user_id}) ===")
        print("1. 📝 Apply for Leave")
        print("2. 📜 View History")
        print("3. 🚫 Cancel Request")
        print("4. 🚪 LOGOUT")
        
        choice = input("Choice: ")
        
        if choice == '1': leave_request()
        elif choice == '2': view_my_requests()
        elif choice == '3': cancel_request()
        elif choice == '4': break
        else: print("Invalid Choice")

def login():
    global current_user_id
    
    print("\n------ 🔐 USER LOGIN ------")
    user_name = input("Enter user name : ")
    password = input("Enter the password : ")
    
    user = cur.execute("SELECT emp_id, role FROM employees WHERE username = ? AND password =?", (user_name, password)).fetchone()
    
    if user:
        current_user_id = user[0]
        role = user[1]
        print("Login Successful!")
        
        if role == 'manager':
            admin_menu()
        else:
            employee_menu()
    else:
        print("Error: Invalid Username or Password")

def main():
    while True:
        print("\n------ 🏥 LMS MAIN SYSTEM ------") 
        print("1. 🔐 Login")
        print("2. ❌ Exit System")
        choice = input("Choice: ")
        
        if choice == "1":
            login()
        elif choice == "2":
            print("Exiting...")
            break
        else:
            print("Invalid Input")



    # Run the program
if __name__ == "__main__":
    
    # Check if database is empty. If yes, force create an Admin.
    user_count = cur.execute("SELECT count(*) FROM employees").fetchone()[0]
    if user_count == 0:
        print("⚠️ No users found! Let's create the first Admin.")
        add_admin()
        
    main()
    conn.close()
   