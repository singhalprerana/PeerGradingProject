# all the imports
import sqlite3, datetime, os
from contextlib import closing
from flask import Flask, jsonify, request, session, g, redirect, url_for, \
     abort, render_template, flash, make_response
from werkzeug import secure_filename
from flask.ext.httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()
auth2 = HTTPBasicAuth()
from collections import Counter

# configuration
DATABASE = 'flaskapp.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'password'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = set(['txt', 'csv'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.route('/')
def show_entries():
    cur = g.db.execute('select title, text, time from entries order by id desc')
    entries = [dict(title=row[0], text=row[1], datetime=row[2]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)

@auth.get_password
def get_password(username):
    cur = g.db.execute('select * from users where authorization="instructor"')
    passwords = {}
    for row in cur.fetchall():
        passwords[row[0]] = row[1]
    if username in passwords:
        return passwords[username]
    else:
        return None

@auth2.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)

@auth2.get_password
def get_password(username):
    cur = g.db.execute('select * from users where authorization="admin"')
    passwords = {}
    for row in cur.fetchall():
        passwords[row[0]] = row[1]
    if username in passwords:
        return passwords[username]
    else:
        return None

@app.route('/uploadfiles', methods=['GET', 'POST'])
def uploadfiles():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.replace('\n','')
                    words = line.split(',')
                    words = [i.strip() for i in words]
                    cur2 = g.db.execute('insert into users values (?,?,?)', [words[0], words[1], words[2]])
                    g.db.commit()
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return '''
            <!doctype html>
            <title>Bulk Loading Successful.</title>
            <h1>Bulk Loading Successful.</h1>
             <a href="http://localhost:5000/">BACK</a>
            '''

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/api/download_grades/', methods=['GET'])
@auth.login_required
def api_download_grades():
    data = []
    cur2 = g.db.execute('select receiver, grader, grades from tasks natural join grades where creator = ?', [auth.username()])
    for row in cur2.fetchall():
        data.append({ 'to':row[0], 'by': row[1], 'grades': row[2]})
    return jsonify({'grades': data})


@app.route('/api/download_userinfo/', methods=['GET'])
@auth2.login_required
def api_download_userinfo():
    data = []
    cur2 = g.db.execute('select * from users')
    for row in cur2.fetchall():
        data.append({ 'username':row[0], 'password': row[1], 'privilege': row[2]})
    return jsonify({'users': data})

@app.route('/api/add_users/', methods=['POST'])
@auth2.login_required
def api_add_users():
    if not request.json:
        abort(400)
    cur2 = g.db.execute('insert into users values (?,?,?)', [request.json['username'], request.json['password'], request.json['authorization']])
    g.db.commit()
    return jsonify({'user': request.json})

@app.route('/api/add_grades/', methods=['POST'])
@auth.login_required
def api_add_grades():
    if not request.json:
        abort(400)
    cur2 = g.db.execute('insert into grades values (?,?,?,?,?)', [request.json['taskname'], request.json['grader'], request.json['receiver'], request.json['grades'], request.json['review']])
    g.db.commit()
    return jsonify({'grades': request.json})

