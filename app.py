from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///brainboost.db'
db = SQLAlchemy(app)
from flask_migrate import Migrate
migrate = Migrate(app, db)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.Integer, default=3)
    tags = db.Column(db.String(200), default='')
    date = db.Column(db.DateTime, default=datetime.utcnow)

class CheckIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    water = db.Column(db.Boolean, default=False)
    exercise = db.Column(db.Boolean, default=False)
    meditation = db.Column(db.Boolean, default=False)
    sleep = db.Column(db.Boolean, default=False)

class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    emoji = db.Column(db.String(10), default='✅')

class HabitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    done = db.Column(db.Boolean, default=False)
    habit = db.relationship('Habit', backref='logs')

class Gratitude(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

quotes = [
    "Believe in yourself and all that you are.",
    "Every day is a second chance.",
    "You are stronger than you think.",
    "Small steps every day lead to big results.",
    "Your only limit is your mind.",
    "Be the energy you want to attract.",
    "Growth begins at the end of your comfort zone.",
    "You got this. One day at a time."
]

with app.app_context():
    db.create_all()
    if Habit.query.count() == 0:
        defaults = [
            Habit(name='Drink enough water', emoji='💧'),
            Habit(name='Exercise', emoji='🏃'),
            Habit(name='Meditate', emoji='🧘'),
            Habit(name='Sleep well', emoji='😴'),
        ]
        db.session.add_all(defaults)
        db.session.commit()

def get_streak():
    entries = Entry.query.order_by(Entry.date.desc()).all()
    if not entries:
        return 0
    
    streak = 0
    today = datetime.utcnow().date()
    check_date = today
    
    for entry in entries:
        entry_date = entry.date.date()
        if entry_date == check_date:
            streak += 1
            check_date -= __import__('datetime').timedelta(days=1)
        elif entry_date < check_date:
            break
    
    return streak

@app.route('/')
def home():
    quote = random.choice(quotes)
    streak = get_streak()
    today = datetime.utcnow().date()
    habits = Habit.query.all()
    logs_today = {log.habit_id: log.done for log in HabitLog.query.filter_by(date=today).all()}
    unchecked = [h for h in habits if not logs_today.get(h.id)]
    checked = [h for h in habits if logs_today.get(h.id)]
    return render_template('index.html', quote=quote, streak=streak, unchecked=unchecked, checked=checked)
    
@app.route('/journal', methods=['GET', 'POST'])
def journal():
    if request.method == 'POST':
        content = request.form['content']
        mood = int(request.form.get('mood', 3))
        tags = request.form.get('tags', '')
        entry = Entry(content=content, mood=mood, tags=tags)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('journal'))
    entries = Entry.query.order_by(Entry.date.desc()).all()
    return render_template('journal.html', entries=entries)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    results = Entry.query.filter(
        Entry.content.contains(query) | Entry.tags.contains(query)
    ).order_by(Entry.date.desc()).all()
    return render_template('search.html', results=results, query=query)

@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    today = datetime.utcnow().date()
    habits = Habit.query.all()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_habit':
            name = request.form.get('habit_name')
            emoji = request.form.get('habit_emoji', '✅')
            if name:
                habit = Habit(name=name, emoji=emoji)
                db.session.add(habit)
                db.session.commit()
        
        elif action == 'log':
            for habit in habits:
                log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
                done = str(habit.id) in request.form.getlist('habits')
                if log:
                    log.done = done
                else:
                    log = HabitLog(habit_id=habit.id, date=today, done=done)
                    db.session.add(log)
            db.session.commit()
        
        return redirect(url_for('checkin'))
    
    logs_today = {log.habit_id: log.done for log in HabitLog.query.filter_by(date=today).all()}
    
    history = {}
    past_logs = HabitLog.query.filter(HabitLog.date != today).order_by(HabitLog.date.desc()).all()
    for log in past_logs:
        if log.date not in history:
            history[log.date] = []
        if log.done:
            history[log.date].append(f"{log.habit.emoji} {log.habit.name}")
    
    return render_template('checkin.html', habits=habits, logs_today=logs_today, today=today, history=history)

@app.route('/quick_checkin/<int:habit_id>', methods=['POST'])
def quick_checkin(habit_id):
    today = datetime.utcnow().date()
    log = HabitLog.query.filter_by(habit_id=habit_id, date=today).first()
    if log:
        log.done = True
    else:
        log = HabitLog(habit_id=habit_id, date=today, done=True)
        db.session.add(log)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/gratitude', methods=['GET', 'POST'])
def gratitude():
    if request.method == 'POST':
        content = request.form['content']
        g = Gratitude(content=content)
        db.session.add(g)
        db.session.commit()
        return redirect(url_for('gratitude'))
    items = Gratitude.query.order_by(Gratitude.date.desc()).all()
    return render_template('gratitude.html', items=items)

@app.route('/delete/<int:id>')
def delete(id):
    entry = Entry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('journal'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    entry = Entry.query.get_or_404(id)
    if request.method == 'POST':
        entry.content = request.form['content']
        db.session.commit()
        return redirect(url_for('journal'))
    return render_template('edit.html', entry=entry)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)