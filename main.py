from flask import Flask , render_template , url_for , redirect , request , session , flash
from datetime import datetime , timedelta
import mysql.connector 

app = Flask(__name__)
app.secret_key = 'hello'

#creating database and table
mycon = mysql.connector.connect(host = 'localhost', user ='root', password = 'prachi07' )
cur = mycon.cursor()
cur.execute("CREATE DATABASE IF NOT EXISTS info_db")
cur.execute("USE info_db")
cur.execute("CREATE TABLE IF NOT EXISTS raw_info(id INT AUTO_INCREMENT PRIMARY KEY , Name VARCHAR(50) NOT NULL  , Amount INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
cur.execute("CREATE TABLE IF NOT EXISTS splitted_info(id INT AUTO_INCREMENT PRIMARY KEY , Get_NAME VARCHAR(50) NOT NULL, Give_NAME VARCHAR(50) NOT NULL, Give_AMOUNT INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP) ")
cur.execute("CREATE TABLE IF NOT EXISTS raw_history(Name VARCHAR(50) NOT NULL  , Amount INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
cur.execute("CREATE TABLE IF NOT EXISTS splitted_history(Get_NAME VARCHAR(50) NOT NULL, Give_NAME VARCHAR(50) NOT NULL, Give_AMOUNT INT NOT NULL , Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP) ")
mycon.commit()


#home page
@app.route('/')
@app.route('/home/')
def home():
    return render_template('home.html')

#login page
@app.route('/login/', methods = ['POST','GET'])
def login():
    if session.get('logged_in'):
        flash("You're already logged in. Please logout before logging in again.", "warning")
        return redirect(url_for('home'))
    
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
            cur.execute("INSERT INTO raw_info VALUES (%s , %s , %s, %s )" , (id , name , amount, now))
            cur.execute("INSERT INTO raw_history VALUES (%s , %s, %s )" , (name , amount, now))
            id+=1  
        mycon.commit()
        session['logged_in'] = True
        return redirect(url_for('splitted_info'))
            
    else:
        return render_template('login.html')

#Raw info page
@app.route('/raw_info/')
def raw_info():
    cur.execute("SELECT * FROM raw_info")  
    info = cur.fetchall()  #it gives list of tuples containing one value
    if info == []:
        flash("No raw data found. Please enter some info first.", "warning")
        return redirect(url_for('login'))
    return render_template('raw_info.html' , info=info)


#Splitted info page
@app.route('/splitted_info/')
def splitted_info():
    try:
    #splitting 
        cur.execute("DELETE FROM splitted_info")
        mycon.commit()
        cur.execute("SELECT Name , Amount FROM raw_info ")  
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
                    cur.execute("INSERT INTO splitted_info VALUES (%s , %s , %s , %s, %s)" , (id, k, row[0], row[1], now))
                    cur.execute("INSERT INTO splitted_history VALUES (%s , %s , %s, %s)" , (k, row[0], row[1], now))
                    id += 1
        mycon.commit()
        cur.execute("SELECT * FROM splitted_info")
        info = cur.fetchall()
        return render_template('splitted_info.html', info=info ,total = total , splitted_amount = average)
    
    except ZeroDivisionError:
        flash("No data available to split. Please enter info first.", "danger")
        return redirect(url_for('login'))
    
#history page
@app.route('/history/')
def history():
    return render_template('history.html')

@app.route('/history/raw/')
def raw_history():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cur.execute("SELECT * FROM raw_history WHERE Timestamp >= %s", (thirty_days_ago,))
    raw_history = cur.fetchall()
    if not raw_history:
        flash("No raw history found in the last 30 days.", "info")
    return render_template('raw_history.html', raw=raw_history)

@app.route('/history/split/')
def splitted_history():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    cur.execute("SELECT * FROM splitted_history WHERE Timestamp >= %s", (thirty_days_ago,))
    split_history = cur.fetchall()
    if not split_history:
        flash("No split history found in the last 30 days.", "info")
    return render_template('splitted_history.html', split=split_history)

@app.route('/history/delete')
def delete_history():
    cur.execute('DELETE FROM raw_history')
    cur.execute('DELETE FROM splitted_history')
    mycon.commit()
    return render_template('delete_history.html')


#logout page
@app.route('/logout')
def logout():
    cur.execute('DELETE FROM raw_info')
    cur.execute('DELETE FROM splitted_info')
    mycon.commit()  
    session.pop('logged_in', None)
    return render_template('logout.html')

if __name__ == '__main__':
    app.run(debug = True) 