@app.route('/grading_stats')
def grading_stats():
    cur = g.db.execute('select taskname, grader, receiver, grades, review from tasks natural join grades where creator = ? and not grader = ? order by grades.taskname, receiver, grader',[session['name'],session['name']])
    entries = [row for row in cur.fetchall()]
    #print entries
    cur1 = g.db.execute('select taskname, receiver, grades, review from grades where grader = ? order by grades.taskname, receiver',[session['name']])
    entries1 = [row for row in cur1.fetchall()]
    #print entries1

    with open('grade_config.txt') as f:
        grades = f.readlines()
    grades=[row.strip('\n') for row in grades]
    num={}
    num['']=0
    l=len(grades)
    for i in range(l):
        num[grades[i]]=l-i

    xx=[[row[0],row[1]] for row in entries1]
    for row in entries:
        if [row[0],row[2]] not in xx:
            entries1.append((row[0],row[2],'','',))

    for j in range(len(entries1)):
        count=0
        sm=0
        for i in range(len(entries)):
            if entries[i][0]==entries1[j][0] and entries[i][2]==entries1[j][1]:
                count+=1
                sm+=num[entries[i][3]]
        if count>0:
            sm=round(float(sm)/float(count))
            #print j,entries1[j]
            entries1[j]=entries1[j]+(grades[int(l-sm)],)
        else:
            entries1[j]=entries1[j]+('',)
    #print entries
    #print entries1

    cur2=g.db.execute('select taskname, weight from tasks where creator = ?',[session['name']])
    wts = [row for row in cur2.fetchall()]
    total_wt=sum([row[1] for row in wts])
    #print 'Total Weight',total_wt

    dict_w={}
    for row in wts:
        dict_w[row[0]]=int(row[1])
    entry_dict={}
    for row in entries1:
        if row[1] not in entry_dict:
            entry_dict[row[1]]=dict_w[row[0]]*num[row[2]]
        else:
            entry_dict[row[1]]+=dict_w[row[0]]*num[row[2]]

    entries2=[]
    for key in entry_dict:
        x=int(l-round(float(entry_dict[key])/float(total_wt)))
        if x>l-1:
            x=l-1
        if x<0:
            x=0
        entries2.append([key,grades[x]])
    cur3=g.db.execute('select username from users where authorization = \'student\'')
    studs=[row[0] for row in cur3.fetchall()]
    ent_studs=[row[0] for row in entries2]
    for s in studs:
        if s not in ent_studs:
            entries2.append([s,grades[l-1]])
    #print entries2

    gds = Counter([row[1] for row in entries2])
    grads=[0]*len(grades)
    for i in range(len(grades)):
        if grades[i] in gds:
            grads[i]=[grades[i],gds[grades[i]]]
        else:
            grads[i]=[grades[i],0]

    task_wise_grades = {}
    for row in entries1:
        if row[0] in task_wise_grades:
            task_wise_grades[row[0]].append(row[2])
        else:
            task_wise_grades[row[0]] = []
            task_wise_grades[row[0]].append(row[2])

    for key in task_wise_grades:
        xx=Counter(task_wise_grades[key])
        task_wise_grades[key]=[0]*len(grades)
        for i in range(len(grades)):
            if grades[i] in xx:
                task_wise_grades[key][i]=[grades[i],xx[grades[i]]]
            else:
                task_wise_grades[key][i]=[grades[i],0]
    return render_template('grading_stats.html', grades=grads, twg = task_wise_grades)

@app.route('/download')
def download():
    csv="STUDENT, GRADE\n"
    cur = g.db.execute('select grades.taskname, grader, receiver, grades, review from tasks natural join grades where creator = ? and not grader = ? order by grades.taskname, receiver, grader',[session['name'],session['name']])
    entries = [row for row in cur.fetchall()]
    #print entries
    cur1 = g.db.execute('select taskname, receiver, grades, review from grades where grader = ? order by grades.taskname, receiver',[session['name']])
    entries1 = [row for row in cur1.fetchall()]
    #print entries1

    with open('grade_config.txt') as f:
        grades = f.readlines()
    grades=[row.strip('\n') for row in grades]
    num={}
    num['']=0
    l=len(grades)
    for i in range(l):
        num[grades[i]]=l-i

    xx=[[row[0],row[1]] for row in entries1]
    for row in entries:
        if [row[0],row[2]] not in xx:
            entries1.append((row[0],row[2],'','',))

    for j in range(len(entries1)):
        count=0
        sm=0
        for i in range(len(entries)):
            if entries[i][0]==entries1[j][0] and entries[i][2]==entries1[j][1]:
                count+=1
                sm+=num[entries[i][3]]
        if count>0:
            sm=round(float(sm)/float(count))
            #print j,entries1[j]
            entries1[j]=entries1[j]+(grades[int(l-sm)],)
        else:
            entries1[j]=entries1[j]+('',)
    #print entries
    #print entries1

    cur2=g.db.execute('select taskname, weight from tasks where creator = ?',[session['name']])
    wts = [row for row in cur2.fetchall()]
    total_wt=sum([row[1] for row in wts])
    #print 'Total Weight',total_wt

    dict_w={}
    for row in wts:
        dict_w[row[0]]=int(row[1])
    entry_dict={}
    for row in entries1:
        if row[1] not in entry_dict:
            entry_dict[row[1]]=dict_w[row[0]]*num[row[2]]
        else:
            entry_dict[row[1]]+=dict_w[row[0]]*num[row[2]]

    entries2=[]
    for key in entry_dict:
        x=int(l-round(float(entry_dict[key])/float(total_wt)))
        if x>l-1:
            x=l-1
        if x<0:
            x=0
        entries2.append([key,grades[x]])
    cur3=g.db.execute('select username from users where authorization = \'student\'')
    studs=[row[0] for row in cur3.fetchall()]
    ent_studs=[row[0] for row in entries2]
    for s in studs:
        if s not in ent_studs:
            entries2.append([s,grades[l-1]])
    #print entries2

    for row in entries2:
        string = str(row[0])+","+str(row[1])+"\n"
        csv = csv+string
    response = make_response(csv)
    response.headers["Content-Disposition"] = "attachment; filename=result.csv"
    return response

