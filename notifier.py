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


def add_user_to_group(user):

    # Get organisation from user attribute

    organisation = user.get('attributes').get('organisation')[0]

    path = '/' + organisation
    parent = keycloak_data['admin'].get_group_by_path(path='/partners', search_in_subgroups=False)

    # Create group if does not exist
    keycloak_data['admin'].create_group(payload={'name': organisation, 'path': path}, parent=parent['id'], skip_exists=True)

    # Get group using organisation attribute
    group = keycloak_data['admin'].get_group_by_path(path='/partners/' + str(organisation), search_in_subgroups=True)

    # Add User to group
    keycloak_data['admin'].group_user_add(user['id'], group['id'])

    print('Adding ' +
            user['email'] + ' to group: ' + organisation)


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

        # read a text file as a list of lines
        # find the last line, change to a file you have
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
                    add_user_to_group(get_user(user_id))
                    print(message)
                    send_mail(message, event_type)
                    
                    with open(file, "w") as file:
                        file.write(str(time))



                else:
                    print('Error occured')

                sleep(2) # Time in seconds.dd

            except:
                continue
    else:
        print('Error:' + str(response.status_code))

get_keycloak_events(get_keycloak_token(), 'REGISTER')
