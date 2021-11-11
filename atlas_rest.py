#------------------------------------------------#
#  Atlas_rest - REST API Atlas examples
#------------------------------------------------#

import sys
import os
import csv
from collections import OrderedDict
import json
import datetime
import random
import time
import re
import multiprocessing
import pprint
import getopt
import copy
import bson
from bson.objectid import ObjectId
from bb_util import Util
from datetime import datetime
import requests
from requests.auth import HTTPDigestAuth
from pymongo import MongoClient

'''
#------------------------------------------#
  Notes -
  Call v1 rest api for Atlas
#
'''
settings_file = "rest_settings.json"

def atlas_org_info(details = {}):
    url = base_url
    result = rest_get(url)
    if not "quiet" in details:
        bb.message_box("Atlas Org Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_project_info(details = {}):
    url = f'{base_url}/groups'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Projects", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_cluster_info(details = {}):
    result = {"nothing to show here": True}
    project_id = settings["project_id"]
    if "project_id" in details:
        project_id = details["project_id"]
    if "verbose" in ARGS:
        details["verbose"] = True
    if "name" in ARGS:
        cluster_name = ARGS["name"]
        url = f'{base_url}/groups/{project_id}/clusters/{cluster_name}'
    elif "all" in ARGS or "all" in details:
        url = f'{base_url}/clusters'
    else:
        url = f'{base_url}/groups/{project_id}/clusters'
    raw_result = rest_get(url, details) #, {"verbose" : True})
    if "results" in raw_result:
        result = raw_result["results"]
        if "clusters" in raw_result:
            result = result["clusters"]
    else:
        result = raw_result
    if not "quiet" in details:
        bb.message_box("Atlas Cluster Info", "title")
        pprint.pprint(raw_result)
    return result

def atlas_users(details = {}):
    url = base_url + f'/users?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas User Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_database_users(details = {}):
    project_id = settings["project_id"]
    if "project_id" in details:
        project_id = details["project_id"]
    url = base_url + f'/groups/{project_id}/databaseUsers?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas User Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_user_audit(details = {}):
    bb.message_box("User Rights Audit", "title")
    #clusters = atlas_cluster_info({"quiet" : True, "all" : True})
    projects = atlas_project_info({"quiet" : True})
    client = client_connection()
    db = client[settings["database"]]
    collection = "user_audit"
    #  Get a list of departments from cluster metadata
    project_names = {}
    user_rights = []
    clusters = []
    cnt = 0
    bb.logit("#--- Projects ---#")
    bb.logit(f'Logging to: {settings["database"]}.{collection}')
    for item in projects:
        project_names[item["id"]] = item["name"]
        cur_users = atlas_database_users({"quiet" : True, "project_id" : item["id"]})
        bb.logit(f'- {item["name"]}')
        #pprint.pprint(cur_users)
        bulk_docs = []
        for entry in cur_users:
            idoc = OrderedDict()
            idoc["project"] = item["name"]
            idoc["user"] = entry["username"]
            idoc["database_name"] = entry["databaseName"]
            idoc["roles"] = entry["roles"]
            if entry["ldapAuthType"] != "NONE":
                idoc["user_type"] = "ldap"
            elif entry["x509Type"] != "NONE":
                idoc["user_type"] = "x509"
            elif entry["awsIAMType"] != "NONE":
                idoc["user_type"] = "IAM"
            else:
                idoc["user_type"] = "scram"
            idoc["scopes"] = entry["scopes"]
            bulk_docs.append(idoc)
            cnt += 1
        if len(bulk_docs) > 0:
            db[collection].insert_many(bulk_docs)
        bb.logit(f'Inserted: {cnt} audits')
    bb.logit("#------------ All Done ----------------#")


def atlas_private_endpoints(details = {}):
    provider = "AWS"
    if "provider" in ARGS:
        provider = ARGS["provider"]
    url = base_url + f'/groups/{settings["project_id"]}/privateEndpoint/{provider}/endpointService?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    return result

def atlas_private_endpoint_detail(details = {}):
    if "endpoint" in ARGS:
        endpoint = ARGS["endpoint"]
    else:
        print("Send endpoint=<endpoint_id>")
        sys.exit(1)
    if "endpoint_service" in ARGS:
        endpoint_service = ARGS["endpoint_service"]
    else:
        print("Send endpoint_service=<endpoint_service_id>")
        sys.exit(1)
    provider = "AWS"
    if "provider" in ARGS:
        provider = ARGS["provider"]
    url = base_url + f'/groups/{settings["project_id"]}/privateEndpoint/{provider}/endpointService/{endpoint_service}/endpoint/{endpoint}?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    return result

def atlas_project_alerts(details = {}):
    url = base_url + f'/groups/{settings["project_id"]}/alertConfigs?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas Alert Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_billing(details = {}):
    url = base_url + f'/orgs/{settings["org_id"]}/invoices?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas Billing Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_billing_invoice(details = {}):
    if "invoice_id" in ARGS:
        invoice_id = ARGS["invoice_id"]
    else:
        print("Send invoice_id=<invoice_id>")
        sys.exit(1)

    url = base_url + f'/orgs/{settings["org_id"]}/invoices/{invoice_id}?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas Billing Info", "title")
        pprint.pprint(result)
    return result

def atlas_department_accounting(details = {}):
    bb.message_box("Department Accounting", "title")
    #clusters = atlas_cluster_info({"quiet" : True, "all" : True})
    invoices = atlas_billing({"quiet" : True})
    projects = atlas_project_info({"quiet" : True})
    client = client_connection()
    db = client[settings["database"]]
    collection = "invoices"
    idoc = OrderedDict()
    if not "invoice_id" in ARGS:
        bb.logit(f'Current: {invoices[0]["id"]}, Start: {invoices[0]["startDate"]} - {invoices[0]["endDate"]}')
        ARGS["invoice_id"] = invoices[0]["id"]
    billing = atlas_billing_invoice({"quiet" : True})
    #  Get a list of departments from cluster metadata
    project_names = {}
    clusters = []
    bb.logit("#--- Projects ---#")
    for item in projects:
        project_names[item["id"]] = item["name"]
        cur_clusters = atlas_cluster_info({"quiet" : True, "project_id" : item["id"]})
        clusters = clusters + cur_clusters
        bb.logit(f'- {item["name"]}')
    #  Get a list of departments from cluster metadata
    departments = {}
    ipos = 0
    for item in clusters:
        name = f'unknown-{ipos}'
        if "name" in item:
            name = item["name"]
        bb.logit(f'Name: {name}, Labels: ')
        dept = "General"
        if "labels" in item:
            for k in item["labels"]:
                if k["key"] == "department":
                    dept = k["value"]
        bb.logit(f'- {name} => {dept}')
        departments[name] = dept
        ipos += 1
    ipos = 0
    bb.logit("#--- Processing Line Items ---#")
    billing["startDate"] = datetime.datetime.strptime(billing["startDate"],"%Y-%m-%dT%H:%M:%SZ")
    billing["endDate"] = datetime.datetime.strptime(billing["endDate"],"%Y-%m-%dT%H:%M:%SZ")
    for line in billing["lineItems"]:
        dept = "unknown"
        cur = f'unknown-{ipos}'
        if "clusterName" in line:
            cur = line["clusterName"]
        dept = departments[cur] if cur in departments else dept
        billing["lineItems"][ipos]["department"] = dept
        billing["lineItems"][ipos]["project"] = project_names[line["groupId"]]
        billing["version"] = "1.0"
        ipos += 1
        #bb.logit(f'Item: {ipos} - {line["sku"]}')
    ans = db[collection].insert_one(billing)

def updateClusterLabels():
    bb.message_box("Updating Department Accounting", "title")
    #clusters = atlas_cluster_info({"quiet" : True, "all" : True})
    projects = atlas_project_info({"quiet" : True})
    project_names = {}
    clusters = []
    departments = [
        "CodeWizards",
        "CapacityPlanners",
        "MobileExperts",
        "DeepSearchers"
    ]
    bb.logit("#--- Projects ---#")
    for item in projects:
        project_names[item["id"]] = item["name"]
        cur_clusters = atlas_cluster_info({"quiet" : True, "project_id" : item["id"]})
        for clus in cur_clusters:
            dept = random.choice(departments)
            bb.logit(f'- {clus["name"]} => {dept}')
            data = {"labels" : [{"key" : "owner", "value" : item["name"]},{"key" : "department", "value" : dept}]}
            atlas_update_cluster({"project" : clus["groupId"], "name" : clus["name"], "data" : data})


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

def atlas_update_cluster(args = {}):
    if len(args.keys()) == 0:
        args = ARGS
    if "data" not in args:
        print("Send data=\"{json}\"")
        sys.exit(1)
    data = args["data"]
    if "name" not in args:
        print("Send name=<cluster_name>")
        sys.exit(1)
    proj = settings["project_id"]
    if "project" in args:
        proj = args["project"]
    data = args["data"]
    cluster_name = args["name"]
    url = base_url + f'/groups/{proj}/clusters/{cluster_name}?pretty=true'
    result = rest_update(url, {"data" : data})
    bb.message_box("Response")
    pprint.pprint(result)

def atlas_resume_cluster():
    data = {"paused" : False}
    if "name" in ARGS:
        name = ARGS["name"]
    else:
        print("Send name=<cluster_name>")
        sys.exit(1)
    atlas_update_cluster({"name" : name, "data" : data})

def atlas_search_indexes():
    #	/groups/{GROUP-ID}/clusters/{CLUSTER-NAME}/fts/indexes/{DATABASE-NAME}/{COLLECTION-NAME}
    cluster = ARGS["cluster"]
    database = ARGS["database"]
    collection = ARGS["collection"]
    url = f'{base_url}/groups/{settings["project_id"]}/clusters/{cluster}/fts/indexes/{database}/{collection}'
    result = rest_get(url, {"verbose" : True})
    bb.message_box("Atlas Search Index Info", "title")
    pprint.pprint(result)

def rest_get(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
  api_pair = bb.desecret(api_key).split(":")
  response = requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers)
  result = response.content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Status: {response.status_code}")
      bb.logit(f"Headers: {response.headers}")
      bb.logit(f"URL: {url}")
      bb.logit(f"Response: {result}")
  return(json.loads(result))

def rest_post(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
  api_pair = bb.desecret(api_key).split(":")
  post_data = details["data"]
  response = requests.post(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), data=json.dumps(post_data), headers=headers)
  result = response.json() #content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Status: {response.status_code}")
      bb.logit(f"Headers: {response.headers}")
      bb.logit(f"Response: {json.dumps(result)}")
  return(result) #json.loads(result))

def rest_update(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
  api_pair = bb.desecret(api_key).split(":")
  post_data = details["data"]
  if isinstance(post_data, str):
      post_data = json.loads(post_data)
      print(post_data)
  response = requests.patch(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), data=json.dumps(post_data), headers=headers)
  result = response.json() #content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Status: {response.status_code}")
      bb.logit(f"Headers: {response.headers}")
      bb.logit(f"Response: {json.dumps(result)}")
  return(result) #json.loads(result))

def test_shell():
  cmd = ["which", "curl"]
  result = bb.run_shell(cmd)

def template_test():
    # Open a template into a json object and modify it
    cur_temp = copy.deepcopy(settings["templates"]["test"])
    print("Orig")
    pprint.pprint(cur_temp)
    cur_temp["name"] = "NewCluster1"
    cur_temp["providerSettings"]["instanceSizeName"] = "M60"
    print("Mod")
    pprint.pprint(cur_temp)
    print("Parent")
    pprint.pprint(settings["templates"]["test"])

def atlas_online_archive():
    # POST /groups/{GROUP-ID}/clusters/{CLUSTER-NAME}/onlineArchives
    if "json" not in ARGS:
        print("Send json=<file_path>")
        sys.exit(1)
    tname = ARGS["json"]
    tinfo = bb.read_json(tname)
    url = base_url + f'/groups/{settings["project_id"]}/clusters/{settings["cluster_name"]}/onlineArchives'
    result = rest_post(url, {"data" : tinfo})
    bb.message_box("Response")
    pprint.pprint(result)


def json_template(temp_type):
    if not temp_type.endsWith(".json"):
        temp_type = temp_type + ".json"
    ppath = f'{base_path}/{temp_type}'
    result = bb.read_json(ppath)
    return(copy.deepcopy(result))

def client_connection(type = "uri", details = {}):
    mdb_conn = settings[type]
    username = settings["username"]
    password = settings["password"]
    if "username" in details:
        username = details["username"]
        password = details["password"]
    mdb_conn = mdb_conn.replace("//", f'//{username}:{password}@')
    bb.logit(f'Connecting: {mdb_conn}')
    if "readPreference" in details:
        client = MongoClient(mdb_conn, readPreference=details["readPreference"]) #&w=majority
    else:
        client = MongoClient(mdb_conn)
    return client

#------------------------------------------------------------------#
#     MAIN
#------------------------------------------------------------------#
if __name__ == "__main__":
    bb = Util()
    ARGS = bb.process_args(sys.argv)
    settings = bb.read_json(settings_file)
    api_key = settings["api_key"]
    bb.add_secret(bb.desecret(api_key))
    base_path = os.path.dirname(os.path.abspath(__file__))

    base_url = settings["base_url"]
    if "action" not in ARGS:
        print("Send action= argument")
        sys.exit(1)
    elif ARGS["action"] == "org_info":
        atlas_org_info()
    elif ARGS["action"] == "org_projects":
        atlas_project_info()
    elif ARGS["action"] == "alert_settings":
        atlas_project_alerts()
    elif ARGS["action"] == "private_links":
        atlas_private_endpoints()
    elif ARGS["action"] == "private_link":
        atlas_private_endpoint_detail()
    elif ARGS["action"] == "billing":
        atlas_billing()
    elif ARGS["action"] == "billing_invoice":
        atlas_billing_invoice()
    elif ARGS["action"] == "department_accounting":
        atlas_department_accounting()
    elif ARGS["action"] == "user_add":
        atlas_user_add()
    elif ARGS["action"] == "users":
        atlas_users()
    elif ARGS["action"] == "database_users":
        atlas_database_users()
    elif ARGS["action"] == "user_audit":
        atlas_user_audit()
    elif ARGS["action"] == "cluster_info":
        atlas_cluster_info()
    elif ARGS["action"] == "create_cluster":
        atlas_create_cluster()
    elif ARGS["action"] == "update_cluster":
        atlas_update_cluster()
    elif ARGS["action"] == "resume":
        atlas_resume_cluster()
    elif ARGS["action"] == "update_cluster_labels":
        updateClusterLabels()
    elif ARGS["action"] == "online_archive":
        atlas_online_archive()
    elif ARGS["action"] == "search_indexes":
        # cluster, database, collection
        atlas_search_indexes()
    elif ARGS["action"] == "test":
        template_test()
    elif ARGS["action"] == "encrypt":
        res = bb.secret(ARGS["secret"])
        bb.logit(f'Encrypted: {res}')
    elif ARGS["action"] == "decrypt":
        res = bb.desecret(ARGS["secret"])
        bb.logit(f'Decrypted: {res}',"SECRET")
    else:
        print(f'{ARGS["action"]} not found')



#------------------- Not Used ------------------------#

def curl_get(url):
  cmd = ["curl","-X","GET","-u",f'{bb.desecret(api_key)}', "--digest", url]
  result = bb.run_shell(cmd)
  jsoninfo = bb.read_json(result.stdout, False)
  return jsoninfo

def curl_post(url, details = {}):
  tempfile = f'{base_path}/data.json'
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
