import sqlite3
from datetime import datetime,timedelta

class sqlpy:
    def __init__(self):
        self.conn = sqlite3.connect('my_database.db',check_same_thread=False)
        self.cursor = self.conn.cursor()

        # Create the users table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(255),
                email VARCHAR(255),  
                password VARCHAR(255),
                chatgpt BOOL,
                status VARCHAR(255),
                ChatGpt_used INTEGER,
                ChatGpt_limit INTEGER,
                remaining_time DATETIME
                );""")

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
        
        # Insert temporary user record
        self.cursor.execute('SELECT * FROM users')
        data = self.cursor.fetchone()
        if not data:
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,remaining_time,ChatGpt_limit) VALUES(?,?,?,?,?,?,?,?)",('u1','temp','0000',0,'Accepted',0,None,5))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,remaining_time,ChatGpt_limit) VALUES(?,?,?,?,?,?,?,?)",('u2','temp1','0000',1,'Pending',0,None,5))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,remaining_time,ChatGpt_limit) VALUES(?,?,?,?,?,?,?,?)",('u3','temp2','0000',1,'Rejected',0,None,5))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,remaining_time,ChatGpt_limit) VALUES(?,?,?,?,?,?,?,?)",('u4','temp3','0000',1,'Accepted',4,None,5))
            self.cursor.execute("INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,remaining_time,ChatGpt_limit) VALUES(?,?,?,?,?,?,?,?)",('u5','temp4','0000',1,'Accepted',5,datetime.now()-timedelta(days=40),5))

        # Insert admin record
        self.cursor.execute('SELECT * FROM admin')
        data = self.cursor.fetchone()
        if not data:
            self.cursor.execute("INSERT INTO admin (email, password, chatgpt, chatgpt_limit) VALUES (?, ?, ?, ?)", ('admin', '0000',1,5))
        self.conn.commit()

    def get_status(self,email):
        query = "SELECT status FROM users WHERE email = ?"
        self.cursor.execute(query,(email,))
        data = self.cursor.fetchone()
        if data:
            return data[0]
        else:
            return None
        
    def register_user(self,email,password):
        self.cursor.execute("SELECT MAX(CAST(SUBSTR(user_id, 2) AS INTEGER)) FROM users")
        data = self.cursor.fetchone()
        if data[0] is None:
            id = 'u1'
        else:
            id = 'u' + str(data[0] + 1)
        global_gpt = self.get_gpt_limit()
        self.cursor.execute('INSERT INTO users (user_id,email,password,chatgpt,status,ChatGpt_used,ChatGpt_limit) VALUES (?,?,?,?,?,?,?)',(id,email,password,0,'Pending',0,global_gpt))
        self.conn.commit()

    def check_login_admin(self,email,password):
        self.cursor.execute('SELECT * FROM admin WHERE email = ? and password = ?',(email,password))
        data = self.cursor.fetchone()
        if data:
            return 'admin'
        else:
            return None
    def check_login_user(self,email,password):
        self.cursor.execute("SELECT * FROM users WHERE email = ? and password = ?",(email,password))
        data = self.cursor.fetchone()
        if not data:
            return None
        else:
            return data[4]
        
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
        self.cursor.execute('UPDATE users SET chatgpt = ? WHERE user_id = ?',(chatgpt,id))
        self.conn.commit()

    def get_user_gpt_status(self,email):
        self.cursor.execute('SELECT chatgpt FROM users WHERE email = ?',(email,))
        chatgpt = self.cursor.fetchone()[0]
        return chatgpt
    
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
                self.cursor.execute("SELECT remaining_time FROM users WHERE email = ?",(user,))
                old_date = self.cursor.fetchone()[0]
                new_date = datetime.now()
                difference = new_date - datetime.strptime(old_date, "%Y-%m-%d %H:%M:%S.%f")
                if difference.days >= 30:
                    self.cursor.execute("UPDATE users SET ChatGpt_used = ? , remaining_time = ? WHERE email = ?",(0,None,user))
                    self.conn.commit()
                    return True
                else:
                    return False
            return False
        
    def increase_gpt(self,user):
        self.cursor.execute("SELECT ChatGpt_used FROM users WHERE email = ?",(user,))
        times = self.cursor.fetchone()[0]
        times = times+1
        self.cursor.execute("SELECT ChatGpt_limit FROM users WHERE email = ?",(user,))
        limit = self.cursor.fetchone()[0]
        if times == limit:
            remaining_time = datetime.now()
        else:
            remaining_time = None
        self.cursor.execute("UPDATE users SET ChatGpt_used = ? , remaining_time = ? WHERE email = ?",(times,remaining_time,user))
        self.conn.commit()

    def increase_gpt_limit(self,user,limit):
        self.cursor.execute("UPDATE users SET ChatGpt_limit = ? WHERE user_id = ?",(limit,user))
        self.conn.commit()

    def set_gpt_limit(self,limit):
        # self.cursor.execute("UPDATE users SET ChatGpt_limit = ?",(limit,))
        self.cursor.execute("UPDATE admin SET chatgpt_limit = ?",(limit,))
        self.conn.commit()

    def get_gpt_limit(self):
        self.cursor.execute("SELECT chatgpt_limit FROM admin")
        data = self.cursor.fetchone()[0]
        return data
    

        

        
        

        
    