"""Small learning app: PostgreSQL in AWS; SQLite only for local demos."""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from flask import Flask, abort, render_template, request

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8192
LOCAL = os.getenv('LOCAL_DEMO') == '1'


@contextmanager
def database():
    if LOCAL:
        path = os.getenv('SQLITE_PATH', '/tmp/bookings-demo.sqlite3')
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY, description TEXT NOT NULL,
            amount_pence INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    else:
        import boto3
        import psycopg
        from psycopg.rows import dict_row
        from botocore.config import Config
        # Read fresh credentials on each connection so password rotation is respected.
        client = boto3.client('secretsmanager', region_name=os.environ['AWS_REGION'],
                             config=Config(connect_timeout=3, read_timeout=3,
                                           retries={'max_attempts': 1}))
        secret = json.loads(client.get_secret_value(
            SecretId=os.environ['DB_SECRET_ARN'])['SecretString'])
        connection = psycopg.connect(
            host=os.environ['DB_HOST'], dbname=os.environ.get('DB_NAME', 'appdb'),
            user=secret['username'], password=secret['password'], port=5432,
            sslmode='verify-full', sslrootcert=str(Path(__file__).with_name('rds-ca.pem')),
            connect_timeout=5, options='-c statement_timeout=5000', row_factory=dict_row)
        # Transaction lock serializes the first table creation across ECS tasks.
        connection.execute('SELECT pg_advisory_xact_lock(71846291)')
        connection.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id BIGSERIAL PRIMARY KEY, description VARCHAR(200) NOT NULL,
            amount_pence BIGINT NOT NULL CHECK (amount_pence > 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        connection.commit()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def parse_booking(form):
    description = form.get('description', '').strip()
    amount = form.get('amount', '').strip()
    if not description or len(description) > 200:
        raise ValueError('Enter a description between 1 and 200 characters.')
    if not re.fullmatch(r'\d{1,7}(?:\.\d{1,2})?', amount):
        raise ValueError('Enter a GBP amount with no more than two decimal places.')
    pence = int(Decimal(amount) * 100)
    if not 1 <= pence <= 100_000_000:
        raise ValueError('Enter an amount between £0.01 and £1,000,000.')
    return description, pence


@app.get('/health')
def health():
    # Liveness only; homepage and saving a booking exercise the database.
    return {'status': 'ok'}


@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    status = 200
    if request.method == 'POST':
        # Browser form includes same-origin fetch; external pages cannot submit JSON.
        if not request.is_json or request.headers.get('X-Booking-Form') != '1':
            abort(403)
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            abort(403)
        data = request.get_json()
        if not isinstance(data, dict) or not all(isinstance(data.get(k), str) for k in ('description', 'amount')):
            return {'error': 'Enter a description and amount.'}, 400
        try:
            description, pence = parse_booking(data)
        except ValueError as exc:
            return {'error': str(exc)}, 400
        try:
            with database() as conn:
                marker = '?' if LOCAL else '%s'
                conn.execute(f'INSERT INTO bookings (description, amount_pence) VALUES ({marker}, {marker})',
                             (description, pence))
            return {'saved': True}, 201
        except Exception as exc:
            app.logger.error('Booking save failed (%s)', type(exc).__name__)
            return {'error': 'Could not save the booking. Check the application logs and database configuration.'}, 503
    try:
        with database() as conn:
            rows = conn.execute('SELECT id, description, amount_pence, created_at FROM bookings ORDER BY id DESC LIMIT 100').fetchall()
        bookings = [dict(row) for row in rows]
        for row in bookings:
            row['amount'] = f"{Decimal(row['amount_pence']) / 100:,.2f}"
    except Exception as exc:
        app.logger.error('Database read failed (%s)', type(exc).__name__)
        bookings = []
        error = 'Database unavailable. Check the application logs and database configuration.'
        status = 503
    return render_template('index.html', bookings=bookings, error=error, local=LOCAL), status


@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store'
    return response
