import os
import sqlite3
import click
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import check_password_hash, generate_password_hash
import pdfkit
import tempfile

app = Flask(__name__)
app.secret_key = 'silico_battles_2025_winner'

# database stuff
DB_PATH = 'podium.db'

# connects to the database
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# makes the database tables and adds some data
def init_db():
    conn = get_db_connection()
    with conn:
        # Create tables if they don't exist
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('super_admin', 'admin'))
            );
            CREATE TABLE IF NOT EXISTS Events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                results_entered INTEGER DEFAULT 0,
                first_place_points INTEGER DEFAULT 100,
                second_place_points INTEGER DEFAULT 75,
                third_place_points INTEGER DEFAULT 50
            );
            CREATE TABLE IF NOT EXISTS Results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER UNIQUE NOT NULL REFERENCES Events(id),
                first_place_school TEXT,
                second_place_school TEXT,
                third_place_school TEXT,
                submitted_at DATETIME NOT NULL
            );
            CREATE TABLE IF NOT EXISTS Schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS AuditLog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                action TEXT NOT NULL,
                event_name TEXT,
                timestamp DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES Users(id)
            );
        ''')

        # Seed the database with initial data
        with open('seed.sql') as f:
            conn.executescript(f.read())

    conn.close()

@app.cli.command("init-db")
def init_db_command():
    """Clears the existing data and creates new tables."""
    init_db()
    click.echo("Initialized the database.")

@app.cli.command("create-user")
@click.argument("username")
@click.argument("password")
@click.argument("role")
def create_user_command(username, password, role):
    """Creates a new user with the given username, password, and role."""
    if role not in ['admin', 'super_admin']:
        click.echo("Invalid role. Please choose 'admin' or 'super_admin'.")
        return

    conn = get_db_connection()
    try:
        with conn:
            hashed_password = generate_password_hash(password, method='scrypt')
            conn.execute(
                'INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, hashed_password, role)
            )
        click.echo(f"User '{username}' created successfully as '{role}'.")
    except sqlite3.IntegrityError:
        click.echo(f"Error: Username '{username}' already exists.")
    finally:
        conn.close()

@app.after_request
def add_header(response):
    """
    Add headers to both force latest content and prevent caching.
    """
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# gets the school scores
def get_school_standings(conn):
    query = """
        WITH EventPoints AS (
            SELECT
                r.event_id,
                e.first_place_points,
                e.second_place_points,
                e.third_place_points,
                r.first_place_school,
                r.second_place_school,
                r.third_place_school
            FROM Results r
            JOIN Events e ON r.event_id = e.id
        ),
        AllPlacements AS (
            SELECT first_place_school AS school, first_place_points AS points, 1 AS first_places, 0 AS second_places, 0 AS third_places FROM EventPoints UNION ALL
            SELECT second_place_school AS school, second_place_points AS points, 0 AS first_places, 1 AS second_places, 0 AS third_places FROM EventPoints UNION ALL
            SELECT third_place_school AS school, third_place_points AS points, 0 AS first_places, 0 AS second_places, 1 AS third_places FROM EventPoints
        )
        SELECT
            school,
            SUM(points) AS total_points,
            SUM(first_places) AS first_places,
            SUM(second_places) AS second_places,
            SUM(third_places) AS third_places
        FROM AllPlacements
        WHERE school IS NOT NULL AND school != ''
        GROUP BY school
        ORDER BY total_points DESC, first_places DESC, second_places DESC, third_places DESC, school ASC;
    """
    return conn.execute(query).fetchall()

# main page
@app.route('/')
def standings_view():
    conn = get_db_connection()
    standings_raw = get_school_standings(conn)

    standings = []
    rank = 0
    last_school_details = (-1, -1, -1, -1) # points, 1st, 2nd, 3rd
    for i, school in enumerate(standings_raw):
        current_school_details = (school['total_points'], school['first_places'], school['second_places'], school['third_places'])
        if current_school_details != last_school_details:
            rank += 1
        standings.append(dict(school, rank=rank))
        last_school_details = current_school_details

    # for showing when the scores were last updated
    last_updated_query = "SELECT MAX(submitted_at) FROM Results"
    last_update_row = conn.execute(last_updated_query).fetchone()
    last_update = last_update_row[0] if last_update_row and last_update_row[0] else None

    last_updated_time = None
    if last_update:
        # change from UTC to our time
        last_updated_naive = datetime.fromisoformat(last_update)
        last_updated_utc = last_updated_naive.replace(tzinfo=timezone.utc)
        ist_tz = ZoneInfo("Asia/Kolkata")
        last_updated_time = last_updated_utc.astimezone(ist_tz)

    all_results_query = """
        SELECT e.name, r.first_place_school, r.second_place_school, r.third_place_school
        FROM Results r
        JOIN Events e ON r.event_id = e.id
        ORDER BY e.name ASC
    """
    all_results = conn.execute(all_results_query).fetchall()

    conn.close()
    return render_template('standings.html', schools=standings, last_updated=last_updated_time, all_results=all_results)

@app.route('/scoring')
def scoring_view():
    conn = get_db_connection()
    events_query = "SELECT name, first_place_points, second_place_points, third_place_points FROM Events ORDER BY name ASC"
    all_events = conn.execute(events_query).fetchall()
    conn.close()
    return render_template('scoring.html', events=all_events)

# this sends data for the graph on the main page
@app.route('/api/graph_data')
def graph_data():
    conn = get_db_connection()
    query = """
        SELECT r.submitted_at, e.name, r.first_place_school, r.second_place_school, r.third_place_school
        FROM Results r
        JOIN Events e ON r.event_id = e.id
        ORDER BY r.submitted_at ASC
    """
    submissions = conn.execute(query).fetchall()

    labels = [sub['name'] for sub in submissions]
    datasets = {}
    all_schools = set()

    for sub in submissions:
        all_schools.add(sub['first_place_school'])
        all_schools.add(sub['second_place_school'])
        all_schools.add(sub['third_place_school'])

    for school in all_schools:
        if not school: continue
        datasets[school] = {
            'label': school,
            'data': [],
            'borderColor': f'hsla({(hash(school) % 360)}, 90%, 70%, 1)',
            'backgroundColor': f'hsla({(hash(school) % 360)}, 90%, 70%, 1)',
            'tension': 0.1
        }
    
    for i, sub in enumerate(submissions):
        if i > 0:
            for school in datasets:
                datasets[school]['data'].append(datasets[school]['data'][i-1])
        else:
            for school in datasets:
                datasets[school]['data'].append(0)

        event_points = conn.execute('SELECT first_place_points, second_place_points, third_place_points FROM Events WHERE name = ?', (sub['name'],)).fetchone()

        if sub['first_place_school'] in datasets:
            datasets[sub['first_place_school']]['data'][i] += event_points['first_place_points']
        if sub['second_place_school'] in datasets:
            datasets[sub['second_place_school']]['data'][i] += event_points['second_place_points']
        if sub['third_place_school'] in datasets:
            datasets[sub['third_place_school']]['data'][i] += event_points['third_place_points']

    conn.close()
    final_datasets = list(datasets.values())
    return jsonify({'labels': labels, 'datasets': final_datasets})

@app.route('/school/<school_name>')
def school_details(school_name):
    conn = get_db_connection()
    
    standings_raw = get_school_standings(conn)
    
    standings = []
    rank = 0
    last_school_details = (-1, -1, -1, -1)
    for i, school in enumerate(standings_raw):
        current_school_details = (school['total_points'], school['first_places'], school['second_places'], school['third_places'])
        if current_school_details != last_school_details:
            rank += 1
        standings.append(dict(school, rank=rank))
        last_school_details = current_school_details

    current_rank = "N/A"
    for school in standings:
        if school['school'] == school_name:
            current_rank = school['rank']
            break
    
    positions_query = """
        SELECT e.name AS event_name,
               CASE
                   WHEN r.first_place_school = ? THEN '1st Place'
                   WHEN r.second_place_school = ? THEN '2nd Place'
                   WHEN r.third_place_school = ? THEN '3rd Place'
               END AS position
        FROM Results r JOIN Events e ON r.event_id = e.id
        WHERE r.first_place_school = ? OR r.second_place_school = ? OR r.third_place_school = ?
        ORDER BY e.name;
    """
    positions = conn.execute(positions_query, (school_name, school_name, school_name, school_name, school_name, school_name)).fetchall()
    
    total_points = 0
    summary = {'1st Place': 0, '2nd Place': 0, '3rd Place': 0}

    # Get points for each event
    event_points_query = """
        SELECT e.name, e.first_place_points, e.second_place_points, e.third_place_points
        FROM Events e
    """
    event_points_rows = conn.execute(event_points_query).fetchall()
    event_points = {row['name']: row for row in event_points_rows}

    for result in positions:
        summary[result['position']] += 1
        points = event_points.get(result['event_name'])
        if points:
            if result['position'] == '1st Place':
                total_points += points['first_place_points']
            elif result['position'] == '2nd Place':
                total_points += points['second_place_points']
            elif result['position'] == '3rd Place':
                total_points += points['third_place_points']

    conn.close()
    
    return render_template('school_details.html', 
                           school_name=school_name, 
                           results=positions,
                           summary=summary,
                           total_points=total_points,
                           rank=current_rank)

# login page for admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']

            if user['role'] == 'super_admin':
                return redirect(url_for('super_admin_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Wrong username or password.", "danger")
    return render_template('login.html')

# admin dashboard to add/edit scores
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') not in ['admin', 'super_admin']:
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))
    
    conn = get_db_connection()

    # when submitting new results
    if request.method == 'POST':
        event_id = request.form['event_id']
        first = request.form['first_place']
        second = request.form['second_place']
        third = request.form['third_place']

        # cant have same school in multiple places
        if len(set([first, second, third])) < 3:
            flash("A school cannot be in multiple places for one event.", "danger")
            return redirect(url_for('admin_dashboard'))
        
        try:
            with conn:
                conn.execute('''
                    INSERT INTO Results (event_id, first_place_school, second_place_school, third_place_school, submitted_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (event_id, first, second, third, datetime.now(timezone.utc)))
                conn.execute('UPDATE Events SET results_entered = 1 WHERE id = ?', (event_id,))

                # Audit log
                user_id = session['user_id']
                username = conn.execute('SELECT username FROM Users WHERE id = ?', (user_id,)).fetchone()['username']
                event_name = conn.execute('SELECT name FROM Events WHERE id = ?', (event_id,)).fetchone()['name']
                conn.execute(
                    'INSERT INTO AuditLog (user_id, username, action, event_name, timestamp) VALUES (?, ?, ?, ?, ?)',
                    (user_id, username, 'submit_result', event_name, datetime.now(timezone.utc))
                )
            flash('Results submitted!', 'success')
        except sqlite3.IntegrityError:
            flash("Results for this event have already been submitted.", "danger")

        if session.get('role') == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        return redirect(url_for('admin_dashboard'))

    # show the page
    all_events = conn.execute('SELECT e.id, e.name, e.results_entered, r.first_place_school, r.second_place_school, r.third_place_school FROM Events e LEFT JOIN Results r ON e.id = r.event_id ORDER BY e.name').fetchall()

    schools_query = "SELECT name FROM Schools ORDER BY name ASC"
    schools = [row['name'] for row in conn.execute(schools_query).fetchall()]

    conn.close()
    
    pending = [e for e in all_events if not e['results_entered']]
    submitted = [e for e in all_events if e['results_entered']]

    return render_template('admin_dashboard.html', pending_events=pending, submitted_events=submitted, schools=schools)

