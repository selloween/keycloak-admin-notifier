# Keycloak Admin Notifier

Keycloak is a great Identity and Access Managment (IAM) solution but lacks currently the ability of sending notification emails to the administrator. As an admin it is crucial beeing notified when a new user registers to take further actions like granting a user specific roles and permissions. Thankfully Keycloak offers an extensive Rest API that we can use to fetch and further process user events. 

You can review the full source code in my github repository: https://github.com/selloween/keycloak-admin-notifier

In this guide we will write a Python script that sends notifications to a specified email address when a new user registers. We will take advantage of `python-keycloak`, a Python package providing access to the Keycloak API.
The script can be easily modified to send emails on any other event such as user logins or failed login attempts.

You can read more on python keycloak here: https://pypi.org/project/python-keycloak/
For more information on the Keycloak Admin Rest API visit: https://www.keycloak.org/docs-api/2.5/rest-api/index.html

## Steps Overview

Let's note down the steps that we want our script to do.

1. Authenticate with the Keycloak Admin CLI and fetch an access token
2. Request registration events
3. Get user information from the response
4. (Optional actions, e.g. adding a user to a specific group - this will be handled in another tutorial)
5. Send an email containing user information to a specified email address
6. Create a log file containing a timestamp of the last event
7. Run the script regulary by creating a cronjob on the server

## Environment setup

Before we can start we have to make sure that following requirements are installed on the system:

### Requirements

* Python 3
* Python pip
* Miniconda

This guide assumes installation in a Linux environment. If you are a Mac or Windows user you can install the requirements by reffering to the online documentation accordingly.
As our script will be running on a Linux server I would recommend setting up an virtual environment using a Virtual Machine or Docker.
To keep things simple I will be demonstrating the setup on a Ubuntu/Debian system.
Feel free to use any other distribution.

### Install Python 3

`sudo apt-get install python3 python3-pip`

### Install Miniconda

"Conda is an open source package and environment management system that runs on Windows, macOS and Linux. Conda quickly installs, runs and updates packages and their dependencies. Miniconda is a small, bootstrap version of Anaconda that includes only conda, Python, the packages they depend on and a small number of other useful packages."

For more information on Conda visit: https://docs.conda.io

#### Download Miniconda 3 installer

* Visit https://docs.conda.io/en/latest/miniconda.html
* Download the latest Miniconda 3 bash installer for 64-bit Linux
* Make sure to download Miniconda for Python 3 (currently Python 3.7)
* Open a terminal and navigate to the download directory
* Make the installation script executable by using the command bellow (Change the file name accordingly to the current Python version)

```bash
sudo chmod +x Miniconda3-latest-Linux-x86_64.sh
```

*In the download directory install Miniconda by typing:

```bash
sudo ./Miniconda3-latest-Linux-x86_64.sh
```

*Check if Conda is installed

```bash
$ conda -V
conda 4.5.12
```

*Update Conda

```bash
conda update conda
```

## Create a Virtual Environment

* Open a terminal and enter the command bellow where `env_name` is the name of the environment.
* Replace the Python version accordingly by first checking the Python 3 version installed as showed in the example.
* Activate the environment.

```bash
$ python -V
Python 3.7.1
```

```bash
conda create -n env_name python=3.7
```

```bash
conda activate env_name
```

You can deactive the environment like this: `conda deactivate env_name`

## Create a Keycloak Realm Admin

Each Keycloak Realm has its own `admin-cli` client which only a realm administrator can access. We have to create an dedicated realm admin or give an exisiting user the required realm administration roles so that he can access the realm admin-cli. Out of security reasons I would suggest having only one dedicated realm administrator per realm. Keep in mind that the master realm administrator can't access the admin-cli of another realm than the master realm via the API directly.

* Navigate to your desired Realm Dashboard in the graphical Keycloak admin interface.
* Click on `Users`in the navigation sidebar and add a new user by clicking the `Add User` button.
* Create the user and don't forget to set a secure password - this is done in the `Credentials` tab
* Click on the `Role Mappings` tab and extend the `Client Roles` dropdown menu.
* Select `Realm Management` and assign all available roles. Keep in mind that this gives the user all possible realm permissions. You might want to restrict some of the permissions depending on your needs.

## Directory structure

1. Create a project directory and name it as your liking.
2. Create a sub-directory and name it `log`. This will be the directory the script will write to our `timestamp.log` file.
3. Create Python file and name it `notifier.py`. This file will contain our source code.
4. Create a file named `run.sh`. This file will export necessary environment variables and run the notifier Python script.

