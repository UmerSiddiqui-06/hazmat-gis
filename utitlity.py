import sqlite3

class sqlpy:
    def __init__(self):
        self.conn = sqlite3.connect('my_database.db')
        self.cursor = self.conn.cursor()

        # Create the users table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR(255),
                email VARCHAR(255),  
                password VARCHAR(255),
                status VARCHAR(255)
                );""")

        # Create the admin table
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS admin (
                email VARCHAR(255),
                password VARCHAR(255)
                );""")
        
        # Insert temporary user record
        self.cursor.execute('SELECT * FROM users')
        data = self.cursor.fetchone()
        if not data:
            self.cursor.execute("INSERT INTO users (user_id,email,password,status) VALUES(?,?,?,?)",('u1','temp','0000','Accepted'))

        # Insert admin record
        self.cursor.execute('SELECT * FROM admin')
        data = self.cursor.fetchone()
        if not data:
            self.cursor.execute("INSERT INTO admin (email, password) VALUES (?, ?)", ('admin', '0000'))
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

        self.cursor.execute('INSERT INTO users (user_id,email,password,status) VALUES (?,?,?,?)',(id,email,password,'Pending'))
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
            return data[3]
        
    def get_users(self):
        self.cursor.execute("SELECT * FROM users")
        data = self.cursor.fetchall()
        return data
    
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


        

        
        

        
    