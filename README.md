
# Jira Worklog Extractor

This Python application extracts worklogs from Jira using Jira's REST API (v3) within a specified date range. It provides detailed information on the time logged for various issues during the provided date range, simplifying the task of tracking worklogs for projects.

## Features
- Connects to Jira using Jira REST API v3.
- Fetches worklogs for specified date ranges.
- Filters worklogs by user.
- Outputs worklogs in a readable JSON format.
  
## Prerequisites
- Python 3.8 or higher
- Jira API access (API Token and credentials)

## Installation

1. **Clone the Repository:**
```bash
	git clone https://github.com/yourusername/jira-worklog-extractor.git
	cd jira-worklog-extractor
```
    
2. **Create a virtual environment (Optional but recommended):**
```bash
	python -m venv venv
	source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. **Install Dependencies::**
```bash
	pip install -r requirements.txt
```
-   Flask (for the web server)
-   Requests (for interacting with the Jira REST API)
-   pytz (for timezone management)
-   Jinja2 (for templating)
-   Gunicorn (for running the Flask app in production)

4. **Configuration:**
    Update the `config.json` file in the root directory with the following content:
```json
	{
		"DEBUG": true,
		"JIRA_URL": "https://your-company.atlassian.net",
		"APP_SECRET_KEY": "<YOUR_CUSTOM_APP_SECRET_KEY>",
		"LOG_FILE_NAME": "jira_app_logs.txt"
	}
```
- Replace `JIRA_URL` with your Jira instance URL.
- Set `APP_SECRET_KEY` to a custom secret key.
- `LOG_FILE_NAME` is the file where logs will be stored. This file is saved under `_logs` folder in the root directory

5. **Jira Setup:**
- You will need the following credentials to access Jira’s REST API:
- Jira Base URL (e.g., https://your-domain.atlassian.net)
- Jira Username (email)
- Jira API Token (generate from Jira settings)

6. **Running the App**
You can run the app locally using Python:
```bash
	python app.py
```

7. **Access the Application**
Once the app is running, you can access it via http://localhost:5000


## How to Use

#### Login
-   Click the "Login" button and enter your Jira email and API token to authenticate.
-   After logging in, you will be redirected to the dashboard.

#### Fetch Worklogs
-   Enter following details to fetch worklogs: 
	1. ##### Project Key `[optional]`  
	2. ##### User IDs `[mandatory]`
	3. ##### Date Range `[mandatory]`
-   The fetched worklogs are displayed in a data table with ticket numbers, summaries, project names, time spent (hours), and start times.
-   Footer of the data table contains `Page Total` and `Total` hours
-   Filtering records will update the `Page Total`

#### Logout
-   Use the "Logout" button to clear your session and end the Jira login.

#### Error Handling and Logging
-   All errors and exceptions are logged to the file specified in the `LOG_FILE_NAME` field in the `config.json` file.
-   If the application encounters an issue while fetching data from Jira, appropriate error messages are displayed.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more details.