@app.route('/show_all_grades')
def show_all_grades():
    cur = g.db.execute('select grades.taskname, grader, receiver, grades, review from tasks natural join grades where creator = ? and not grader = ? order by grades.taskname, receiver, grader',[session['name'],session['name']])
    entries = [row for row in cur.fetchall()]
    #print entries
    cur1 = g.db.execute('select taskname, receiver, grades, review from grades where grader = ? order by grades.taskname, receiver',[session['name']])
    entries1 = [row for row in cur1.fetchall()]
    #print entries1

    with open('grade_config.txt') as f:
        grades = f.readlines()
    grades=[row.strip('\n') for row in grades]
    num={}
    num['']=0
    l=len(grades)
    for i in range(l):
        num[grades[i]]=l-i

    xx=[[row[0],row[1]] for row in entries1]
    for row in entries:
        if [row[0],row[2]] not in xx:
            entries1.append((row[0],row[2],'','',))

    for j in range(len(entries1)):
        count=0
        sm=0
        for i in range(len(entries)):
            if entries[i][0]==entries1[j][0] and entries[i][2]==entries1[j][1]:
                count+=1
                sm+=num[entries[i][3]]
        if count>0:
            sm=round(float(sm)/float(count))
            #print j,entries1[j]
            entries1[j]=entries1[j]+(grades[int(l-sm)],)
        else:
            entries1[j]=entries1[j]+('',)
    #print entries
    #print entries1

    cur2=g.db.execute('select taskname, weight from tasks where creator = ?',[session['name']])
    wts = [row for row in cur2.fetchall()]
    total_wt=sum([row[1] for row in wts])
    #print 'Total Weight',total_wt

    dict_w={}
    for row in wts:
        dict_w[row[0]]=int(row[1])
    entry_dict={}
    for row in entries1:
        if row[1] not in entry_dict:
            entry_dict[row[1]]=dict_w[row[0]]*num[row[2]]
        else:
            entry_dict[row[1]]+=dict_w[row[0]]*num[row[2]]

    entries2=[]
    for key in entry_dict:
        x=int(l-round(float(entry_dict[key])/float(total_wt)))
        if x>l-1:
            x=l-1
        if x<0:
            x=0
        entries2.append([key,grades[x]])
    cur3=g.db.execute('select username from users where authorization = \'student\'')
    studs=[row[0] for row in cur3.fetchall()]
    ent_studs=[row[0] for row in entries2]
    for s in studs:
        if s not in ent_studs:
            entries2.append([s,grades[l-1]])
    #print entries2

    return render_template('show_all_grades.html', entries=entries, entries1=entries1, entries2=entries2, num=num)

@app.route('/grade_peers')
def grade_peers():
    cur = g.db.execute('select taskname from student_task where student = ?',[session['name']])
    rows=cur.fetchall()
    if len(rows)>0:
        entries = [row[0] for row in rows]
    else:
        entries=[]

    with open('grade_config.txt') as f:
        grades = f.readlines()
    grades=[row.strip('\n') for row in grades]
    #print grades

    cur = g.db.execute('select username from users where authorization=\'student\'')
    students=[row[0] for row in cur.fetchall()]

    return render_template('show_available_tasks.html', entries=entries, grades=grades, students=students)

