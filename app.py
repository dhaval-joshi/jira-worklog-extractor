import traceback
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
from datetime import datetime
import pytz
import logging
import json
import os

if not os.path.exists('_logs'):
        os.makedirs('_logs')

with open('config.json') as config_file:
    config_data = json.load(config_file)

app = Flask(__name__)
app.config.update(config_data)
app.secret_key = app.config['APP_SECRET_KEY']  # Needed to manage sessions

# Jira URL
JIRA_URL = app.config['JIRA_URL']

# Set up logging
logging.basicConfig(filename=f'_logs\\{app.config['LOG_FILE_NAME']}', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/')
def index():
    if 'logged_in' in session:
        return render_template('index.html', logged_in=True, user_email=session['user_email'])
    else:
        return render_template('index.html', logged_in=False)


@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.json.get('email')
        api_token = request.json.get('api_token')

        # Attempt to authenticate with Jira
        response = requests.get(f'{JIRA_URL}/rest/api/3/myself', auth=(email, api_token))

        if response.status_code == 200:
            session['logged_in'] = True
            session['user_email'] = email
            session['jira_auth'] = (email, api_token)
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Invalid Jira credentials'}), 401

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({'An internal error has occurred!'}), 500


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True}), 200


@app.route('/check_login', methods=['GET'])
def check_login():
    return jsonify({'logged_in': 'jira_auth' in session and session['jira_auth'] is not None}), 200


@app.route('/fetch_worklogs', methods=['POST'])
def fetch_worklogs():
    if 'logged_in' not in session:
        return jsonify({'error': 'User not logged in'}), 401

    auth = session['jira_auth']  # Get Jira auth from session

    try:
        req_json = request.json
        proj_key = req_json.get('project_key', '')
        project_key = proj_key.upper()
        users = req_json.get('users', '')
        start_date = req_json.get('start_date', '2024-01-01')
        end_date = req_json.get('end_date', '2024-12-31')

        user_ids = [user.strip() for user in users.split(',')]
        if not user_ids:
            return jsonify({'error': 'No users provided'}), 400

        start_timestamp = convert_to_unix_timestamp_ms(f'{start_date} 00:00:00')
        end_timestamp = convert_to_unix_timestamp_ms(f'{end_date} 23:59:59')

        worklog_ids = get_worklog_ids(start_timestamp, end_timestamp, project_key, auth)
        worklogs = get_worklogs_details(worklog_ids, auth)

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_dt = datetime.strptime(end_date, '%Y-%m-%d')

        filtered_worklogs = filter_worklogs_by_user_and_date(worklogs, user_ids, start_date_dt, end_date_dt, project_key)
        result = filter_worklogs_and_fetch_issue_keys(filtered_worklogs, user_ids, project_key)

        return jsonify(result), 200

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({'An internal error has occurred!'}), 500


def get_worklog_ids(start_timestamp, end_timestamp, project_key, auth):
    worklog_ids = []
    next_page = f'{JIRA_URL}/rest/api/3/worklog/updated?since={start_timestamp}&until={end_timestamp}'

    while next_page:
        response = requests.get(next_page, auth=auth)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch worklog IDs: {response.text}")

        data = response.json()
        worklog_ids.extend([worklog['worklogId'] for worklog in data.get('values', [])])

        next_page = data.get('nextPage')

    return worklog_ids


def get_worklogs_details(worklog_ids, auth):
    worklogs_details = []
    chunk_size = 1000

    for i in range(0, len(worklog_ids), chunk_size):
        chunk_ids = worklog_ids[i:i + chunk_size]
        response = requests.post(f'{JIRA_URL}/rest/api/3/worklog/list', json={'ids': chunk_ids}, auth=auth)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch worklogs details: {response.text}")
        worklogs_details.extend(response.json())
    return worklogs_details


def filter_worklogs_by_user_and_date(worklogs, user_ids, start_date_dt, end_date_dt, project_key):
    filtered_worklogs = [
        {
            'accountId': worklog['author']['accountId'],
            'user': worklog['author']['displayName'],
            'issueId': worklog['issueId'],
            'timeSpent': worklog['timeSpentSeconds'],
            'started': worklog['started'],
        }
        for worklog in worklogs
        if worklog['timeSpentSeconds'] > 0 and worklog['author']['accountId'] in user_ids and start_date_dt <= datetime.strptime(worklog['started'][:10], '%Y-%m-%d') <= end_date_dt
    ]
    return filtered_worklogs


def filter_worklogs_and_fetch_issue_keys(worklogs, user_ids, fltr_project_key):
    user_worklogs = {}
    issue_ids = list(set(worklog['issueId'] for worklog in worklogs))
    issue_details = get_issue_details(issue_ids, fltr_project_key)

    for worklog in worklogs:
        issue_id = worklog['issueId']
        user_id = worklog['accountId']
        issue_key = issue_details.get(issue_id, {}).get('key', 'Unknown')
        project_name = issue_details.get(issue_id, {}).get('projectName', 'Unknown')
        project_key = issue_details.get(issue_id, {}).get('projectKey', 'Unknown')
        summary = issue_details.get(issue_id, {}).get('summary', 'Unknown')

        if fltr_project_key != '' and fltr_project_key != project_key:
            continue

        if user_id not in user_worklogs:
            user_worklogs[user_id] = {'displayName': worklog['user'], 'worklogs': []}

        user_worklogs[user_id]['worklogs'].append({
            'ticket': issue_key,
            'summary': summary,
            'projectName': project_name,
            'projectKey': project_key,
            'timeSpent': worklog['timeSpent'],
            'started': worklog['started']
        })

    return user_worklogs


def get_issue_details(issue_ids, fltr_project_key):
    issue_details = {}
    chunk_size = 1000

    for i in range(0, len(issue_ids), chunk_size):
        chunk_ids = issue_ids[i:i + chunk_size]
        jql = f"id in ({','.join(map(str, chunk_ids))})"

        if fltr_project_key != '':
            jql += f' AND project = {fltr_project_key}'

        response = requests.post(f'{JIRA_URL}/rest/api/3/search', json={'jql': jql, 'fields': ['key', 'project', 'summary']}, auth=session['jira_auth'])

        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue details: {response.text}")

        issues = response.json().get('issues', [])
        for issue in issues:
            issue_id = issue['id']
            issue_details[issue_id] = {
                'key': issue['key'],
                'projectName': issue['fields']['project']['name'],
                'projectKey': issue['fields']['project']['key'],
                'summary': issue['fields']['summary']
            }

    return issue_details


def convert_to_unix_timestamp_ms(date_string: str, date_format: str = '%Y-%m-%d %H:%M:%S') -> int:
    dt = datetime.strptime(date_string, date_format)
    ist = pytz.timezone('Asia/Kolkata')
    localized_dt = ist.localize(dt)
    return int(localized_dt.timestamp() * 1000)


if __name__ == '__main__':
    app.run()
