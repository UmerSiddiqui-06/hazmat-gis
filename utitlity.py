import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import bcrypt
from dateutil.relativedelta import relativedelta
from custom_warnings import custom_error
from decouple import config

class sqlpy:
    def close_connection(self):
        """Properly close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("Database connection closed")
        except:
            pass
        finally:
            self.cursor = None
            self.conn = None
    def is_connected(self):
        """Check if database connection is active"""
        try:
            return self.conn and self.conn.is_connected() and self.cursor
        except:
            return False
            

    def ensure_connection(self):
        """Ensure database connection is active, reconnect if needed"""
        if not self.is_connected():
            print("Reconnecting to database...")
            self.__init__()  # Reinitialize connection
        return self.is_connected()

    def safe_execute(self, query, params=None):
        """Execute query with connection checking"""
        if not self.ensure_connection():
            print("No database connection available")
            return None
        
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Query execution failed: {e}")
            return None
    def __init__(self): 
        self.conn = None
        self.cursor = None  # Initialize cursor first
        
        try:
            DB_HOST="nozomi.proxy.rlwy.net"
            DB_PORT=27858
            DB_NAME="railway"
            DB_USER="root"
            DB_PASSWORD="YPcFdhkwAJbLGOTPXAsEWsCdiXBtvCWW"
            
            # Debug info (remove password for security)
            print(f"Attempting to connect to MySQL:")
            print(f"  Host: {DB_HOST}")
            print(f"  Port: {DB_PORT}")
            print(f"  Database: {DB_NAME}")
            print(f"  User: {DB_USER}")
            
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                autocommit=False,
                connect_timeout=60,  # Increased timeout
                connection_timeout=60,
                pool_reset_session=True,
                auth_plugin='mysql_native_password'
            )
            
            if self.conn.is_connected():
                self.cursor = self.conn.cursor()
                print("✓ Database connection successful!")
            else:
                raise Exception("Connection established but not active")
                
        except Error as e:
            error_msg = f"Unable to load Database: {e}"
            print(error_msg)
            
            # Set both to None on failure
            self.conn = None
            self.cursor = None
            
            # Don't call custom_error here as it might cause issues in Streamlit
            # custom_error(error_msg)
            
            # Provide more specific error messages
            if "Access denied" in str(e):
                print("This usually means:")
                print("1. Wrong username or password")
                print("2. User doesn't have permission to access the database")
                print("3. Connecting to wrong host (should it be a remote server?)")
            elif "Can't connect to MySQL server" in str(e):
                print("This usually means:")
                print("1. MySQL server is not running")
                print("2. Wrong host or port")
                print("3. Firewall blocking the connection")
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.conn = None
            self.cursor = None

    def get_status(self, email):
        query = "SELECT status FROM users WHERE email = %s"
        self.cursor.execute(query, (email,))
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None

    def change_admin(self, user_id):
        # Fetch the email and is_admin value
        self.cursor.execute("SELECT email, is_admin FROM users WHERE user_id = %s", (user_id,))
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
                "UPDATE users SET is_admin = %s WHERE user_id = %s", (new_status, user_id)
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
            "INSERT INTO gpt_history (email,link,title,time) VALUES (%s,%s,%s,%s)",
            (email, link, title, date),
        )
        self.conn.commit()

    def get_gpt_response(self, link):
        self.cursor.execute(
            "SELECT Response FROM gpt_responses WHERE Link = %s", (link,)
        )
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None

    def is_temporary_password(self, email):
        self.cursor.execute(
            "SELECT is_temporary FROM temporary_password WHERE email = %s", (email,)
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
            "INSERT INTO gpt_responses (Link,Response) VALUES (%s,%s)", (link, response)
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
            "INSERT INTO users (user_id, email, password, chatgpt, status, ChatGpt_used, ChatGpt_limit, last_reset_date, chatgptlimittype,is_admin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
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

    # def check_login(self, email, input_password):
    #     # Fetch the stored hashed password for the given email
    #     self.cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
    #     data = self.cursor.fetchone()
    #     print("data: ", data)
    #     if not data:
    #         # Email does not exist in the database
    #         return None, None

    #     # Extract the hashed password from the database
    #     stored_hashed_password = data[2]  # Assuming the password is stored in the third column

    #     # Verify the input password with the stored hashed password
    #     if bcrypt.checkpw(input_password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
    #         return data[4], data[-3]
    #     else:
    #         # Password does not match
    #         return None, None

    def check_login(self, email, input_password):
        # Ensure connection is active
        if not self.ensure_connection():
            print("❌ Cannot establish database connection for login")
            return None, None
        
        # Double-check cursor exists
        if not self.cursor:
            print("❌ No database cursor available for login")
            return None, None
        
        try:
            # Fetch the stored hashed password for the given email
            self.cursor.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
            data = self.cursor.fetchone()
            print("data: ", data)
            
            if not data:
                # Email does not exist in the database
                return None, None

            # Extract the hashed password from the database
            stored_hashed_password = data[2]  # Assuming the password is stored in the third column

            # Verify the input password with the stored hashed password
            if bcrypt.checkpw(input_password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
                return data[4], data[-3]
            else:
                # Password does not match
                return None, None
                
        except Exception as e:
            print(f"❌ Login query failed: {e}")
            return None, None

    def get_users(self):
        self.cursor.execute("SELECT * FROM users")
        data = self.cursor.fetchall()
        return data
    
    def change_user_twitter_status(self, user_id):
        # Fetch the twitterapi status of the user
        self.cursor.execute("SELECT twitterapi FROM users WHERE user_id = %s", (user_id,))
        result = self.cursor.fetchone()

        if result is not None:
            already_status = result[0]

            new_status = not already_status

            # Update the twitterapi column
            self.cursor.execute(
                "UPDATE users SET twitterapi = %s WHERE user_id = %s", (new_status, user_id)
            )
            self.conn.commit()
            print(f"User {user_id} Twitter API status updated: {already_status} -> {new_status}")
        else:
            print(f"No user found with user_id: {user_id}")

    def change_status(self, user_id):
        # Fetch the email and status of the user
        self.cursor.execute("SELECT email, status FROM users WHERE user_id = %s", (user_id,))
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
                "UPDATE users SET status = %s WHERE user_id = %s", (new_status, user_id)
            )
            self.conn.commit()
            print(f"User {user_id} status updated: {already_status} -> {new_status}")
        else:
            print(f"No user found with user_id: {user_id}")


    def accept_user(self, user_id):
        self.cursor.execute(
            "UPDATE users SET status = %s WHERE user_id = %s", ("Accepted", user_id)
        )
        self.conn.commit()

    def reject_user(self, user_id):
        self.cursor.execute(
            "UPDATE users SET status = %s WHERE user_id = %s", ("Rejected", user_id)
        )
        self.conn.commit()

    def is_user_exist(self, email):
        self.cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
        data = self.cursor.fetchone()
        if data:
            return True
        else:
            return False

    def add_new_login(self, email):
        date = datetime.now().replace(microsecond=0)
        self.cursor.execute(
            "INSERT INTO login_history (email, time) VALUES (%s, %s)", (email, date)
        )
        self.conn.commit()

    def get_login_info(self, users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute("SELECT * FROM login_history WHERE email = %s", (email,))
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
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
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
        self.cursor.execute("UPDATE gpt_limit SET chatgpt = %s ", (chatgpt,))
        self.conn.commit()
        
    def get_user_download_status(self, email):
        """Check if the user is allowed to download."""
        self.cursor.execute("SELECT allow_download FROM users WHERE email = %s", (email,))
        result = self.cursor.fetchone()
        return result[0] if result else 0  # Default to disabled


    def change_user_download_status(self, email):
       """Toggle the user's download permission."""
       current_status = self.get_user_download_status(email)
       new_status = 1 if current_status == 0 else 0  # Toggle between 0 and 1
       self.cursor.execute("UPDATE users SET allow_download = %s WHERE email = %s", (new_status, email))
       self.conn.commit()


    def get_gpt_status(self):
        self.cursor.execute("SELECT chatgpt from gpt_limit")
        chatgpt = self.cursor.fetchone()[0]
        return chatgpt
        
    def is_admin(self, email):
        if not self.ensure_connection():
            print("Database connection not available for is_admin check")
            return "user"  # Safe default
        
        try:
            self.cursor.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
            result = self.cursor.fetchone()
            
            if result is not None:
                return "admin" if result[0] == 1 else "user"
            return "user"  # Default to "user" if email is not found
            
        except Exception as e:
            print(f"is_admin query failed: {e}")
            return "user"  # Safe default

    def change_user_gpt_status(self, id):
        # Fetch the email and chatgpt status of the user
        self.cursor.execute("SELECT email, chatgpt FROM users WHERE user_id = %s", (id,))
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
                "UPDATE users SET chatgpt = %s, chatgptlimittype = %s, ChatGpt_limit = %s WHERE user_id = %s",
                (chatgpt, "default", limit, id),
            )
            self.conn.commit()
            print(f"User {id} GPT status updated: {chatgpt}")
        else:
            print(f"No user found with user_id: {id}")


    def get_user_gpt_status(self, email):
        self.cursor.execute("SELECT chatgpt FROM users WHERE email = %s", (email,))
        chatgpt = self.cursor.fetchone()
        if chatgpt:
            return chatgpt[0]
        else:
            return None

    def get_user_download_history(self, users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute(
                "SELECT * FROM download_history WHERE Email = %s", (email,)
            )
            temp = self.cursor.fetchall()
            if temp:
                for record in temp:
                    data.append(record)
        return data

    def get_gpt_limit_check(self, user):
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = %s", (user,))
        data = self.cursor.fetchone()
        if data:
            data = data[0]
            self.cursor.execute(
                "SELECT ChatGpt_limit FROM users WHERE email = %s", (user,)
            )
            limit = self.cursor.fetchone()
            if limit:
                limit = limit[0]
                if data < limit:
                    return True
                else:
                    if data == limit:
                        self.cursor.execute(
                            "SELECT last_reset_date FROM users WHERE email = %s", (user,)
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
                                "UPDATE users SET ChatGpt_used = %s , last_reset_date = %s WHERE email = %s",
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
            "SELECT last_reset_date FROM users WHERE email = %s", (user,)
        )
        old_date = self.cursor.fetchone()[0]
        new_date = datetime.now()
        difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
        if difference.days >= 30:
            n = difference.days // 30
            new_datetime = old_date + relativedelta(months=n)
            self.cursor.execute(
                "UPDATE users SET ChatGpt_used = %s , last_reset_date = %s WHERE email = %s",
                (0, new_datetime, user),
            )
            self.conn.commit()
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = %s", (user,))
        times = self.cursor.fetchone()[0]
        times = times + 1
        self.cursor.execute(
            "UPDATE users SET ChatGpt_used = %s WHERE email = %s", (times, user)
        )
        self.conn.commit()

    def increase_gpt_limit(self, user, limit):
        self.cursor.execute(
            "UPDATE users SET ChatGpt_limit = %s, chatgptlimittype = %s WHERE user_id = %s",
            (limit, "modified", user),
        )
        self.conn.commit()

    def set_gpt_limit(self, limit):
        self.cursor.execute(
            "UPDATE users SET ChatGpt_limit = %s WHERE chatgptlimittype = %s",
            (limit, "default"),
        )
        self.cursor.execute("UPDATE gpt_limit SET chatgpt_limit = %s", (limit,))
        self.conn.commit()

    def get_gpt_limit(self):
        self.cursor.execute("SELECT chatgpt_limit FROM gpt_limit")
        data = self.cursor.fetchone()[0]
        return data

    def update_password(self, email, password):
        self.cursor.execute(
            "UPDATE users SET password = %s WHERE email = %s", (password, email)
        )

        self.conn.commit()

    def delete_user(self, email):
        try:
            print("Deleting user: ", email)
            # Delete the user with the specified email
            self.cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"An error occurred: {e}")