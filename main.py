from flask import Flask , render_template , url_for , redirect , request , session , flash
from datetime import datetime , timedelta
import mysql.connector 

app = Flask(__name__)
app.secret_key = 'hello'

#creating database and table
mycon = mysql.connector.connect(host = 'localhost', user ='root', password = 'prachi07' )
cur = mycon.cursor()


#home page
@app.route('/')
@app.route('/home/')
def home():
    return render_template('home.html')


#login page
@app.route('/login/', methods = ['POST','GET'])
def login():     
    cur.execute("USE signin_db")
    if request.method == 'POST':
        user = request.form.get('user', '').strip()
        password = request.form.get('password', '').strip()

        cur.execute("SELECT Password FROM signin WHERE UserName = %s", (user,))
        result = cur.fetchone()

        if result and result[0] == password:
            session['logged_in'] = True
            session['user'] = user
            flash("Login successful!", "success")

            try:
                user = session.get('user')
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{user}_info_db`")
                cur.execute(f"USE `{user}_info_db`")
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{user}_raw_info`(id INT PRIMARY KEY , Name VARCHAR(50) NOT NULL  , Amount INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{user}_splitted_info`(id INT AUTO_INCREMENT PRIMARY KEY , Get_NAME VARCHAR(50) NOT NULL, Give_NAME VARCHAR(50) NOT NULL, Give_AMOUNT INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP) ")
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{user}_raw_history`(Name VARCHAR(50) NOT NULL  , Amount INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
                cur.execute(f"CREATE TABLE IF NOT EXISTS `{user}_splitted_history`(Get_NAME VARCHAR(50) NOT NULL, Give_NAME VARCHAR(50) NOT NULL, Give_AMOUNT INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP) ")
                mycon.commit()
            except mysql.connector.Error as err:
                flash(f"Error creating database for user: {err}", "danger")
            return redirect(url_for('options'))
        
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))
        
    else:
        return render_template('login.html')


#creating database and table for signin info
cur.execute("CREATE DATABASE IF NOT EXISTS signin_db")
cur.execute("USE signin_db")
cur.execute("CREATE TABLE IF NOT EXISTS signin (UserName VARCHAR(50) NOT NULL UNIQUE  , Password VARCHAR(20) NOT NULL)")


#signin page
@app.route('/login/signin/' , methods = ['POST','GET'])
def signin():
    cur.execute("USE signin_db")
    if request.method == 'POST':
        user = request.form['user']
        password = request.form['password']
        
        cur.execute("SELECT * FROM signin WHERE UserName = %s", (user,))
        existing_user = cur.fetchone()

        if existing_user :
            flash("User already exists. Please login.", "warning")
            return redirect(url_for('login'))
        
        cur.execute("INSERT INTO signin VALUES (%s , %s)" , (user , password))
        mycon.commit()

        flash("Signup successful. Please login.", "success")
        return redirect(url_for('login'))
    
    else:
        return render_template('signin.html')


#options page
@app.route('/options')
def options():
    return render_template('options.html')


#splitData input page
@app.route('/splitData/', methods = ['POST','GET'])
def split_data():
    if not session.get('logged_in'):
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    
    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")
    
    if request.method == 'POST':
        form_data = request.form.items()
        names = []
        amounts = []
        id = 1
        
        for key, value in form_data:
            if key.startswith('name'):
                index = key.replace('name', '')
                name = value.strip()
                amount = request.form.get(f'amount{index}')
                if name and amount:
                    try:
                        amounts.append(int(amount))
                        names.append(name)
                    except ValueError:
                        flash(f"Invalid amount for {name}", "warning")
                else:
                    flash("Please fill in both name and amount fields.", "warning")

        for name,amount in zip(names,amounts):
            now = datetime.now()
            cur.execute(f"INSERT INTO `{user}_raw_info` (id , Name, Amount, Timestamp) VALUES (%s, %s, %s, %s)", (id , name, amount, now))
            cur.execute(f"INSERT INTO `{user}_raw_history` VALUES (%s , %s, %s )" , (name , amount, now))
            id += 1
      
        mycon.commit()
        return redirect(url_for('splitted_info'))
    else:
        return render_template('split_data.html')


#Raw info page
@app.route('/raw_info/')
def raw_info():
    if not session.get('logged_in'):
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    
    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    cur.execute(f"SELECT * FROM `{user}_raw_info`")  
    info = cur.fetchall()  #it gives list of tuples containing one value
    if info == []:
        flash("No raw data found. Please enter some info first.", "warning")
        return redirect(url_for('login'))
    return render_template('raw_info.html' , info=info)


