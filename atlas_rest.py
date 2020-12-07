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
    result = curl_get(url)
    bb.message_box("Atlas Org Info", "title")
    pprint.pprint(result)

def atlas_cluster_info():
    url = f'{base_url}/groups/{settings["project_id"]}/clusters'
    result = curl_get(url)
    bb.message_box("Atlas Cluster Info", "title")
    pprint.pprint(result)

def atlas_user_add():
    if "user" not in ARGS:
        print("Send user=<user:password>")
        sys.exit(1)
    secret = ARGS["user"]
    pair = secret.split(":")
    obj = {
      "database_name" : "admin",
      "roles" : [
        {"databaseName" : "admin", "roleName" : "MyNewRole"}
      ],
      "username" : pair[0],
      "password" : pair[1]
    }
    url = base_url + f"/groups/{settings["project_id"]}/databaseUsers?pretty=true"
    result = curl_post(url)


def curl_get(url):
  cmd = ["curl","-X","GET","-u",f'{bb.desecret(api_key)}', "--digest", url]
  #curl = f'curl -X GET -u "{api_public_key}:{api_private_key}" --digest -i "{url}"'
  #curl -X GET -u "yclukopd:b8c4f8ee-fada-4edb-8195-00f521974f79" --digest -i "https://cloud.mongodb.com/api/atlas/v1.0"
  result = bb.run_shell(cmd)
  json = bb.read_json(result.stdout, False)
  return json


def curl_post(url, details = {}):
  curl = f'curl -i -u "{bb.desecret(api_key)}" --digest -H "Content-Type: application/json" -X POST "{url}" --data @json_out.txt'
  result = bb.run_shell(curl)
  json = bb.read_json(result, False)
  return json

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
    elif ARGS["action"] == "cluster_info":
        atlas_cluster_info()
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
