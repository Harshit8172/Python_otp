from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_mail import Mail, Message
import random
import pyodbc
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from langchain.agents import create_pandas_dataframe_agent
from langchain.llms import AzureOpenAI
from flask import Flask, request


app = Flask(__name__)

#  Set up OpenAI environment variables
import os
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_KEY"] = "8bfef13d7f4c4780a4c5db83a902a773"
os.environ["OPENAI_API_BASE"] = "https://serviceteamai.openai.azure.com/"
os.environ["OPENAI_API_VERSION"] = "2022-12-01"

# Create an instance of AzureOpenAI language model
llm = AzureOpenAI(
    deployment_name="serviceteam-davinci-003",
    model_name="text-davinci-003",
    openai_api_key="8bfef13d7f4c4780a4c5db83a902a773",
    model_kwargs={
        "api_type": "azure",
        "api_version": "2022-12-01"
    }
)

# Configure Flask Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'imharshitshukla@gmail.com'  # Replace with your email address
app.config['MAIL_PASSWORD'] = 'ejjajqrrpuorlrig'  # Replace with your email password
mail = Mail(app)

# SQL Server connection settings
server = 'DESKTOP-PV2MMT2\\SQLEXPRESS'
database = 'Employee'
trusted_connection = 'yes'

# Set up SQL Server connection string
conn_str = f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection={trusted_connection}"

# Create SQLAlchemy engine
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={conn_str}")

# Execute SQL query and fetch data into a DataFrame
query = 'SELECT * FROM Details'
df = pd.read_sql(query, engine)
print(df)

# Create the agent
agent = create_pandas_dataframe_agent(llm, df)

# Store the URL where the Flask app is running
app_url = ""

# Store OTPs for verification
otps = {}


@app.route('/')
def index():
    global app_url 
    app_url = request.host_url

    return render_template('verify.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        email = request.form['email']
        otp = str(random.randint(100000, 999999))
        otps[email] = otp

        # Send OTP via email
        send_otp_email(email, otp)

        return redirect(url_for('otp_verification', email=email))
    return render_template('verify.html')



@app.route('/otp_verification', methods=['GET', 'POST'])
def otp_verification():
    if request.method == 'POST':
        user_otp = request.form['otp']

        if user_otp in otps.values():
            # OTP verification successful
            return redirect(url_for('chatbot'))
        else:
            # OTP verification failed
            return redirect(url_for('index'))
    
    # If the request method is GET or not POST
    return render_template('otp_verification.html')



@app.route('/chatbot')
def chatbot():
    
    global app_url
    app_url = request.host_url
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask():
    question = request.form['question']
    if not question:
        return jsonify({'response': 'Please enter a question.'})
    try:
        response = agent.run(question)
        response_with_url = f"{app_url} - {response}"  # Include the URL with the response

        # Save chat history to SQL Server
        # saved_chat_history(question, response)

        return jsonify({'response': response_with_url})
    except Exception as e:
        return jsonify({'response': str(e)})
    
def send_otp_email(email, otp):
    msg = Message('OTP Verification', sender='your_email@gmail.com', recipients=[email])
    msg.body = f'Your OTP: {otp}'
    mail.send(msg)

def save_otp_history(email_input,otp_response):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO Otp_Verification_Details (Emailid, Otp, Timestamp) VALUES (?, ?, ?)"
    cursor.execute(query, (email_input, otp_response, timestamp))
    conn.commit()
    conn.close()

def saved_chat_history(user_input,bot_response):
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query = "INSERT INTO ChatHistory (User_Input, Bot_Response, Timestamp) VALUES (?, ?, ?)"
    cursor.execute(query, (user_input, bot_response, timestamp))
    conn.commit()
    conn.close()


@app.after_request
def after_request(response):
    # Print the URL in the terminal
    print(f"URL: {request.host_url}")
    return response


if __name__ == '__main__':
    app.run(debug=True)