#Splitted info page
@app.route('/splitted_info/')
def splitted_info():
    if not session.get('logged_in'):
        flash("Please login first.", "warning")
        return redirect(url_for('login'))
    
    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    try:
    #splitting 
        cur.execute(f"DELETE FROM `{user}_splitted_info`")
        mycon.commit()
        cur.execute(f"SELECT Name , Amount FROM `{user}_raw_info` ")  
        name_amount_fetched = cur.fetchall()  #it gives list of tuples containing one value
        
        name_amount = [[row[0],row[1]] for row in name_amount_fetched]

        amnts = [row[1] for row in name_amount]

        total = sum(amnts)
        average = total / (len(amnts))

        get_money = []
        give_money = []
        for row in name_amount:
            temp=[]
            diff = row[1] - average

            if diff>0:
                temp = [row[0] , diff]
                get_money.append(temp)
                
            elif diff<0:
                temp = [row[0] , abs(diff)]
                give_money.append(temp)

            else:
                continue

        money_exchange = {}

        for get in get_money:
            temp = []
            for give in give_money:
                
                if give[1]!=0 and get[1]!=0:
                    
                    if give[1] < get[1]:
                        temp.append([give[0] , give[1]])
                        money_exchange[get[0]] = temp
                        give[1] = 0
                        get[1] = get[1]-give[1]
                            
                    elif give[1] > get[1]:
                        temp.append([give[0] , get[1]])
                        money_exchange[get[0]] = temp
                        give[1] = give[1]-get[1]
                        get[1] = 0
                        
                    else:
                        money_exchange[get[0]] = [[give[0], give[1]]]
                        give[1] = 0
                        get[1] = 0

        id = 1
        for k in money_exchange:
            for row in money_exchange[k]:
                if isinstance(row, (list, tuple)) and len(row) == 2:
                    now = datetime.now()
                    cur.execute(f"INSERT INTO `{user}_splitted_info` VALUES (%s , %s , %s , %s, %s)" , (id, k, row[0], row[1], now))
                    cur.execute(f"INSERT INTO `{user}_splitted_history` VALUES (%s , %s , %s, %s)" , (k, row[0], row[1], now))
                    id += 1
        mycon.commit()
        cur.execute(f"SELECT * FROM `{user}_splitted_info`")
        info = cur.fetchall()
        return render_template('splitted_info.html', info=info ,total = total , splitted_amount = average)
    
    except ZeroDivisionError:
        flash("No data available to split. Please enter info first.", "danger")
        return redirect(url_for('login'))
    


#history page
@app.route('/history/')
def history():
    return render_template('history.html')

#raw history
@app.route('/history/raw/')
def raw_history():
    if not session.get('logged_in'):
        flash("Please login first to view raw history.", "warning")
        return redirect(url_for('login'))

    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    thirty_days_ago = datetime.now() - timedelta(days=30)
    cur.execute(f"SELECT * FROM `{user}_raw_history` WHERE Timestamp >= %s", (thirty_days_ago,))
    raw_history = cur.fetchall()

    if not raw_history:
        flash("No raw history found in the last 30 days.", "info")
    return render_template('raw_history.html', raw=raw_history)

#splitted history
@app.route('/history/split/')
def splitted_history():
    if not session.get('logged_in'):
        flash("Please login first to view raw history.", "warning")
        return redirect(url_for('login'))

    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    thirty_days_ago = datetime.now() - timedelta(days=30)
    cur.execute(f"SELECT * FROM `{user}_splitted_history` WHERE Timestamp >= %s", (thirty_days_ago,))
    split_history = cur.fetchall()

    if not split_history:
        flash("No split history found in the last 30 days.", "info")
    return render_template('splitted_history.html', split=split_history)

#delete history
@app.route('/history/delete')
def delete_history():
    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    cur.execute(f'DELETE FROM `{user}_raw_history`')
    cur.execute(f'DELETE FROM `{user}_splitted_history`')
    mycon.commit()

    return render_template('delete_history.html')


#logout page
@app.route('/logout')
def logout():
    user = session.get('user')
    cur.execute(f"USE `{user}_info_db`")

    cur.execute(f'DELETE FROM `{user}_raw_info`')
    cur.execute(f'DELETE FROM `{user}_splitted_info`')
    mycon.commit()  
    session.clear()
    return render_template('logout.html')


#signout / delete account page
@app.route('/signout')
def signout():
    user = session.get('user')
    cur.execute("USE signin_db")
    cur.execute('DELETE FROM signin WHERE UserName = %s', (user,))
    cur.execute(f"DROP database `{user}_info_db`")
    mycon.commit()  
    session.clear()
    return render_template('signout.html')


if __name__ == '__main__':
    app.run(debug = True) 