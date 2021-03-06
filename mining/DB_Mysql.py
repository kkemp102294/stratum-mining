import time
import hashlib
import lib.settings as settings
import lib.logger
log = lib.logger.get_logger('DB_Mysql')

import MySQLdb
                
class DB_Mysql():
    def __init__(self):
        log.debug("Connecting to DB")
        
        required_settings = ['PASSWORD_SALT', 'DB_MYSQL_HOST', 
                             'DB_MYSQL_USER', 'DB_MYSQL_PASS', 
                             'DB_MYSQL_DBNAME','DB_MYSQL_PORT']
        
        for setting_name in required_settings:
            if not hasattr(settings, setting_name):
                raise ValueError("%s isn't set, please set in config.py" % setting_name)
        
        self.salt = getattr(settings, 'PASSWORD_SALT')
        self.connect()
        
    def connect(self):
        self.dbh = MySQLdb.connect(
            getattr(settings, 'DB_MYSQL_HOST'), 
            getattr(settings, 'DB_MYSQL_USER'),
            getattr(settings, 'DB_MYSQL_PASS'), 
            getattr(settings, 'DB_MYSQL_DBNAME'),
            getattr(settings, 'DB_MYSQL_PORT')
        )
        self.dbc = self.dbh.cursor()
        self.dbh.autocommit(True)
            
    def execute(self, query, args=None):
        try:
            self.dbc.execute(query, args)
        except MySQLdb.OperationalError:
            log.debug("MySQL connection lost during execute, attempting reconnect")
            self.connect()
            self.dbc = self.dbh.cursor()
            
            self.dbc.execute(query, args)
            
    def executemany(self, query, args=None):
        try:
            self.dbc.executemany(query, args)
        except MySQLdb.OperationalError:
            log.debug("MySQL connection lost during executemany, attempting reconnect")
            self.connect()
            self.dbc = self.dbh.cursor()
            
            self.dbc.executemany(query, args)
    
        
    def list_users(self):
        self.execute(
            """
            SELECT *
            FROM `pool_worker`
            WHERE `id`> 0
            """
        )
        
        while True:
            results = self.dbc.fetchmany()
            if not results:
                break
            
            for result in results:
                yield result
                
                
    def get_user(self, id_or_username):
        log.debug("Finding user with id or username of %s", id_or_username)
        
        self.execute(
            """
            SELECT *
            FROM `pool_worker`
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        user = self.dbc.fetchone()
        return user

    def get_uid(self, id_or_username):
        log.debug("Finding user id of %s", id_or_username)
        uname = id_or_username.split(".", 1)[0]
        self.execute("SELECT `id` FROM `accounts` where username = %s", (uname))
        row = self.dbc.fetchone()

        if row is None:
            return False
        else:
            uid = row[0]
            return uid

    def insert_worker(self, account_id, username, password):
        log.debug("Adding new worker %s", username)
        query = "INSERT INTO pool_worker"
        self.execute(query + '(account_id, username, password) VALUES (%s, %s, %s);', (account_id, username, password))
        self.dbh.commit()
        return str(username)
        

    def delete_user(self, id_or_username):
        if id_or_username.isdigit() and id_or_username == '0':
            raise Exception('You cannot delete that user')
        
        log.debug("Deleting user with id or username of %s", id_or_username)
        
        self.execute(
            """
            UPDATE `shares`
            SET `username` = 0
            WHERE `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        self.execute(
            """
            DELETE FROM `pool_worker`
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """, 
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username
            }
        )
        
        self.dbh.commit()

    def insert_user(self, username, password):
        log.debug("Adding new user %s", username)
        
        self.execute(
            """
            INSERT INTO `pool_worker`
            (`username`, `password`)
            VALUES
            (%(uname)s, %(pass)s)
            """,
            {
                "uname": username, 
                "pass": password
            }
        )
        
        self.dbh.commit()
        
        return str(username)

    def update_user(self, id_or_username, password):
        log.debug("Updating password for user %s", id_or_username);
        
        self.execute(
            """
            UPDATE `pool_worker`
            SET `password` = %(pass)s
            WHERE `id` = %(id)s
              OR `username` = %(uname)s
            """,
            {
                "id": id_or_username if id_or_username.isdigit() else -1,
                "uname": id_or_username,
                "pass": password
            }
        )
        
        self.dbh.commit()

    def check_password(self, username, password):
        log.debug("Checking username/password for %s", username)
        
        self.execute(
            """
            SELECT COUNT(*) 
            FROM `pool_worker`
            WHERE `username` = %(uname)s
              AND `password` = %(pass)s
            """,
            {
                "uname": username, 
                "pass": password
            }
        )
        
        data = self.dbc.fetchone()
        if data[0] > 0:
            return True
        
        return False

    def get_workers_stats(self):
        self.execute(
            """
            SELECT `username`, `speed`, `last_checkin`, `total_shares`,
              `total_rejects`, `total_found`, `alive`
            FROM `pool_worker`
            WHERE `id` > 0
            """
        )
        
        ret = {}
        
        for data in self.dbc.fetchall():
            ret[data[0]] = {
                "username": data[0],
                "speed": int(data[1]),
                "last_checkin": time.mktime(data[2].timetuple()),
                "total_shares": int(data[3]),
                "total_rejects": int(data[4]),
                "total_found": int(data[5]),
                "alive": True if data[6] is 1 else False,
            }
            
        return ret
    def get_uid(self, id_or_username):
        log.debug("Finding user id of %s", id_or_username)
        uname = id_or_username.split(".", 1)[0]
        self.execute("SELECT `id` FROM `accounts` where username = %s", (uname))
        row = self.dbc.fetchone()
        
       
        if row is None:
            return False
        else:
            uid = row[0]
            return uid
    
    
    def insert_worker(self, account_id, username, password):
        log.debug("Adding new worker %s", username)
        query = "INSERT INTO pool_worker"
        self.execute(query + '(account_id, username, password) VALUES (%s, %s, %s);', (account_id, username, password))
        self.dbh.commit()
        return str(username)
        


    def close(self):
        self.dbh.close()

    def check_tables(self):
        log.debug("Checking Database")
        
        self.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE `table_schema` = %(schema)s
              AND `table_name` = 'shares'
            """,
            {
                "schema": getattr(settings, 'DB_MYSQL_DBNAME')
            }
        )
        
        data = self.dbc.fetchone()
        
        if data[0] <= 0:
           raise Exception("There is no shares table. Have you imported the schema?")
 