# edit existing results
@app.route('/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_result(event_id):
    if 'user_id' not in session or session.get('role') not in ['admin', 'super_admin']:
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        first = request.form['first_place']
        second = request.form['second_place']
        third = request.form['third_place']

        if len(set([first, second, third])) < 3:
            flash("A school cannot be in multiple places for one event.", "danger")
            # if theres an error, we have to load the data again
            result = conn.execute('SELECT * FROM Results WHERE event_id = ?', (event_id,)).fetchone()
            event = conn.execute('SELECT * FROM Events WHERE id = ?', (event_id,)).fetchone()
            schools_query = "SELECT name FROM Schools ORDER BY name ASC"
            schools = [row['name'] for row in conn.execute(schools_query).fetchall()]
            conn.close()
            return render_template('edit_result.html', result=result, event=event, schools=schools)
        
        conn.execute('''
            UPDATE Results
            SET first_place_school = ?, second_place_school = ?, third_place_school = ?, submitted_at = ?
            WHERE event_id = ?
        ''', (first, second, third, datetime.now(timezone.utc), event_id))

        # Audit log
        user_id = session['user_id']
        username = conn.execute('SELECT username FROM Users WHERE id = ?', (user_id,)).fetchone()['username']
        event_name = conn.execute('SELECT name FROM Events WHERE id = ?', (event_id,)).fetchone()['name']
        conn.execute(
            'INSERT INTO AuditLog (user_id, username, action, event_name, timestamp) VALUES (?, ?, ?, ?, ?)',
            (user_id, username, 'edit_result', event_name, datetime.now(timezone.utc))
        )

        conn.commit()
        conn.close()
        flash('Results updated!', 'success')

        if session.get('role') == 'super_admin':
            return redirect(url_for('super_admin_dashboard'))
        return redirect(url_for('admin_dashboard'))

    # load the page
    result = conn.execute('SELECT * FROM Results WHERE event_id = ?', (event_id,)).fetchone()

    if result is None:
        conn.close()
        flash('No results for this event.', 'warning')
        return redirect(url_for('admin_dashboard'))

    event = conn.execute('SELECT * FROM Events WHERE id = ?', (event_id,)).fetchone()
    schools_query = "SELECT name FROM Schools ORDER BY name ASC"
    schools = [row['name'] for row in conn.execute(schools_query).fetchall()]
    conn.close()
    
    return render_template('edit_result.html', result=result, event=event, schools=schools)

@app.route('/api/predictive_analytics')
def predictive_analytics():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db_connection()
    standings = get_school_standings(conn)

    total_events = conn.execute('SELECT COUNT(id) FROM Events').fetchone()[0]

    school_participation = {}
    for school_row in standings:
        school_name = school_row['school']
        count = conn.execute("SELECT COUNT(DISTINCT event_id) FROM (SELECT event_id FROM Results WHERE first_place_school = ? OR second_place_school = ? OR third_place_school = ?)", (school_name, school_name, school_name)).fetchone()[0]
        school_participation[school_name] = count

    conn.close()

    projected_standings = []
    for school_row in standings:
        school_name = school_row['school']
        current_points = school_row['total_points']
        events_participated = school_participation.get(school_name, 1) # Avoid division by zero

        avg_points_per_event = current_points / events_participated

        remaining_events = total_events - events_participated
        projected_points = current_points + (avg_points_per_event * remaining_events)

        projected_standings.append({
            'school': school_name,
            'total_points': round(projected_points)
        })

    projected_standings.sort(key=lambda x: x['total_points'], reverse=True)

    return jsonify(projected_standings[:5])


@app.route('/what_if_scenario', methods=['POST'])
def what_if_scenario():
    if 'user_id' not in session or session.get('role') not in ['admin', 'super_admin']:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    first = data.get('first_place')
    second = data.get('second_place')
    third = data.get('third_place')

    conn = get_db_connection()
    current_standings = get_school_standings(conn)
    conn.close()

    standings_dict = {row['school']: {'total_points': row['total_points'], 'original_points': row['total_points']} for row in current_standings}

    avg_points = conn.execute('''
        SELECT AVG(first_place_points), AVG(second_place_points), AVG(third_place_points)
        FROM Events
    ''').fetchone()

    avg_first = avg_points[0] if avg_points[0] is not None else 100
    avg_second = avg_points[1] if avg_points[1] is not None else 75
    avg_third = avg_points[2] if avg_points[2] is not None else 50


    if first and first in standings_dict:
        standings_dict[first]['total_points'] += avg_first
    elif first:
        standings_dict[first] = {'total_points': avg_first, 'original_points': 0}

    if second and second in standings_dict:
        standings_dict[second]['total_points'] += avg_second
    elif second:
        standings_dict[second] = {'total_points': avg_second, 'original_points': 0}

    if third and third in standings_dict:
        standings_dict[third]['total_points'] += avg_third
    elif third:
        standings_dict[third] = {'total_points': avg_third, 'original_points': 0}

    new_standings = sorted(
        [{'school': k, **v} for k, v in standings_dict.items()],
        key=lambda x: x['total_points'],
        reverse=True
    )

    return jsonify(new_standings)

@app.route('/download_leaderboard_pdf')
def download_leaderboard_pdf():
    conn = get_db_connection()
    standings_raw = get_school_standings(conn)
    conn.close()

    standings = []
    rank = 0
    last_school_details = (-1, -1, -1, -1)
    for i, school in enumerate(standings_raw):
        current_school_details = (school['total_points'], school['first_places'], school['second_places'], school['third_places'])
        if current_school_details != last_school_details:
            rank += 1
        standings.append(dict(school, rank=rank))
        last_school_details = current_school_details

    # Get current time for the timestamp
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    timestamp = now.strftime('%B %d, %Y at %I:%M %p')

    # Render the PDF-specific template
    rendered_html = render_template('leaderboard_pdf.html', schools=standings, timestamp=timestamp)

    # Generate PDF from the rendered HTML
    pdf = pdfkit.from_string(rendered_html, False)

    # Create a response with the PDF
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=leaderboard.pdf'

    return response

@app.route('/admin/audit_log')
def audit_log():
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    logs_from_db = conn.execute('SELECT * FROM AuditLog ORDER BY timestamp DESC').fetchall()
    conn.close()

    logs = []
    for log in logs_from_db:
        log_dict = dict(log)
        # Convert timestamp string to datetime object and make it timezone-aware
        dt_naive = datetime.fromisoformat(log_dict['timestamp'].replace('Z', ''))
        dt_utc = dt_naive.replace(tzinfo=timezone.utc)
        ist_tz = ZoneInfo("Asia/Kolkata")
        log_dict['timestamp'] = dt_utc.astimezone(ist_tz)
        logs.append(log_dict)

    return render_template('audit_log.html', logs=logs)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session.get('role') != 'super_admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    if user_id == session['user_id']:
        return jsonify({'success': False, 'message': 'You cannot delete yourself.'}), 400

    conn = get_db_connection()
    conn.execute('DELETE FROM Users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'User deleted successfully.'})

@app.route('/podium')
def podium():
    conn = get_db_connection()
    standings_raw = get_school_standings(conn)
    conn.close()

    standings = []
    rank = 0
    last_school_details = (-1, -1, -1, -1)
    for i, school in enumerate(standings_raw):
        current_school_details = (school['total_points'], school['first_places'], school['second_places'], school['third_places'])
        if current_school_details != last_school_details:
            rank += 1
        standings.append(dict(school, rank=rank))
        last_school_details = current_school_details

    top_schools = [s for s in standings if s['rank'] <= 3]

    return render_template('podium.html', top_three=top_schools)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# to delete a school
@app.route('/admin/schools/delete/<int:school_id>', methods=['POST'])
def delete_school(school_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    conn = get_db_connection()

    school_to_delete = conn.execute('SELECT name FROM Schools WHERE id = ?', (school_id,)).fetchone()
    if not school_to_delete:
        conn.close()
        return jsonify({'success': False, 'message': 'School not found.'}), 404

    school_name = school_to_delete['name']

    # check if school has any results, cant delete if so
    results_check = conn.execute('''
        SELECT 1 FROM Results WHERE first_place_school = ? OR second_place_school = ? OR third_place_school = ?
    ''', (school_name, school_name, school_name)).fetchone()

    if results_check:
        conn.close()
        return jsonify({'success': False, 'message': f"Cannot delete '{school_name}' because it has associated results."}), 400

    conn.execute('DELETE FROM Schools WHERE id = ?', (school_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f"School '{school_name}' deleted successfully."})

# to edit a school name
@app.route('/admin/schools/edit/<int:school_id>', methods=['GET', 'POST'])
def edit_school(school_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    school = conn.execute('SELECT * FROM Schools WHERE id = ?', (school_id,)).fetchone()
    if not school:
        flash("School not found.", "danger")
        conn.close()
        return redirect(url_for('manage_schools'))

    if request.method == 'POST':
        new_name = request.form['name'].strip()
        old_name = school['name']

        if not new_name:
            flash("School name can't be empty.", "danger")
        elif new_name != old_name:
            try:
                # update name in all tables
                conn.execute('UPDATE Schools SET name = ? WHERE id = ?', (new_name, school_id))
                conn.execute('UPDATE Results SET first_place_school = ? WHERE first_place_school = ?', (new_name, old_name))
                conn.execute('UPDATE Results SET second_place_school = ? WHERE second_place_school = ?', (new_name, old_name))
                conn.execute('UPDATE Results SET third_place_school = ? WHERE third_place_school = ?', (new_name, old_name))
                conn.commit()
                flash(f"School name changed to '{new_name}'.", "success")
                conn.close()
                return redirect(url_for('manage_schools'))
            except sqlite3.IntegrityError:
                flash(f"School name '{new_name}' already exists.", "danger")
                # stay on page to show error
        else:
            # no change
            flash("No changes made.", "info")

        conn.close()
        return redirect(url_for('edit_school', school_id=school_id))

    # show the page
    conn.close()
    return render_template('edit_school.html', school=school)

# page to add/delete/edit schools
@app.route('/admin/schools', methods=['GET', 'POST'])
def manage_schools():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()

    # for adding a new school
    if request.method == 'POST':
        school_name = request.form['name'].strip()
        if school_name:
            try:
                conn.execute('INSERT INTO Schools (name) VALUES (?)', (school_name,))
                conn.commit()
                flash(f"School '{school_name}' added!", "success")
            except sqlite3.IntegrityError:
                flash(f"School '{school_name}' already exists.", "danger")
        else:
            flash("School name can't be empty.", "danger")

        conn.close()
        return redirect(url_for('manage_schools'))

    # show the page with all schools
    schools = conn.execute('SELECT * FROM Schools ORDER BY name ASC').fetchall()
    conn.close()

    return render_template('manage_schools.html', schools=schools)

@app.route('/admin/events', methods=['GET', 'POST'])
def manage_events():
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        first_points = request.form['first_place_points']
        second_points = request.form['second_place_points']
        third_points = request.form['third_place_points']
        try:
            conn.execute(
                'INSERT INTO Events (name, first_place_points, second_place_points, third_place_points) VALUES (?, ?, ?, ?)',
                (name, first_points, second_points, third_points)
            )
            conn.commit()
            flash(f"Event '{name}' created successfully.", "success")
        except sqlite3.IntegrityError:
            flash(f"Event '{name}' already exists.", "danger")
        return redirect(url_for('manage_events'))

    events = conn.execute('SELECT * FROM Events ORDER BY name ASC').fetchall()
    conn.close()

    return render_template('manage_events.html', events=events)

@app.route('/admin/events/edit/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        first_points = request.form['first_place_points']
        second_points = request.form['second_place_points']
        third_points = request.form['third_place_points']
        try:
            conn.execute(
                'UPDATE Events SET name = ?, first_place_points = ?, second_place_points = ?, third_place_points = ? WHERE id = ?',
                (name, first_points, second_points, third_points, event_id)
            )
            conn.commit()
            flash(f"Event '{name}' updated successfully.", "success")
        except sqlite3.IntegrityError:
            flash(f"Event '{name}' already exists.", "danger")
        return redirect(url_for('manage_events'))

    event = conn.execute('SELECT * FROM Events WHERE id = ?', (event_id,)).fetchone()
    conn.close()

    return render_template('edit_event.html', event=event)

@app.route('/admin/events/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM Events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('manage_events'))

@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if not username or not password or not role:
            flash("Username, password, and role are required.", "danger")
        else:
            hashed_password = generate_password_hash(password, method='scrypt')
            try:
                conn.execute(
                    'INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)',
                    (username, hashed_password, role)
                )
                conn.commit()
                flash(f"User '{username}' created successfully.", "success")
            except sqlite3.IntegrityError:
                flash(f"Username '{username}' already exists.", "danger")

        return redirect(url_for('manage_users'))

    users = conn.execute('SELECT id, username, role FROM Users').fetchall()
    conn.close()

    return render_template('manage_users.html', users=users)

@app.route('/super_admin_dashboard')
def super_admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'super_admin':
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for('login'))

    conn = get_db_connection()
    all_events = conn.execute('SELECT e.id, e.name, e.results_entered, r.first_place_school, r.second_place_school, r.third_place_school FROM Events e LEFT JOIN Results r ON e.id = r.event_id ORDER BY e.name').fetchall()
    schools_query = "SELECT name FROM Schools ORDER BY name ASC"
    schools = [row['name'] for row in conn.execute(schools_query).fetchall()]
    conn.close()

    pending = [e for e in all_events if not e['results_entered']]
    submitted = [e for e in all_events if e['results_entered']]

    return render_template('super_admin_dashboard.html', pending_events=pending, submitted_events=submitted, schools=schools)

if __name__ == '__main__':
    app.run(debug=True)