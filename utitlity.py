import sqlite3
from datetime import datetime, timedelta
import bcrypt
from dateutil.relativedelta import relativedelta
from custom_warnings import custom_error

class sqlpy:
    def __init__(self): 
        try:
            self.conn = sqlite3.connect(
                "/var/data/my_database.db", check_same_thread=False
            )
        except:
            custom_error("Unable to load Database")
            return None
        self.cursor = self.conn.cursor()
        password = bcrypt.hashpw("0000".encode("utf-8"), bcrypt.gensalt())
        


        
        # Delete the table if it exists
        self.cursor.execute("DROP TABLE IF EXISTS gpt_limit")
        self.conn.commit()

        # # Recreate the table
        # self.cursor.execute(
        # """CREATE TABLE gpt_limit (
        # chatgpt BOOL,
        # chatgpt_limit INTEGER,
        # enable_download BOOL DEFAULT 0
        # );"""
        # )
        # self.conn.commit()

# Insert default values
        self.cursor.execute(
        "INSERT INTO gpt_limit (chatgpt, chatgpt_limit, enable_download) VALUES (?, ?, ?)", 
        (1, 5, 0)
        )
        self.conn.commit()

        # self.cursor.execute("UPDATE users SET email = 'HazMat.GIS@gmail.com' WHERE email = 'admin'")

        # self.cursor.execute("INSERT INTO gpt_limit (chatgpt, ChatGpt_limit) VALUES (1, 5)")

        # self.cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOL DEFAULT 0")

        # self.cursor.execute("""
        #     INSERT INTO users (user_id, email, password, chatgpt, status, ChatGpt_used, last_reset_date, ChatGpt_limit, chatgptlimittype, is_admin) 
        #     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        # """, (0, 'admin', password, 1, 'Accepted', 0, datetime.now(), 5, 'default', 1))

        # self.conn.commit()
        # Create the users table
        
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                email VARCHAR(255),  
                password VARCHAR(255),
                chatgpt BOOL,
                status VARCHAR(255),
                ChatGpt_used INTEGER,
                ChatGpt_limit INTEGER,
                last_reset_date DATETIME,
                chatgptlimittype VARCHAR(255),
                is_admin BOOl
                );"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS temporary_password(
                email VARCHAR(255),
                is_temporary BOOL
            )"""
        )

        self.cursor.execute("SELECT * FROM temporary_password")
        if not self.cursor.fetchone():
            self.cursor.execute(
                "INSERT INTO temporary_password (email,is_temporary) VALUES (?,?)",
                ("temp4", True),
            )

        # # Create the gpt_limit table
        # self.cursor.execute(
        #     """CREATE TABLE IF NOT EXISTS gpt_limit (
        #     chatgpt BOOL,
        #     chatgpt_limit INTEGER,
        #     enable_download BOOL DEFAULT 0  -- New column for download toggle
        #    );"""
        #   )


        # Create the login_history table
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS login_history(
                email VARCHAR(255),
                time DATETIME                        
                );"""
        )

        # Create the download_history
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS download_history(
                Email VARCHAR(255),
                Time DATETIME,
                Type VARCHAR(255),
                Category VARCHAR(255),
                Country VARCHAR(255),
                Impact VARCHAR(255),
                Severity VARCHAR(255),
                Date VARCHAR(255)            
                );"""
        )

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS gpt_history(
                email VARCHAR(255),
                link TEXT,
                title TEXT,
                time DATETIME
            );"""
        )

        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS gpt_responses(
                Link VARCHAR(255),
                Response TEXT
            );"""
        )

        self.cursor.execute("SELECT * FROM users")
        data = self.cursor.fetchone()
        if not data:
            password = bcrypt.hashpw("0000".encode("utf-8"), bcrypt.gensalt())
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "0",
                    "admin",
                    password,
                    1,
                    "Accepted",
                    0,
                    datetime.now(),
                    5,
                    "default",
                    1,
                ),
            )
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "1",
                    "temp",
                    password,
                    0,
                    "Accepted",
                    0,
                    datetime.now(),
                    5,
                    "defualt",
                    0,
                ),
            )
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "2",
                    "temp1",
                    password,
                    1,
                    "Pending",
                    0,
                    datetime.now(),
                    5,
                    "default",
                    0,
                ),
            )
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "3",
                    "temp2",
                    password,
                    1,
                    "Rejected",
                    0,
                    datetime.now(),
                    5,
                    "default",
                    0,
                ),
            )
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "4",
                    "temp3",
                    password,
                    1,
                    "Accepted",
                    4,
                    datetime.now(),
                    5,
                    "default",
                    0,
                ),
            )
            self.cursor.execute(
                "INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype,is_admin) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "5",
                    "temp4",
                    password,
                    1,
                    "Accepted",
                    5,
                    datetime.now(),
                    5,
                    "default",
                    0,
                ),
            )

        

        self.cursor.execute("UPDATE users SET email = LOWER(email)")

        self.conn.commit()

    def get_status(self, email):
        query = "SELECT status FROM users WHERE email = ?"
        self.cursor.execute(query, (email,))
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None

    def change_admin(self, user_id):
        # Fetch the email and is_admin value
        self.cursor.execute("SELECT email, is_admin FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()

        if result is not None:
            email, current_status = result
            # If email is 'admin', do nothing and return
            if email == "HazMat.GIS@gmail.com":
                print("Cannot change admin status for the main admin user.")
                return

            new_status = 0 if current_status else 1  # Toggle boolean (0 ⇄ 1)

            # Update the is_admin column
            self.cursor.execute(
                "UPDATE users SET is_admin = ? WHERE user_id = ?", (new_status, user_id)
            )
            self.conn.commit()
            print(f"Admin status updated for {user_id}: {current_status} -> {new_status}")
        else:
            print(f"No user found with user_id: {user_id}")


    def get_gpt_history(self):
        self.cursor.execute("SELECT * FROM gpt_history")
        return self.cursor.fetchall()

    def add_gpt_history(self, email, link, title):
        date = datetime.now().replace(microsecond=0)
        self.cursor.execute(
            "INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",
            (email, link, title, date),
        )
        self.conn.commit()

    def get_gpt_response(self, link):
        self.cursor.execute(
            "SELECT Response FROM gpt_responses WHERE Link = ?", (link,)
        )
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None

    def is_temporary_password(self, email):
        self.cursor.execute(
            "SELECT is_temporary FROM temporary_password WHERE email = ?", (email,)
        )
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None

    def get_gpt_usage(self):
        self.cursor.execute("SELECT email,ChatGpt_used,ChatGpt_limit FROM users")
        return self.cursor.fetchall()

    def add_gpt_response(self, link, response):
        self.cursor.execute(
            "INSERT INTO gpt_responses (Link,Response) VALUES (?,?)", (link, response)
        )
        self.conn.commit()

    def register_user(self, email, password):
        """
        Registers a new user with the given email and password.

        Parameters:
            email (str): The email of the user.
            password (str): The plain text password of the user.
        """
        password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Get the maximum current ID
        self.cursor.execute("SELECT MAX(user_id) FROM users")
        data = self.cursor.fetchone()

        if data[0] is None:
            new_id = 1  # Start with ID 1 if the table is empty
        else:
            new_id = data[0] + 1  # Increment the maximum ID by 1

        global_gpt = self.get_gpt_limit()
        last_reset_date = datetime.now()

        # Insert the new user into the users table
        self.cursor.execute(
            "INSERT INTO users (user_id, email, password, chatgpt, status, ChatGpt_used, ChatGpt_limit, last_reset_date, chatgptlimittype,is_admin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id,
                email.lower(),
                password,
                0,
                "Pending",
                0,
                global_gpt,
                last_reset_date,
                "default",
                0,
            ),
        )

        self.conn.commit()

    def check_login(self, email, input_password):
        # Fetch the stored hashed password for the given email
        self.cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        data = self.cursor.fetchone()

        if not data:
            # Email does not exist in the database
            return None, None

        # Extract the hashed password from the database
        stored_hashed_password = data[2]  # Assuming the password is stored in the third column

        # Verify the input password with the stored hashed password
        if bcrypt.checkpw(input_password.encode("utf-8"), stored_hashed_password):
            return data[4], data[-1]
        else:
            # Password does not match
            return None, None

    def get_users(self):
        self.cursor.execute("SELECT * FROM users")
        data = self.cursor.fetchall()
        return data

    def change_status(self, user_id):
        # Fetch the email and status of the user
        self.cursor.execute("SELECT email, status FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()

        if result is not None:
            email, already_status = result

            # If email is 'admin', do nothing and return
            if email == "HazMat.GIS@gmail.com":
                print("Cannot change status for the main admin user.")
                return

            if already_status in ["Rejected", "Pending"]:
                new_status = "Accepted"
            elif already_status == "Accepted":
                new_status = "Rejected"
            else:
                print("Invalid status found.")
                return

            # Update the status column
            self.cursor.execute(
                "UPDATE users SET status = ? WHERE user_id = ?", (new_status, user_id)
            )
            self.conn.commit()
            print(f"User {user_id} status updated: {already_status} -> {new_status}")
        else:
            print(f"No user found with user_id: {user_id}")


    def accept_user(self, user_id):
        self.cursor.execute(
            "UPDATE users SET status = ? WHERE user_id = ?", ("Accepted", user_id)
        )
        self.conn.commit()

    def reject_user(self, user_id):
        self.cursor.execute(
            "UPDATE users SET status = ? WHERE user_id = ?", ("Rejected", user_id)
        )
        self.conn.commit()

    def is_user_exist(self, email):
        self.cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
        data = self.cursor.fetchone()
        if data:
            return True
        else:
            return False

    def add_new_login(self, email):
        date = datetime.now().replace(microsecond=0)
        self.cursor.execute(
            "INSERT INTO login_history (email, time) VALUES (?, ?)", (email, date)
        )
        self.conn.commit()

    def get_login_info(self, users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute("SELECT * FROM login_history WHERE email = ?", (email,))
            temp = self.cursor.fetchall()
            if temp:
                for record in temp:
                    data.append(record)
        return data

    def add_download_history(
        self, email, type, category, country, impact, severity, date
    ):
        download_date = datetime.now().replace(microsecond=0)
        self.cursor.execute(
            """INSERT INTO download_history (Email,Time,Type,Category,Country,Impact,Severity,Date) 
            VALUES (?,?,?,?,?,?,?,?)""",
            (email, download_date, type, category, country, impact, severity, date),
        )
        self.conn.commit()

    def get_download_history(self):
        self.cursor.execute("SELECT * FROM download_history")
        data = self.cursor.fetchall()
        return data

    def change_gpt_status(self):
        self.cursor.execute("SELECT chatgpt from gpt_limit")
        chatgpt = self.cursor.fetchone()[0]
        chatgpt = chatgpt ^ 1
        self.cursor.execute("UPDATE gpt_limit SET chatgpt = ? ", (chatgpt,))
        self.conn.commit()
    def get_download_status(self):
        """Fetch the current download status (enabled/disabled)."""
        self.cursor.execute("SELECT enable_download FROM gpt_limit")
        result = self.cursor.fetchone()
        return result[0] if result else 0  # Default to disabled

    def change_download_status(self):
        """Toggle the download status (Enable/Disable)."""
        self.cursor.execute("SELECT enable_download FROM gpt_limit")
        current_status = self.cursor.fetchone()[0]
        new_status = 1 if current_status == 0 else 0  # Toggle between 0 and 1
        self.cursor.execute("UPDATE gpt_limit SET enable_download = ?", (new_status,))
        self.conn.commit()

    def get_gpt_status(self):
        self.cursor.execute("SELECT chatgpt from gpt_limit")
        chatgpt = self.cursor.fetchone()[0]
        return chatgpt
    def is_admin(self, email):
        self.cursor.execute("SELECT is_admin FROM users WHERE email = ?", (email,))
        result = self.cursor.fetchone()
        
        if result is not None:
            return "admin" if result[0] == 1 else "user"
        return "user"  # Default to "user" if email is not found

    def change_user_gpt_status(self, id):
        # Fetch the email and chatgpt status of the user
        self.cursor.execute("SELECT email, chatgpt FROM users WHERE user_id = ?", (id,))
        result = self.cursor.fetchone()

        if result is not None:
            email, chatgpt = result

            # If email is 'admin', do nothing and return
            if email == "HazMat.GIS@gmail.com":
                print("Cannot change GPT status for the main admin user.")
                return

            # Toggle chatgpt status (0 ⇄ 1)
            chatgpt ^= 1

            # Fetch the default GPT limit from gpt_limit table
            self.cursor.execute("SELECT chatgpt_limit FROM gpt_limit")
            limit = self.cursor.fetchone()[0]

            # Update user's GPT status and limit
            self.cursor.execute(
                "UPDATE users SET chatgpt = ?, chatgptlimittype = ?, ChatGpt_limit = ? WHERE user_id = ?",
                (chatgpt, "default", limit, id),
            )
            self.conn.commit()
            print(f"User {id} GPT status updated: {chatgpt}")
        else:
            print(f"No user found with user_id: {id}")


    def get_user_gpt_status(self, email):
        self.cursor.execute("SELECT chatgpt FROM users WHERE email = ?", (email,))
        chatgpt = self.cursor.fetchone()
        if chatgpt:
            return chatgpt[0]
        else:
            return None

    def get_user_download_history(self, users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute(
                "SELECT * FROM download_history WHERE Email = ?", (email,)
            )
            temp = self.cursor.fetchall()
            if temp:
                for record in temp:
                    data.append(record)
        return data

    def get_gpt_limit_check(self, user):
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = ?", (user,))
        data = self.cursor.fetchone()
        if data:
            data = data[0]
            self.cursor.execute(
                "SELECT ChatGpt_limit FROM users WHERE email = ?", (user,)
            )
            limit = self.cursor.fetchone()
            if limit:
                limit = limit[0]
                if data < limit:
                    return True
                else:
                    if data == limit:
                        self.cursor.execute(
                            "SELECT last_reset_date FROM users WHERE email = ?", (user,)
                        )
                        old_date = self.cursor.fetchone()[0]
                        new_date = datetime.now()
                        old_date = datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
                        difference = new_date - old_date
                        if difference.days >= 30:
                            print(difference.days)
                            n = difference.days // 30
                            new_datetime = old_date + relativedelta(months=n)
                            self.cursor.execute(
                                "UPDATE users SET ChatGpt_used = ? , last_reset_date = ? WHERE email = ?",
                                (0, new_datetime, user),
                            )
                            self.conn.commit()
                            return True
                        else:
                            return False
                    return False
            else:
                return None
        else:
            return None

    def increase_gpt(self, user):
        self.cursor.execute(
            "SELECT last_reset_date FROM users WHERE email = ?", (user,)
        )
        old_date = self.cursor.fetchone()[0]
        new_date = datetime.now()
        difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
        if difference.days >= 30:
            n = difference.days // 30
            new_datetime = old_date + relativedelta(months=n)
            self.cursor.execute(
                "UPDATE users SET ChatGpt_used = ? , last_reset_date = ? WHERE email = ?",
                (0, new_datetime, user),
            )
            self.conn.commit()
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = ?", (user,))
        times = self.cursor.fetchone()[0]
        times = times + 1
        self.cursor.execute(
            "UPDATE users SET ChatGpt_used = ? WHERE email = ?", (times, user)
        )
        self.conn.commit()

    def increase_gpt_limit(self, user, limit):
        self.cursor.execute(
            "UPDATE users SET ChatGpt_limit = ?, chatgptlimittype = ? WHERE user_id = ?",
            (limit, "modified", user),
        )
        self.conn.commit()

    def set_gpt_limit(self, limit):
        self.cursor.execute(
            "UPDATE users SET ChatGpt_limit = ? WHERE chatgptlimittype = ?",
            (limit, "default"),
        )
        self.cursor.execute("UPDATE gpt_limit SET chatgpt_limit = ?", (limit,))
        self.conn.commit()

    def get_gpt_limit(self):
        self.cursor.execute("SELECT chatgpt_limit FROM gpt_limit")
        data = self.cursor.fetchone()[0]
        return data

    def update_password(self, email, password):
        self.cursor.execute(
            "UPDATE users SET password = ? WHERE email = ?", (password, email)
        )

        self.conn.commit()

    def delete_user(self, email):
        try:
            print("Deleting user: ", email)
            # Delete the user with the specified email
            self.cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"An error occurred: {e}")
