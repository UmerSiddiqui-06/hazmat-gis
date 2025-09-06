import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import bcrypt
from dateutil.relativedelta import relativedelta
from components.custom_warnings import custom_error
from decouple import config
import streamlit as st
from contextlib import contextmanager
import time

class SQLConnectionManager:
    """Context manager for MySQL connections with connection pooling and retry logic"""
    
    def __init__(self):
        self.connection_params = {
            "host": "nozomi.proxy.rlwy.net",
            "port": 27858,
            "database": "railway",
            "user": "root",
            "password": "YPcFdhkwAJbLGOTPXAsEWsCdiXBtvCWW",
            "autocommit": False,
            "connect_timeout": 30,
            "auth_plugin": 'mysql_native_password'
        }
    
    @contextmanager
    def get_connection(self, max_retries=3, retry_delay=2):
        """Get a connection with retry logic"""
        conn = None
        attempt = 0
        
        while attempt < max_retries:
            try:
                conn = mysql.connector.connect(**self.connection_params)
                yield conn
                break  # Success, break out of retry loop
            except Error as e:
                attempt += 1
                error_msg = f"Connection attempt {attempt} failed: {e}"
                print(error_msg)
                
                if attempt == max_retries:
                    # Final attempt failed, re-raise the exception
                    custom_error(f"Failed to connect after {max_retries} attempts: {e}")
                    raise
                
                # Wait before retrying
                time.sleep(retry_delay)
            finally:
                if conn:
                    conn.close()