The directory structure should look like this:

```bash
log
notifier.py
run.sh
```

## Install Dependencies

To get easy access to the Keycloak API we will install a Python library called `python-keycloak`.
Make sure you activated the conda environment: `conda activate env_name`.

```bash
pip install python-keycloak
```

Next install the `DateTime` package which will later on help convert UNIX timecode to human readable time.

```bash
pip install datetime
```

`python-keycloak` and `DateTime` are the only two external packages needed. The rest of the dependencies are intergrated Python modules.

## Export the conda environment

Export the conda environment to a file:

```bash
conda env export > environment.yml
```

## Code the Script

Open `notifier.py` and add the dependencies.

### Import Dependencies

```python
import requests
import json
import os
import time
import smtplib

from keycloak import KeycloakAdmin
from time import sleep
from datetime import datetime
from email.message import EmailMessage
# ...
```

### Create environment variables

In order for the script to authenticate we will have to provide the admin credentials. We do not want to store sensitive data like username and password plaintext in our code. Instead it is a better idea to export environment variables and import them in our code. Therfore export them in the  `run.sh` script.

Important Note: Make sure `run.sh` is never pushed to a repository. Add this file to `.gitignore`
Open `run.sh`in your text editor of choice and add the following environment variables. Adjust their values accordingly.

```bash
#!/bin/bash

export KEYCLOAK_URL=https://your-keycloak.com/auth/
export KEYCLOAK_REALM=your-keycloak-realm
export KEYCLOAK_USERNAME=keycloak-admin-user
export KEYCLOAK_PASSWORD=keycloak-export SMTP_HOST=smtp.your-host.com
export SMTP_PORT=587 # Change accordingly
export SMTP_SENDER=mail@your-host.com
export SMTP_RECEIVER=your-receiver@host.com
export SMTP_PASSWORD=your-smtp-passwordadmin-password

```

* `run.sh` will be the entrypoint of our python script.   We will cover that later on. Make sure to replace `env_name` with name you gave your conda environment. We are using the absolute path to the python binary located in the conda environment.  This ensures using the correct Python version and having all dependencies met.

```bash
/home/$USER/miniconda3/envs/env_name/bin/python notifier.py
```

The `$USER` variable will automatically get the user running the script. Note that the user variable has to be replaced to an actual user once deployed.

The complete ode of `run.sh` should look like this:

```bash
#!/bin/bash

export KEYCLOAK_URL=https://your-keycloak.com/auth/
export KEYCLOAK_REALM=your-keycloak-realm
export KEYCLOAK_USERNAME=keycloak-admin-user
export KEYCLOAK_PASSWORD=keycloak-admin-password
export SMTP_HOST=smtp.your-host.com
export SMTP_PORT=587 # Change accordingly
export SMTP_SENDER=mail@your-host.com
export SMTP_RECEIVER=your-receiver@host.com
export SMTP_PASSWORD=your-smtp-password

/home/$USER/miniconda3/envs/env_name/bin/python notifier.py
```

* Make `run.sh`executable

```bash
sudo chmod +x run.sh
```

Now we can ensure that the necessary environment variables are exported and that the correct environment containing all dependencies is loaded when our script is executed.

### Configure SMTP

Using the SMTP Python library `smtplib` we can create a simple function for sending messsages to a specifided email address (e.g. to an admin). Our function takes two string arguments - the message of the email and the keycloak event.

```python
def send_mail(message, event):

    # SMTP configuration
    sender = os.environ['SMTP_SENDER']
    receiver = os.environ['SMTP_RECEIVER']
    password = os.environ['SMTP_PASSWORD']
    host = os.environ['SMTP_HOST']
    port = os.environ['SMTP_PORT']

    # Email configuration
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = 'New Keycloak Event: ' + event
    msg['From'] = sender
    msg['To'] = receiver

    # Start TLS and send email
    server = smtplib.SMTP(host, port)
    server.ehlo()
    server.starttls()
    server.login(sender, password)
    server.sendmail(
        sender,
        receiver,
        str(msg)
    )
    server.quit()
```

### Authentication

#### Import Keycloak Credentials

Open `notifier.py` and declare following variables:

