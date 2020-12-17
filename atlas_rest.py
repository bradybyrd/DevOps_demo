#------------------------------------------------#
#  Atlas_rest - REST API Atlas examples
#------------------------------------------------#

import sys
import os
import csv
#from collections import OrderedDict
import json
import datetime
import random
import time
import re
import multiprocessing
import pprint
import getopt
#import bson
#from bson.objectid import ObjectId
from bb_util import Util
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth
#from pymongo import MongoClient

'''
#------------------------------------------#
  Notes -
  Call v1 rest api for Atlas
#
'''
settings_file = "rest_settings.json"
bb = Util()

def atlas_org_info():
    url = base_url
    result = rest_get(url)
    bb.message_box("Atlas Org Info", "title")
    pprint.pprint(result)

def atlas_cluster_info():
    url = f'{base_url}/groups/{settings["project_id"]}/clusters'
    result = rest_get(url)
    bb.message_box("Atlas Cluster Info", "title")
    pprint.pprint(result)

def atlas_users():
    url = base_url + f'/groups/{settings["project_id"]}/databaseUsers?pretty=true'
    result = rest_get(url)
    bb.message_box("Atlas User Info", "title")
    pprint.pprint(result)

def atlas_user_add():
    if "user" not in ARGS:
        print("Send user=<user:password>")
        sys.exit(1)
    secret = ARGS["user"]
    pair = secret.split(":")
    role = "read"
    if "role" in ARGS:
        role = ARGS["role"]
    obj = {
      "databaseName" : "admin",
      "roles" : [
        {"databaseName" : "admin", "roleName" : role}
      ],
      "username" : pair[0],
      "password" : pair[1]
    }
    url = base_url + f'/groups/{settings["project_id"]}/databaseUsers?pretty=true'
    result = rest_post(url, {"data" : obj})
    bb.message_box("Response")
    pprint.pprint(result)

def atlas_create_cluster():
    if "template" not in ARGS:
        print("Send template=<template_name>")
        sys.exit(1)
    t_name = ARGS["template"]
    name = f"apiCluster{random.randint(1,20)}"
    if "name" in ARGS:
        name = ARGS["name"]
    provider = "AWS"
    if "cloud" in ARGS:
        provider = ARGS["cloud"].upper()
    template = settings["templates"][provider][t_name.upper()]
    obj = {
      "name" : name,
      "numShards" : 1,
      "replicationFactor" : 3,
      "providerSettings" : {
        "providerName" : provider,
        "regionName" : template["region"],
        "instanceSizeName" : t_name.upper()
      },
      "diskSizeGB" : template["disk_gb"],
      "backupEnabled" : False
    }
    if provider == "AWS":
        obj["providerSettings"]["diskIOPS"] = template["iops"]
    url = base_url + f'/groups/{settings["project_id"]}/clusters?pretty=true'
    result = rest_post(url, {"data" : obj})
    bb.message_box("Response")
    pprint.pprint(result)

def curl_get(url):
  cmd = ["curl","-X","GET","-u",f'{bb.desecret(api_key)}', "--digest", url]
  result = bb.run_shell(cmd)
  jsoninfo = bb.read_json(result.stdout, False)
  return jsoninfo

def curl_post(url, details = {}):
  cur_dir = os.path.dirname(os.path.abspath(__file__))
  tempfile = f'{cur_dir}/data.json'
  post_data = details["data"]
  with open(tempfile, 'w') as outfile:
    json.dump(post_data, outfile, sort_keys=True, indent=4)
  cmd = ["curl","-X","POST","-i","-u",f'{bb.desecret(api_key)}', "--digest", "-H", '"Content-Type: application/json"',url,"--data",f'@{tempfile}']
  time.sleep(1)
  result = bb.run_shell(cmd)
  jsoninfo = {}
  if len(result.stdout) > 3:
      jsoninfo = json.loads(result.stdout.decode('ascii'))
  return jsoninfo

def rest_get(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
  api_pair = bb.desecret(api_key).split(":")
  response = requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers)
  bb.logit(f"Status: {response.status_code}")
  bb.logit(f"Headers: {response.headers}")
  result = response.content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Response: {result}")
  return(json.loads(result))

def rest_post(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
  api_pair = bb.desecret(api_key).split(":")
  post_data = details["data"]
  response = requests.post(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), data=json.dumps(post_data), headers=headers)
  bb.logit(f"Status: {response.status_code}")
  bb.logit(f"Headers: {response.headers}")
  result = response.json() #content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Response: {json.dumps(result)}")
  return(result) #json.loads(result))

def test_shell():
  cmd = ["which", "curl"]
  result = bb.run_shell(cmd)

#------------------------------------------------------------------#
#     MAIN
#------------------------------------------------------------------#
if __name__ == "__main__":
    ARGS = bb.process_args(sys.argv)
    settings = bb.read_json(settings_file)
    api_key = settings["api_key"]
    bb.add_secret(bb.desecret(api_key))

    base_url = settings["base_url"]
    if "action" not in ARGS:
        print("Send action= argument")
        sys.exit(1)
    elif ARGS["action"] == "org_info":
        atlas_org_info()
    elif ARGS["action"] == "user_add":
        atlas_user_add()
    elif ARGS["action"] == "users":
        atlas_users()
    elif ARGS["action"] == "cluster_info":
        atlas_cluster_info()
    elif ARGS["action"] == "create_cluster":
        atlas_create_cluster()
    elif ARGS["action"] == "test":
        test_shell()
    elif ARGS["action"] == "encrypt":
        res = bb.secret(ARGS["secret"])
        bb.logit(f'Encrypted: {res}')
    elif ARGS["action"] == "decrypt":
        res = bb.desecret(ARGS["secret"])
        bb.logit(f'Decrypted: {res}')
    else:
        print(f'{ARGS["action"]} not found')