@app.route('/add_grade', methods=['GET', 'POST'])
def add_grade():
    g.db.execute('delete from grades where taskname=? and grader=? and receiver=?',[request.form['task'], session['name'], request.form['receiver']])
    g.db.execute('insert into grades values (?, ?, ?, ?, ?)',
                 [request.form['task'], session['name'], request.form['receiver'], request.form['grade'],request.form['review']])
    g.db.commit()
    if session['name']=='instructor':
        return redirect(url_for('show_all_grades'))
    else:
        return redirect(url_for('grade_peers'))

@app.route('/manage_users')
def manage_users():
    #Use flask-mail.
    cur = g.db.execute('select * from users')
    entries = [dict(username=row[0], privilege=row[2]) for row in cur.fetchall()]
    return render_template('users.html', entries=entries)

@app.route('/grading_tasks')
def grading_tasks():
    cur = g.db.execute('select * from tasks where creator = ?', [session['name']])
    entries = [dict(taskname=row[0], creator=row[2], weight=row[1]) for row in cur.fetchall()]
    cur = g.db.execute('select * from users where authorization = \'student\'')
    students = [row[0] for row in cur.fetchall()]
    return render_template('grading_tasks.html', entries=entries, students=students)

@app.route('/add_task', methods=['POST'])
def add_task():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('insert into tasks values (?, ?, ?)',
                 [request.form['taskname'], int(request.form['weight']), session['name']])
    g.db.commit()
    participants = request.form.getlist('participants')
    for i in participants:
        g.db.execute('insert into student_task values (?, ?)',
                 [i.strip(), request.form['taskname']])
        g.db.commit()
    g.db.execute('insert into student_task values (?, ?)',
                 [session['name'], request.form['taskname']])
    g.db.commit()
    flash('New entry was successfully posted')
    cur = g.db.execute('select * from student_task')
    #print cur.fetchall()
    return redirect(url_for('grading_tasks'))

@app.route('/edit_weight', methods=['GET','POST'])
def edit_weight():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('update tasks set weight=? where taskname=? and creator=?',[request.form['wt'],request.args.get('task'),request.args.get('creator')])
    g.db.commit()
    flash('Entry was successfully updated')

    return redirect(url_for('grading_tasks'))

@app.route('/remove_task', methods=['GET','POST'])
def remove_task():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('delete from tasks where taskname = ?',[request.args.get('task')])
    g.db.commit()
    g.db.execute('delete from student_task where taskname = ?',[request.args.get('task')])
    g.db.commit()
    g.db.execute('delete from grades where taskname = ?',[request.args.get('task')])
    g.db.commit()
    flash('New entry was successfully posted')

    cur = g.db.execute('select * from student_task')
    #print cur.fetchall()
    return redirect(url_for('grading_tasks'))

@app.route('/block_task', methods=['GET','POST'])
def block_task():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('delete from student_task where taskname = ? and not student =?',[request.args.get('task'),session['name']])
    g.db.commit()
    flash('New entry was successfully posted')

    cur = g.db.execute('select * from student_task')
    #print cur.fetchall()
    return redirect(url_for('grading_tasks'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if not session.get('logged_in'):
        abort(401)
    if request.form['username']!='' and request.form['password']!='' and request.form['privilege'] in ['student','instructor','admin']:
        g.db.execute('insert into users values (?, ?, ?)',
                 [request.form['username'], request.form['password'], request.form['privilege']])
        g.db.commit()
        flash('New entry was successfully posted')
    else:
        flash('Error in entry. Try again.')
    return redirect(url_for('manage_users'))

@app.route('/delete_user', methods=['GET','POST'])
def delete_user():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('delete from users where username = ?',
                 [request.args.get('user')])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('manage_users'))

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('insert into entries (title, text, time) values (?, ?, ?)',
                 [session['name'], request.form['text'], datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y")])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    cur = g.db.execute('select * from users')
    rows = cur.fetchall()
    #print rows
    error = None
    if request.method == 'POST':
        cur = g.db.execute('select * from users where username = ? and password = ?',
                         [request.form['username'], request.form['password']])
        rows = cur.fetchall()
        if len(rows)>=1:
            session['logged_in'] = True
            session['name'] = request.form['username']
            session['privilege'] = rows[0][2];
            flash('You were logged in')
            return redirect(url_for('show_entries'))
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session['name'] = request.form['username']
            session['privilege'] = 'admin';
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('privilege', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == '__main__':
    init_db()
    app.run()