```python
# ...
keycloak_username = os.environ['KEYCLOAK_USERNAME']
keycloak_password = os.environ['KEYCLOAK_PASSWORD']
keycloak_url = os.environ['KEYCLOAK_URL']
keycloak_realm = os.environ['KEYCLOAK_REALM']
# ...
```

Now that we have our Keycloak credentials stored safely let's pass them to the `KeycloakAdmin()` method imported from `python-keycloak`.

```python
# ...
keycloak_username = os.environ['KEYCLOAK_USERNAME']
keycloak_password = os.environ['KEYCLOAK_PASSWORD']
keycloak_url = os.environ['KEYCLOAK_URL']
keycloak_realm = os.environ['KEYCLOAK_REALM']

keycloak_admin = KeycloakAdmin(
    server_url=keycloak_url,
    username=keycloak_username,
    password=keycloak_password,
    realm_name=keycloak_realm,
    verify=True)

keycloak_data = {
    'username': keycloak_username,
    'password': keycloak_password,
    'url': keycloak_url,
    'realm': keycloak_realm,
    'admin': keycloak_admin
}
# ...
```

#### Get the Access Token

Let's write a simple function to request an access token. We will add the keycloak credentials, grant type and client id in the data field of the http header.

This function will request and return an access token.

```python
# ...
def get_keycloak_token():

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'username': keycloak_data['username'],
        'password': keycloak_data['password'],
        'grant_type': 'password',
        'client_id': 'admin-cli'
    }

    response = requests.post(keycloak_data['url'] + 'realms/' + keycloak_data['realm'] +
                             '/protocol/openid-connect/token', headers=headers, data=data).json()['access_token']
    token = response.json["access_token"]

    return token
# ...
```

#### Get Keycloak Registrations

With the obtainend access token we can now fetch registration events.
Create a function called `get_keycloak_events()` which will take two arguments (a token and the type of event - in our case a 'registration' event). Passing on a event type will keep things modular and upgradeable if you plan on requesting other event types in the future e.g. login attempts etc.

* Define the function and request the events

```python
#...
def get_keycloak_events(token, event_type):
    token = token
    event_type = event_type
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + str(token),
    }

    response = requests.get(keycloak_data['url'] + 'admin/realms/' +
                            keycloak_data['realm'] + '/events?type=' + event_type, headers=headers)
#...
```

* Check if the response returns a 200 status code

```python
# ...
if response.status_code == 200:
    events = response.json()
    # ...
else:
    print('Error:' + str(response.status_code))
# ...
```

* Create the log file – The file will contain the timestamp of the last event as an reference point.

```python
    # ...
    # Create timestamp.log file
    file = './log/timestamp.log'
    f = open(file, "r")
    # Read lines of the file
    lineList = f.readlines()
    f.close()
    # get the last line
    last_timestamp = lineList[-1]
    # ...
```

* Loop through the events, get the time of the event, convert the UNIX timecode to a human readable time format.
* Subtract the 3 last characters of the timecode to receive a valid UNIX timecode.
* Fetch the email address and user ID and pass them to the email message.

```python
# ...
for event in events:
    try:
        time = event.get('time')
        timestring = str(time)
        unixtimestring = timestring[:-3]
        human_time = datetime.fromtimestamp(int(unixtimestring)).strftime('%Y-%m-%d %H:%M:%S')
        email = event.get('details').get('email')
        user_id = event.get('userId')
        message = 'New Keycloak Event: ' + event_type + \
            ' Time: ' + str(human_time) + ' Email: ' + email + ' User ID: ' + user_id
        # ...
    except:
        continue
    # ...
```

* Compare the time of the current looped event with the last timestamp saved in the `timestamp.log` file.
* If the time value is equal to the last timestamp, there have been no new events and further action is not required, so we can break the loop and print out a short information message.
* If the time value is larger than the last saved timestamp, a email is sent using the `send_mail()` method and the current event timestamp is written to the `timestamp.log` file.

```python
# ...
if time == int(last_timestamp):
    print('No new registrations. Last User registration: Time:' + human_time + ' Email: ' + email + ' User ID: ' + user_id)
    break

elif time > int(last_timestamp):
    print(message)
    send_mail(message, event_type)
    with open(file, "w") as file:
        file.write(str(time))
else:
    print('Error occured')
# ...
```

* For each event a email will be sent in parallel. To avoid beeing marked as spam mail add a time delay of 2 seconds at the end of the for loop.

```python
# ...
sleep(2) # Time in seconds
# ...
```

#### Call the main function