class sqlpy:
    def __init__(self): 
        self.connection_manager = SQLConnectionManager()
        self.conn = None
        self.cursor = None
        
        try:
            # Test connection
            with self.connection_manager.get_connection() as conn:
                self.conn = conn
                self.cursor = self.conn.cursor()
                print("✓ Database connection successful!")
            
        except Error as e:
            error_msg = f"Unable to load Database: {e}"
            print(error_msg)
            custom_error(error_msg)
            
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
                
            # Set to None to indicate connection failure
            self.conn = None
            self.cursor = None

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close the connection and cursor"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def _execute_with_connection(self, func, *args, **kwargs):
        """Helper method to execute functions with a fresh connection"""
        try:
            with self.connection_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    result = func(cursor, *args, **kwargs)
                    conn.commit()
                    return result
        except Error as e:
            print(f"Database error: {e}")
            raise

    # Cached methods for frequently accessed, rarely changed data
    @st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
    def get_status(_self, email):
        def query_func(cursor, email):
            query = "SELECT status FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            data = cursor.fetchone()
            return data[0] if data else None
        return _self._execute_with_connection(query_func, email)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_gpt_history(_self):
        def query_func(cursor):
            cursor.execute("SELECT * FROM gpt_history")
            return cursor.fetchall()
        return _self._execute_with_connection(query_func)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_gpt_usage(_self):
        def query_func(cursor):
            cursor.execute("SELECT email, ChatGpt_used, ChatGpt_limit FROM users")
            return cursor.fetchall()
        return _self._execute_with_connection(query_func)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_users(_self):
        def query_func(cursor):
            cursor.execute("SELECT * FROM users")
            return cursor.fetchall()
        return _self._execute_with_connection(query_func)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_download_history(_self):
        def query_func(cursor):
            cursor.execute("SELECT * FROM download_history")
            return cursor.fetchall()
        return _self._execute_with_connection(query_func)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_gpt_status(_self):
        def query_func(cursor):
            cursor.execute("SELECT chatgpt from gpt_limit")
            chatgpt = cursor.fetchone()[0]
            return chatgpt
        return _self._execute_with_connection(query_func)

    @st.cache_data(ttl=3600, show_spinner=False)  # Cache for 1 hour
    def get_gpt_limit(_self):
        def query_func(cursor):
            cursor.execute("SELECT chatgpt_limit FROM gpt_limit")
            data = cursor.fetchone()[0]
            return data
        return _self._execute_with_connection(query_func)

    # Non-cached methods for data that changes frequently
    def change_admin(self, user_id):
        def update_func(cursor, user_id):
            cursor.execute("SELECT email, is_admin FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()

            if result is not None:
                email, current_status = result
                if email == "HazMat.GIS@gmail.com":
                    print("Cannot change admin status for the main admin user.")
                    return

                new_status = 0 if current_status else 1
                cursor.execute(
                    "UPDATE users SET is_admin = %s WHERE user_id = %s", (new_status, user_id)
                )
                st.cache_data.clear()  # Clear relevant caches
                print(f"Admin status updated for {user_id}: {current_status} -> {new_status}")
            else:
                print(f"No user found with user_id: {user_id}")
        self._execute_with_connection(update_func, user_id)

    def add_gpt_history(self, email, link, title):
        def insert_func(cursor, email, link, title):
            date = datetime.now().replace(microsecond=0)
            cursor.execute(
                "INSERT INTO gpt_history (email,link,title,time) VALUES (%s,%s,%s,%s)",
                (email, link, title, date),
            )
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(insert_func, email, link, title)

    def get_gpt_response(self, link):
        def query_func(cursor, link):
            cursor.execute(
                "SELECT Response FROM gpt_responses WHERE Link = %s", (link,)
            )
            data = cursor.fetchone()
            return data[0] if data else None
        return self._execute_with_connection(query_func, link)

    def is_temporary_password(self, email):
        def query_func(cursor, email):
            cursor.execute(
                "SELECT is_temporary FROM temporary_password WHERE email = %s", (email,)
            )
            data = cursor.fetchone()
            return data[0] if data else None
        return self._execute_with_connection(query_func, email)

    def add_gpt_response(self, link, response):
        def insert_func(cursor, link, response):
            cursor.execute(
                "INSERT INTO gpt_responses (Link,Response) VALUES (%s,%s)", (link, response)
            )
        self._execute_with_connection(insert_func, link, response)

    def register_user(self, email, password):
        def insert_func(cursor, email, password):
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            cursor.execute("SELECT MAX(user_id) FROM users")
            data = cursor.fetchone()

            new_id = 1 if data[0] is None else data[0] + 1
            global_gpt = self.get_gpt_limit()
            last_reset_date = datetime.now()

            cursor.execute(
                "INSERT INTO users (user_id, email, password, chatgpt, status, ChatGpt_used, ChatGpt_limit, last_reset_date, chatgptlimittype,is_admin) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    new_id,
                    email.lower(),
                    password_hash,
                    0,
                    "Pending",
                    0,
                    global_gpt,
                    last_reset_date,
                    "default",
                    0,
                ),
            )
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(insert_func, email, password)

    def check_login(self, email, input_password):
        def query_func(cursor, email, input_password):
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            data = cursor.fetchone()
            
            if data:
                stored_hashed_password = data[2]
                input_password_bytes = input_password.encode('utf-8')
                stored_hashed_password_bytes = stored_hashed_password.encode('utf-8')
                
                if bcrypt.checkpw(input_password_bytes, stored_hashed_password_bytes):
                    return data[4], data[-3]
                else:
                    return "Rejected", False
            else:
                return "Rejected", False
        return self._execute_with_connection(query_func, email, input_password)

    def change_user_twitter_status(self, user_id):
        def update_func(cursor, user_id):
            cursor.execute("SELECT twitterapi FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()

            if result is not None:
                already_status = result[0]
                new_status = not already_status

                cursor.execute(
                    "UPDATE users SET twitterapi = %s WHERE user_id = %s", (new_status, user_id)
                )
                st.cache_data.clear()  # Clear cache after update
                print(f"User {user_id} Twitter API status updated: {already_status} -> {new_status}")
            else:
                print(f"No user found with user_id: {user_id}")
        self._execute_with_connection(update_func, user_id)

    def change_status(self, user_id):
        def update_func(cursor, user_id):
            cursor.execute("SELECT email, status FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()

            if result is not None:
                email, already_status = result

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

                cursor.execute(
                    "UPDATE users SET status = %s WHERE user_id = %s", (new_status, user_id)
                )
                st.cache_data.clear()  # Clear cache after update
                print(f"User {user_id} status updated: {already_status} -> {new_status}")
            else:
                print(f"No user found with user_id: {user_id}")
        self._execute_with_connection(update_func, user_id)

    def accept_user(self, user_id):
        def update_func(cursor, user_id):
            cursor.execute(
                "UPDATE users SET status = %s WHERE user_id = %s", ("Accepted", user_id)
            )
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func, user_id)

    def reject_user(self, user_id):
        def update_func(cursor, user_id):
            cursor.execute(
                "UPDATE users SET status = %s WHERE user_id = %s", ("Rejected", user_id)
            )
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func, user_id)

    def is_user_exist(self, email):
        def query_func(cursor, email):
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            data = cursor.fetchone()
            return bool(data)
        return self._execute_with_connection(query_func, email)

    def add_new_login(self, email):
        def insert_func(cursor, email):
            date = datetime.now().replace(microsecond=0)
            cursor.execute(
                "INSERT INTO login_history (email, time) VALUES (%s, %s)", (email, date)
            )
        self._execute_with_connection(insert_func, email)

    def get_login_info(self, users_emails):
        def query_func(cursor, users_emails):
            data = []
            for email in users_emails:
                cursor.execute("SELECT * FROM login_history WHERE email = %s", (email,))
                temp = cursor.fetchall()
                if temp:
                    for record in temp:
                        data.append(record)
            return data
        return self._execute_with_connection(query_func, users_emails)

    def add_download_history(self, email, type, category, country, impact, severity, date):
        def insert_func(cursor, email, type, category, country, impact, severity, date):
            download_date = datetime.now().replace(microsecond=0)
            cursor.execute(
                """INSERT INTO download_history (Email,Time,Type,Category,Country,Impact,Severity,Date) 
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (email, download_date, type, category, country, impact, severity, date),
            )
        self._execute_with_connection(insert_func, email, type, category, country, impact, severity, date)

    def change_gpt_status(self):
        def update_func(cursor):
            cursor.execute("SELECT chatgpt from gpt_limit")
            chatgpt = cursor.fetchone()[0]
            chatgpt = chatgpt ^ 1
            cursor.execute("UPDATE gpt_limit SET chatgpt = %s ", (chatgpt,))
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func)

    def get_user_download_status(self, email):
        def query_func(cursor, email):
            cursor.execute("SELECT allow_download FROM users WHERE email = %s", (email,))
            result = cursor.fetchone()
            return result[0] if result else 0
        return self._execute_with_connection(query_func, email)

    def change_user_download_status(self, email):
        def update_func(cursor, email):
            current_status = self.get_user_download_status(email)
            new_status = 1 if current_status == 0 else 0
            cursor.execute("UPDATE users SET allow_download = %s WHERE email = %s", (new_status, email))
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func, email)

    def is_admin(self, email):
        def query_func(cursor, email):
            cursor.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
            result = cursor.fetchone()
            return "admin" if result and result[0] == 1 else "user"
        return self._execute_with_connection(query_func, email)

    def change_user_gpt_status(self, id):
        def update_func(cursor, id):
            cursor.execute("SELECT email, chatgpt FROM users WHERE user_id = %s", (id,))
            result = cursor.fetchone()

            if result is not None:
                email, chatgpt = result

                if email == "HazMat.GIS@gmail.com":
                    print("Cannot change GPT status for the main admin user.")
                    return

                chatgpt ^= 1
                cursor.execute("SELECT chatgpt_limit FROM gpt_limit")
                limit = cursor.fetchone()[0]

                cursor.execute(
                    "UPDATE users SET chatgpt = %s, chatgptlimittype = %s, ChatGpt_limit = %s WHERE user_id = %s",
                    (chatgpt, "default", limit, id),
                )
                st.cache_data.clear()  # Clear cache after update
                print(f"User {id} GPT status updated: {chatgpt}")
            else:
                print(f"No user found with user_id: {id}")
        self._execute_with_connection(update_func, id)

    def get_user_gpt_status(self, email):
        def query_func(cursor, email):
            cursor.execute("SELECT chatgpt FROM users WHERE email = %s", (email,))
            chatgpt = cursor.fetchone()
            return chatgpt[0] if chatgpt else None
        return self._execute_with_connection(query_func, email)

    def get_user_download_history(self, users_emails):
        def query_func(cursor, users_emails):
            data = []
            for email in users_emails:
                cursor.execute(
                    "SELECT * FROM download_history WHERE Email = %s", (email,)
                )
                temp = cursor.fetchall()
                if temp:
                    for record in temp:
                        data.append(record)
            return data
        return self._execute_with_connection(query_func, users_emails)

    def get_gpt_limit_check(self, user):
        def query_func(cursor, user):
            cursor.execute("SELECT ChatGpt_used FROM users WHERE email = %s", (user,))
            data = cursor.fetchone()
            if data:
                data = data[0]
                cursor.execute(
                    "SELECT ChatGpt_limit FROM users WHERE email = %s", (user,)
                )
                limit = cursor.fetchone()
                if limit:
                    limit = limit[0]
                    if data < limit:
                        return True
                    else:
                        if data == limit:
                            cursor.execute(
                                "SELECT last_reset_date FROM users WHERE email = %s", (user,)
                            )
                            old_date = cursor.fetchone()[0]
                            new_date = datetime.now()
                            old_date = datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
                            difference = new_date - old_date
                            if difference.days >= 30:
                                print(difference.days)
                                n = difference.days // 30
                                new_datetime = old_date + relativedelta(months=n)
                                cursor.execute(
                                    "UPDATE users SET ChatGpt_used = %s , last_reset_date = %s WHERE email = %s",
                                    (0, new_datetime, user),
                                )
                                return True
                            else:
                                return False
                        return False
                else:
                    return None
            else:
                return None
        return self._execute_with_connection(query_func, user)

    def increase_gpt(self, user):
        def update_func(cursor, user):
            cursor.execute(
                "SELECT last_reset_date FROM users WHERE email = %s", (user,)
            )
            old_date = cursor.fetchone()[0]
            new_date = datetime.now()
            difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
            if difference.days >= 30:
                n = difference.days // 30
                new_datetime = old_date + relativedelta(months=n)
                cursor.execute(
                    "UPDATE users SET ChatGpt_used = %s , last_reset_date = %s WHERE email = %s",
                    (0, new_datetime, user),
                )
            cursor.execute("SELECT ChatGpt_used FROM users WHERE email = %s", (user,))
            times = cursor.fetchone()[0]
            times = times + 1
            cursor.execute(
                "UPDATE users SET ChatGpt_used = %s WHERE email = %s", (times, user)
            )
        self._execute_with_connection(update_func, user)

    def increase_gpt_limit(self, user, limit):
        def update_func(cursor, user, limit):
            cursor.execute(
                "UPDATE users SET ChatGpt_limit = %s, chatgptlimittype = %s WHERE user_id = %s",
                (limit, "modified", user),
            )
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func, user, limit)

    def set_gpt_limit(self, limit):
        def update_func(cursor, limit):
            cursor.execute(
                "UPDATE users SET ChatGpt_limit = %s WHERE chatgptlimittype = %s",
                (limit, "default"),
            )
            cursor.execute("UPDATE gpt_limit SET chatgpt_limit = %s", (limit,))
            st.cache_data.clear()  # Clear cache after update
        self._execute_with_connection(update_func, limit)

    def update_password(self, email, password):
        def update_func(cursor, email, password):
            # ✅ hash the new password
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            cursor.execute(
                "UPDATE users SET password = %s WHERE email = %s", (hashed, email)
            )
            st.cache_data.clear()
        self._execute_with_connection(update_func, email, password)


    def delete_user(self, email):
        def delete_func(cursor, email):
            try:
                print("Deleting user: ", email)
                cursor.execute("DELETE FROM users WHERE email = %s", (email,))
                st.cache_data.clear()  # Clear cache after update
            except Exception as e:
                raise e
        self._execute_with_connection(delete_func, email)