import sqlite3
from datetime import datetime,timedelta
import bcrypt
from dateutil.relativedelta import relativedelta

class sqlpy:
    def __init__(self):
        self.conn = sqlite3.connect('my_database.db',check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Create the users table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                email VARCHAR(255),  
                password VARCHAR(255),
                chatgpt BOOL,
                status VARCHAR(255),
                ChatGpt_used INTEGER,
                ChatGpt_limit INTEGER,
                last_reset_date DATETIME,
                chatgptlimittype VARCHAR(255)
                );""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS temporary_password(
                email VARCHAR(255),
                is_temporary BOOL
            )""")
        
        self.cursor.execute("SELECT * FROM temporary_password")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO temporary_password (email,is_temporary) VALUES (?,?)",("temp4",True))

        # Create the admin table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS admin (
                email VARCHAR(255),
                password VARCHAR(255),
                chatgpt BOOL,
                chatgpt_limit INTEGER            
                );""")
        
        # Create the login_history table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS login_history(
                email VARCHAR(255),
                time DATETIME                        
                );""")
        
        # Create the download_history
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS download_history(
                Email VARCHAR(255),
                Time DATETIME,
                Type VARCHAR(255),
                Category VARCHAR(255),
                Country VARCHAR(255),
                Impact VARCHAR(255),
                Severity VARCHAR(255),
                Date VARCHAR(255)            
                );""")
        
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS gpt_history(
                email VARCHAR(255),
                link TEXT,
                title TEXT,
                time DATETIME
            );""")
        
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS gpt_responses(
                Link VARCHAR(255),
                Response TEXT
            );""")
        
        self.cursor.execute("SELECT * FROM gpt_history")
        data = self.cursor.fetchone()
        if not data:
            self.cursor.execute("INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",("temp","https://www.reuters.com/world/asia-pacific/unstable-nuclear-waste-dams-threaten-fertile-central-asia-heartland-2024-04-23/","temp","11:19"))
            self.cursor.execute("INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",("temp4","https://www.cbsnews.com/sacramento/news/large-explosions-reported-near-sikh-temple-in-south-sacramento-area/","temp","11:20"))
            self.cursor.execute("INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",("temp","https://www.cbsnews.com/sacramento/news/large-explosions-reported-near-sikh-temple-in-south-sacramento-area/","temp","11:21"))
            self.cursor.execute("INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",("temp4","https://www.cbsnews.com/sacramento/news/large-explosions-reported-near-sikh-temple-in-south-sacramento-area/","temp","11:22"))
        
        
        self.cursor.execute('SELECT * FROM users')
        data = self.cursor.fetchone()
        if not data:
            password = bcrypt.hashpw("0000".encode('utf-8'), bcrypt.gensalt())
            
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype) VALUES(?,?,?,?,?,?,?,?,?)",('1','temp',password,0,'Accepted',0,datetime.now(),5,"defualt"))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype) VALUES(?,?,?,?,?,?,?,?,?)",('2','temp1',password,1,'Pending',0,datetime.now(),5,"default"))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype) VALUES(?,?,?,?,?,?,?,?,?)",('3','temp2',password,1,'Rejected',0,datetime.now(),5,"default"))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype) VALUES(?,?,?,?,?,?,?,?,?)",('4','temp3',password,1,'Accepted',4,datetime.now(),5,"default"))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,last_reset_date,ChatGpt_limit,chatgptlimittype) VALUES(?,?,?,?,?,?,?,?,?)",('5','temp4',password,1,'Accepted',5,datetime.now(),5,"default"))

        # Insert admin record
        self.cursor.execute('SELECT * FROM admin')
        data = self.cursor.fetchone()
        admin_password = bcrypt.hashpw("0000".encode('utf-8'), bcrypt.gensalt())
        if not data:
            self.cursor.execute("INSERT INTO admin (email, password, chatgpt, chatgpt_limit) VALUES (?, ?, ?, ?)", ('admin', admin_password,1,5))
        self.conn.commit()

    def get_status(self,email):
        query = "SELECT status FROM users WHERE email = ?"
        self.cursor.execute(query,(email,))
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None
    
    def get_gpt_history(self):
        self.cursor.execute("SELECT * FROM gpt_history")
        return self.cursor.fetchall()
    
    def add_gpt_history(self,email,link,title):
        date = datetime.now().replace(microsecond=0)
        self.cursor.execute("INSERT INTO gpt_history (email,link,title,time) VALUES (?,?,?,?)",(email,link,title,date))
        self.conn.commit()
    
    def get_gpt_response(self,link):
        self.cursor.execute("SELECT Response FROM gpt_responses WHERE Link = ?",(link,))
        data =  self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None
    def is_temporary_password(self,email):
        self.cursor.execute("SELECT is_temporary FROM temporary_password WHERE email = ?",(email,))
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None
    
    def get_gpt_usage(self):
        self.cursor.execute("SELECT email,ChatGpt_used,ChatGpt_limit FROM users")
        return self.cursor.fetchall()
    
    def add_gpt_response(self,link,response):
        self.cursor.execute("INSERT INTO gpt_responses (Link,Response) VALUES (?,?)",(link,response))
        self.conn.commit()
        
    def register_user(self, email, password):
        """
        Registers a new user with the given email and password.

        Parameters:
            email (str): The email of the user.
            password (str): The plain text password of the user.
        """
        password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Get the maximum current ID
        self.cursor.execute("SELECT MAX(id) FROM users")
        data = self.cursor.fetchone()

        if data[0] is None:
            new_id = 1  # Start with ID 1 if the table is empty
        else:
            new_id = data[0] + 1  # Increment the maximum ID by 1

        global_gpt = self.get_gpt_limit()
        last_reset_date = datetime.now()

        # Insert the new user into the users table
        self.cursor.execute(
            'INSERT INTO users (id, email, password, chatgpt, status, ChatGpt_used, ChatGpt_limit, last_reset_date, chatgptlimittype) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (new_id, email, password, 0, 'Pending', 0, global_gpt, last_reset_date, "default")
        )

        self.conn.commit()


    def check_login_admin(self, email, input_password):
        # Fetch the stored hashed password for the given admin email
        self.cursor.execute("SELECT * FROM admin WHERE email = ?", (email,))
        data = self.cursor.fetchone()

        if not data:
            # Email does not exist in the database
            return None

        # Extract the hashed password from the database
        stored_hashed_password = data[1]  # Assuming the password is stored in the third column

        # Verify the input password with the stored hashed password
        if bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password):
            return 'admin'  # Return 'admin' role if the login is successful
        else:
            # Password does not match
            return None

    def check_login_user(self, email, input_password):
        # Fetch the stored hashed password for the given email
        self.cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        data = self.cursor.fetchone()

        if not data:
            # Email does not exist in the database
            return None

        # Extract the hashed password from the database
        stored_hashed_password = data[2]  # Assuming the password is stored in the third column

        # Verify the input password with the stored hashed password
        if bcrypt.checkpw(input_password.encode('utf-8'), stored_hashed_password):
            return data[4]  # Return the desired value (e.g., user ID or role)
        else:
            # Password does not match
            return None

        
    def get_users(self):
        self.cursor.execute("SELECT * FROM users")
        data = self.cursor.fetchall()
        return data
    
    def change_status(self,user_id):
        self.cursor.execute("SELECT status FROM users WHERE user_id = ?",(user_id,))
        already_status = self.cursor.fetchone()[0]
        if already_status == 'Rejected' or already_status=='Pending':
            self.cursor.execute("UPDATE users SET status = ? WHERE user_id = ?",("Accepted",user_id))
        elif already_status=='Accepted': 
            self.cursor.execute("UPDATE users SET status = ? WHERE user_id = ?",('Rejected',user_id))
        self.conn.commit()

    def accept_user(self,user_id):
        self.cursor.execute("UPDATE users SET status = ? WHERE user_id = ?",('Accepted',user_id))
        self.conn.commit()

    def reject_user(self,user_id):
        self.cursor.execute("UPDATE users SET status = ? WHERE user_id = ?",('Rejected',user_id))
        self.conn.commit()

    def is_user_exist(self,email):
        self.cursor.execute('SELECT email FROM users WHERE email = ?',(email,))
        data = self.cursor.fetchone()
        if data:
            return True
        else:
            return False
    
    def add_new_login(self,email):
        date = datetime.now().replace(microsecond=0)
        self.cursor.execute('INSERT INTO login_history (email, time) VALUES (?, ?)', (email,date))
        self.conn.commit()
    
    def get_login_info(self,users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute('SELECT * FROM login_history WHERE email = ?',(email,))
            temp = self.cursor.fetchall()
            if temp:
                for record in temp:
                    data.append(record)
        return data
    
    def add_download_history(self,email,type,category,country,impact,severity,date):
        download_date = datetime.now().replace(microsecond=0)
        self.cursor.execute("""INSERT INTO download_history (Email,Time,Type,Category,Country,Impact,Severity,Date) 
            VALUES (?,?,?,?,?,?,?,?)""",(email,download_date,type,category,country,impact,severity,date))
        self.conn.commit()

    def get_download_history(self):
        self.cursor.execute("SELECT * FROM download_history")
        data = self.cursor.fetchall()
        return data
    
    def change_gpt_status(self):
        self.cursor.execute('SELECT chatgpt from admin')
        chatgpt = self.cursor.fetchone()[0]
        chatgpt = chatgpt ^ 1
        self.cursor.execute('UPDATE admin SET chatgpt = ? ',(chatgpt,))
        self.conn.commit()

    def get_gpt_status(self):
        self.cursor.execute('SELECT chatgpt from admin')
        chatgpt = self.cursor.fetchone()[0]
        return chatgpt
    
    def change_user_gpt_status(self,id):
        self.cursor.execute('SELECT chatgpt FROM users WHERE user_id = ?',(id,))
        chatgpt = self.cursor.fetchone()[0]
        chatgpt = chatgpt ^ 1
        self.cursor.execute("SELECT chatgpt_limit FROM admin")
        limit = self.cursor.fetchone()[0]
        self.cursor.execute('UPDATE users SET chatgpt = ?, chatgptlimittype = ?, ChatGpt_limit = ? WHERE user_id = ?',(chatgpt,"default",limit,id))
        self.conn.commit()

    def get_user_gpt_status(self,email):
        self.cursor.execute('SELECT chatgpt FROM users WHERE email = ?',(email,))
        chatgpt = self.cursor.fetchone()
        if chatgpt:
            return chatgpt[0]
        else:
            return None
    
    def get_user_download_history(self,users_emails):
        data = []
        for email in users_emails:
            self.cursor.execute('SELECT * FROM download_history WHERE Email = ?',(email,))
            temp = self.cursor.fetchall()
            if temp:
                for record in temp:
                    data.append(record)
        return data
    
    def get_gpt_limit_check(self,user):
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = ?",(user,))
        data = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT ChatGpt_limit FROM users WHERE email = ?",(user,))
        limit = self.cursor.fetchone()[0]
        if data < limit:
            return True
        else:
            if data == limit:
                self.cursor.execute("SELECT last_reset_date FROM users WHERE email = ?",(user,))
                old_date = self.cursor.fetchone()[0]
                new_date = datetime.now()
                difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S")
                if difference.days >= 30:
                    n = difference.days//30
                    new_datetime = old_date + relativedelta(months=n)
                    self.cursor.execute("UPDATE users SET ChatGpt_used = ? , last_reset_date = ? WHERE email = ?",(0,new_datetime,user))
                    self.conn.commit()
                    return True
                else:
                    return False
            return False
        
    def increase_gpt(self,user):
        self.cursor.execute("SELECT last_reset_date FROM users WHERE email = ?",(user,))
        old_date = self.cursor.fetchone()[0]
        new_date = datetime.now()
        difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S")
        if difference.days >= 30:
            n = difference.days//30
            new_datetime = old_date + relativedelta(months=n)
            self.cursor.execute("UPDATE users SET ChatGpt_used = ? , last_reset_date = ? WHERE email = ?",(0,new_datetime,user))
            self.conn.commit()
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = ?",(user,))
        times = self.cursor.fetchone()[0]
        times = times+1
        self.cursor.execute("UPDATE users SET ChatGpt_used = ? WHERE email = ?",(times,user))
        self.conn.commit()

    def increase_gpt_limit(self,user,limit):
        self.cursor.execute("UPDATE users SET ChatGpt_limit = ?, chatgptlimittype = ? WHERE user_id = ?",(limit,"modified",user))
        self.conn.commit()

    def set_gpt_limit(self,limit):
        self.cursor.execute("UPDATE users SET ChatGpt_limit = ? WHERE chatgptlimittype = ?",(limit,"default"))
        self.cursor.execute("UPDATE admin SET chatgpt_limit = ?",(limit,))
        self.conn.commit()

    def get_gpt_limit(self):
        self.cursor.execute("SELECT chatgpt_limit FROM admin")
        data = self.cursor.fetchone()[0]
        return data
    
    def update_password_users(self,email,password):
        self.cursor.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (password, email)
        )

        self.conn.commit()

    def update_password_admin(self,email,password):
        self.cursor.execute(
            "UPDATE admin SET password = ? WHERE email = ?",
            (password, email)
        )

        self.conn.commit()

    def delete_user(self, email):
        try:
            print("Deleting user: ",email)
            # Delete the user with the specified email
            self.cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            print(f"An error occurred: {e}")

        

        
    