* Last but not least call the main function at the end of the script.
* Pass on the `get_keycloak_token()` and the string value `REGISTER`

```python
# ...
get_keycloak_events(get_keycloak_token(), 'REGISTER')
# ...
```

## The complete Code

```python
import requests
import json
import os
import time
import smtplib

from keycloak import KeycloakAdmin
from time import sleep
from datetime import datetime
from email.message import EmailMessage


# Keycloak credentials
keycloak_username = os.environ['KEYCLOAK_USERNAME']
keycloak_password = os.environ['KEYCLOAK_PASSWORD']
keycloak_url = os.environ['KEYCLOAK_URL']
keycloak_realm = os.environ['KEYCLOAK_REALM']

keycloak_admin = KeycloakAdmin(
    server_url=keycloak_url,
    username=keycloak_username,
    password=keycloak_password,
    realm_name=keycloak_realm,
    verify=True)

keycloak_data = {
    'username': keycloak_username,
    'password': keycloak_password,
    'url': keycloak_url,
    'realm': keycloak_realm,
    'admin': keycloak_admin
}

def get_user(user_id):
    user = keycloak_data['admin'].get_user(user_id)
    return user

def get_keycloak_token():

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = {
        'username': keycloak_data['username'],
        'password': keycloak_data['password'],
        'grant_type': 'password',
        'client_id': 'admin-cli'
    }

    response = requests.post(keycloak_data['url'] + 'realms/' + keycloak_data['realm'] +
                             '/protocol/openid-connect/token', headers=headers, data=data)
    token = response.json()['access_token']
    return token


def send_mail(message, event):

    # SMTP configuration
    sender = os.environ['SMTP_SENDER']
    receiver = os.environ['SMTP_RECEIVER']
    password = os.environ['SMTP_PASSWORD']
    host = os.environ['SMTP_HOST']
    port = os.environ['SMTP_PORT']

    # Email configuration
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = 'New Keycloak Event: ' + event
    msg['From'] = sender
    msg['To'] = receiver

    # Start TLS and send email
    server = smtplib.SMTP(host, port)
    server.ehlo()
    server.starttls()
    server.login(sender, password)
    server.sendmail(
        sender,
        receiver,
        str(msg)
    )
    server.quit()

def get_keycloak_events(token, event_type):
    token = token
    event_type = event_type
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + str(token),
    }

    response = requests.get(keycloak_data['url'] + 'admin/realms/' +
                            keycloak_data['realm'] + '/events?type=' + event_type, headers=headers)

    if response.status_code == 200:
        events = response.json()

        file = './log/timestamp.log'
        f = open(file, "r")
        lineList = f.readlines()
        f.close()
        last_timestamp = lineList[-1]

        for event in events:
            try:
                time = event.get('time')
                timestring = str(time)
                unixtimestring = timestring[:-3]
                human_time = datetime.fromtimestamp(int(unixtimestring)).strftime('%Y-%m-%d %H:%M:%S')
                email = event.get('details').get('email')
                user_id = event.get('userId')
                message = 'New Keycloak Event: ' + event_type + \
                    ' Time: ' + str(human_time) + ' Email: ' + email + ' User ID: ' + user_id

                if time == int(last_timestamp):
                    print('No new registrations. Last User registration: Time:' + human_time + ' Email: ' + email + ' User ID: ' + user_id)
                    break

                elif time > int(last_timestamp):
                    print(message)
                    send_mail(message, event_type)
                    with open(file, "w") as file:
                        file.write(str(time))

                else:
                    print('Error occured')

                sleep(2) # Time in seconds

            except:
                continue
    else:
        print('Error:' + str(response.status_code))

get_keycloak_events(get_keycloak_token(), 'REGISTER')
```

## Deploy and create a Cronjob

Time to deploy the script and create a hourly cronjob using crontab

1. Upload the project directory to the user home directory
2. Open `run.sh' and change` the `$USER`variable to the actual username
3. Copy the script to the hourly cron directory: `sudo cp run.sh /etc/cron.hourly`
4. Navigate to the cron directory: `cd /etc/cron.hourly`
5. Give the script the correct permissions: `sudo chmod 755 run.sh`
6. Add a new cronjob to crontab: `crontab -e`
7. Add following line: `0 * * * * /etc/cron.hourly/run.sh`
8. Save the file and exit.

That's it - the cronjob will trigger the `notifier.sh` script by the hour.
To test if everything works register a new user and run `./notifier.sh`
