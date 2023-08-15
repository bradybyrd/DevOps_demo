#------------------------------------------------#
#  Atlas_rest - REST API Atlas examples
#------------------------------------------------#

import sys
import os
import csv
from collections import OrderedDict
import json
import datetime as dt
import random
import pathlib
import time
import re
import multiprocessing
import pprint
import getopt
import copy
import pymongo
import bson
from bson.objectid import ObjectId
from mdb_util import Util
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
temp_settings_file = f'temp_settings_{dt.datetime.now().strftime("%m%d%Y%H%M%S")}'

def atlas_org_details(details = {}):
    url = base_url
    result = rest_get(url)
    if not "quiet" in details:
        bb.message_box("Atlas Org Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_org_info(details = {}):
    url = f'{base_url}/orgs'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Organizations", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_project_info(details = {}):
    url = f'{base_url}/groups'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Projects", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_project_info_name(details = {}):
    name=details['project_name']
    #url = f'{base_url}/groups/{name}'
    url = f'{base_url}/groups/byName/{name}'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Projects", "title")
        pprint.pprint(result)
    return result
    
def atlas_project_check(project_name = ""):
    if "project_id" in tempsettings:
        result = tempsettings["project_id"]
    else:
        if project_name == "":
            project_name = get_setting("project_name", {"env" : "Atlas_Project_Name"})
        answer = atlas_project_info_name({"project_name" : project_name})
        if "id" in answer:
            p_status = answer["id"]
        else:
            p_status = "NEW"
    temp_settings("set",{"project_id" : p_status})
    return p_status
               
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
    elif "name" in details:
        cluster_name = details["name"]
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
    url = base_url + f'/orgs/{settings["org_id"]}/users?pretty=true'
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
    org_users = atlas_users({"quiet" : True})
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
        cur_clusters = atlas_cluster_info({"quiet" : True, "project_id" : item["id"]})
        clusters = clusters + cur_clusters
        bb.logit(f'Collecting clusters - {item["name"]}')

    bulk_docs = []
    for entry in org_users:
        idoc = OrderedDict()
        idoc["type"] = "org_user"
        idoc["email"] = entry["emailAddress"]
        idoc["user"] = f'{entry["firstName"]} {entry["lastName"]}'
        idoc["id"] = entry["id"]
        org_privs = []
        access = []
        idoc["all_access"] = False
        for item in entry["roles"]:
            if "orgId" in item:
                org_privs.append(item["roleName"])
                if item["roleName"] == "ORG_OWNER":
                    idoc["all_access"] = True
                    access.append({"project" : "ALL PROJECTS", "info" : "ALL PROJECTS, ALL CLUSTERS - ORG_OWNER", "cluster" : "ALL CLUSTERS", "role" : item["roleName"]})
                else:
                    idoc["all_access"] = False
                    access.append({"project" : "ALL PROJECTS", "info" : f'ALL PROJECTS, ALL CLUSTERS - {item["roleName"]}', "cluster" : "ALL CLUSTERS", "role" : item["roleName"]})
            else: #Project Access
                for inst in clusters:
                    if item["groupId"] == inst["groupId"]:
                        project = project_names[inst["groupId"]]
                        rights = f'{project} - {item["roleName"]}'
                        info = f'{rights}, {inst["name"]}(v{inst["mongoDBVersion"]}) - {inst["stateName"]}'
                        idoc["all_access"] = False
                        access.append({"project" : project, "info" : info, "role" : item["roleName"], "cluster" : inst["name"], "provider_settings" : inst["providerSettings"], "version" : inst["mongoDBVersion"]})
            cnt += 1
        bb.logit(f'{idoc["user"]} - Inserted: {cnt} audits')
        idoc["cluster_access"] = access
        bulk_docs.append(idoc)
    if len(bulk_docs) > 0:
        db[collection].insert_many(bulk_docs)
    bb.logit("#------------ All Done ----------------#")

def atlas_db_user_audit(details = {}):
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
            idoc["type"] = "db_user"
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

def atlas_private_endpoint_svc(details = {}):
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/privateEndpoint/{cloudProvider}/endpointService/{endpointServiceId}
    provider = "AWS"
    if "provider" in details:
        provider = details["provider"]
    if "endpoint_svc_id" in details:
        svc_id = details["endpoint_svc_id"]
    if "provider" in ARGS:
        provider = ARGS["provider"]
    if "svc_id" in ARGS:
        svc_id = ARGS["svc_id"]
    if "project_id" in details:
        project_id = details["project_id"]
    url = base_url + f'/groups/{project_id}/privateEndpoint/{provider}/endpointService/{svc_id}'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box(f"Atlas PrivateLink Info - {svc_id}", "title")
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

def atlas_create_private_endpoint_svc(details = {}):
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/privateEndpoint/endpointService
    provider = "AWS"
    region = "US_EAST_1"
    project_id = settings["project_id"]
    if "provider" in ARGS:
        provider = ARGS["provider"]
    if "region" in ARGS:
        region = ARGS["region"]
    if "provider" in details:
        provider = details["provider"]
    if "region" in details:
        region = details["region"]
    if "project_id" in details:
        project_id = details["project_id"]
    url = base_url + f'/groups/{project_id}/privateEndpoint/endpointService'
    payload = {"providerName" : provider, "region" : region}
    result = rest_post(url, {"data" : payload})
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    for i in range(5):
        bb.logit("Waiting for endpoint creation...")
        time.sleep(30)
        result2 = atlas_private_endpoint_svc({"provider" : provider, "endpoint_svc_id" : result["id"], "project_id" : project_id})
        pprint.pprint(result2)
        if result2["status"] == "AVAILABLE":
            break
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLink Details", "title")
        pprint.pprint(result2)
    if provider == "AZURE":
        payload = result2
        # TODO - get the extras vnet etc into payload
        #azure_create_private_endpoint(payload)
    temp_settings("set",{"pe_service_id" : result["id"]})
    return result2
    
def azure_create_private_endpoint(details = {}):    
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/privateEndpoint/{cloudProvider}/endpointService/{endpointServiceId}/endpoint
    provider = "AZURE"
    project_id = settings["project_id"]
    bb.message_box("completing PE steps" , "Title")
    project_id = atlas_project_check()
    if "Resource_Group" in os.environ:
        rg=os.environ.get("Resource_Group")
        resource_name = settings["privatelink"][rg]["RG"]
        vnet_name = settings["privatelink"][rg]["vnet"]
        region=rg[rg.find("US_"):len(rg)]
        subnet = settings["privatelink"][rg]["subnet"]    
        #service_id = f'{rg}_'
        do_fetch = True
    pe_resource_id = get_setting("pe_resource_id",{"env" : "PE_Resource_ID", "error" : True})
    if "PE_Resource_ID" in os.environ:
        pe_resource_id = os.environ.get("PE_Resource_ID")
    else:
        bb.logit("error-missing PE_Resource_ID")
        sys.exit(1)
    if "PE_SVCID" in os.environ:
        pe_svcid = os.environ.get("PE_SVCID")
    else:
        bb.logit("error-missing PE_SVCID")
        sys.exit(1)
    if "PE_IP" in os.environ:
        cidr=os.environ.get("PE_IP")
    else:
        bb.logit("For azure - add cidr=<IPAddress>")
        sys.exit(1)
    url = base_url + f'/groups/{project_id}/privateEndpoint/{provider}/endpointService/{pe_svcid}/endpoint'
    bb.logit(f"ServiceURL: {url}")
    payload = {"id" : pe_resource_id}
    if provider == "AZURE":
        payload["privateEndpointIPAddress"] = cidr
    result = rest_post(url, {"data" : payload})
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    return result

def azure_create_private_endpoint_service(details = {}):
    # Use azure CLI to create PE
    '''
    python3 atlas_rest.py action azure_cli_command service_id=64505410cdbca3236596c2cd resource_name=BB-DEVOps_group vnet_name=BradyDevOps subnet=default
    resource_name
    vnet_name
    subnet_namecreate
    Result from rest call:
    {'errorMessage': None,
    'id': '64505410cdbca3236596c2cd',
    'privateEndpoints': [],
    'privateLinkServiceName': 'pls_64505410cdbca3236596c2cd',
    'privateLinkServiceResourceId': '/subscriptions/52f0a73e-87fd-4b87-bc73-b76cbda361ee/resourceGroups/rg_64503bf4f695331ad04754fa_4atbmuhb/providers/Microsoft.Network/privateLinkServices/pls_64505410cdbca3236596c2cd',
    'regionName': 'US_EAST_2',
    'status': 'AVAILABLE'}
    az network vnet subnet update --resource-group resource-group-name --vnet-name vnet-name --name subnet-xxxx1 --disable-private-endpoint-network-policies true
    endpoint_name

    az network private-endpoint create --resource-group resource-group-name --name endpoint-name --vnet-name vnet-name --subnet subnet-xxxx1 --private-connection-resource-id /subscriptions/52f0a73e-87fd-4b87-bc73-b76cbda361ee/resourceGroups/rg_64503bf4f695331ad04754fa_epc7hkvk/providers/Microsoft.Network/privateLinkServices/pls_64503bf4f695331ad04754f9 --connection-name pls_64503bf4f695331ad04754f9 --manual-request true
    '''
    provider = "AZURE"
    project_id = settings["project_id"]
    if "Atlas_Project_Name" in os.environ:
        project_name=os.environ.get("Atlas_Project_Name")
        answer=atlas_project_info_name({"project_name" : project_name})
        project_id=answer["id"]
    else:
        project_id = os.environ.get("Atlas_Project_Id")
    if "Resource_Group" in os.environ:
        rg=os.environ.get("Resource_Group")
        resource_name = settings["privatelink"][rg]["RG"]
        vnet_name = settings["privatelink"][rg]["vnet"]
        region=rg[rg.find("US_"):len(rg)]
        subnet = settings["privatelink"][rg]["subnet"]    
        #service_id = f'{rg}_'
        do_fetch = True
    else:
        if "privateLinkServiceName" in details:
            svc_id = details["privateLinkServiceName"]
            resource_id = details["privateLinkServiceResourceId"]
            resource_name = details["resource_name"]
            vnet_name = details["vnet_name"]
            subnet = details["subnet"]
            do_fetch = False
        else:
            bb.logit("Pass results from private_link_svc call")
            sys.exit(1)
    if do_fetch:
        results = atlas_create_private_endpoint_svc({"provider" : provider, "region" : region, "project_id" : project_id})
        svc_id = results["privateLinkServiceName"]
        resource_id = results["privateLinkServiceResourceId"]
    endpoint_name = f"pe_az_shub_{region}_{project_name}"
                    
    disabler = f"network vnet subnet update --resource-group {resource_name} --vnet-name {vnet_name} --name {subnet} --disable-private-endpoint-network-policies true"
    template = f"network private-endpoint create --resource-group {resource_name} --name {endpoint_name} --vnet-name {vnet_name} --subnet {subnet} --private-connection-resource-id {resource_id} --connection-name {svc_id} --manual-request true"
    bb.logit("# ----------------------- Azure CLI Commands -------------------------- #")
    print(disabler)
    print(" -------------------------- ")
    print(template)
    with open (f"{os.environ.get('WORKSPACE')}/disabler.txt" , "w") as fil:
        fil.write(disabler)
    with open (f"{os.environ.get('WORKSPACE')}/pe-template.txt" , "w") as fil:
        fil.write(template)
    return({"disabler" : disabler, "endpoint" : template})

def gcp_create_private_endpoint(details = {}):
    test = "true"

def gcp_create_kms_encryption(details = {}):
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/encryptionAtRest
    atlas_organization_name = os.environ.get("Atlas_Organization_Name")
    key_resource_id = os.environ.get("Key_Version_Resource_ID")
    with open(os.environ.get("SECRET_FILE")) as secretfile:
        service_account_key = secretfile.read()
    project_id = atlas_project_check()
    payload = {"googleCloudKms" : {
        "enabled": True,
        "keyVersionResourceID": key_resource_id,
        "serviceAccountKey": service_account_key
    }}
    url = base_url + f'/groups/{project_id}/encryptionAtRest'
    result = rest_update(url, {"data" : payload, "org":atlas_organization_name})
    if not "quiet" in details:
        bb.message_box("Atlas GCP-KMS Encryption Info", "title")
        #print(payload)
        print("----------------------------------------------------")
        pprint.pprint(result)
    return result

def kms_encryption_key_settings():
    project_id = atlas_project_check()
    org=os.environ.get("Atlas_Organization_Name")
    skey="sa_prod_key"
    isnonprod = "nonprod" in project_name.lower().replace("-", "")
    if isnonprod:
        skey="sa_nonprod_key"
    bb.logit(f'using_key {org}-{settings["atlas_organization"][org][skey]}')
    with open (f"{os.environ.get('WORKSPACE')}/skey_status.txt" , "w") as fil:
            fil.write(settings["atlas_organization"][org][skey])

def atlas_kms_encryption(details = {}):
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/encryptionAtRest
    url = base_url + f'/groups/{settings["project_id"]}/encryptionAtRest'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas KMS Encryption Info", "title")
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
    billing["startDate"] = dt.datetime.strptime(billing["startDate"],"%Y-%m-%dT%H:%M:%SZ")
    billing["endDate"] = dt.datetime.strptime(billing["endDate"],"%Y-%m-%dT%H:%M:%SZ")
    for line in billing["lineItems"]:
        dept = "unknown"
        cur = f'unknown-{ipos}'
        if "clusterName" in line:
            cur = line["clusterName"]
        dept = departments[cur] if cur in departments else dept
        billing["lineItems"][ipos]["department"] = dept
        proj = "unknown/deleted"
        if line["groupId"] in project_names:
            proj = project_names[line["groupId"]]
        billing["lineItems"][ipos]["project"] = proj
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


def atlas_user_add(details={}):
    role = "readWriteAnyDatabase"
    if "user" in details:
        secret=details["user"]
    elif "user" in ARGS:
        secret = ARGS["user"]
    elif "DB_Users" in os.environ:
        secret = os.environ["DB_Users"]
        pair = secret.split("|")
        role = pair[1]
        secret = pair[0]
    if "project_id" in details:
        project_id = details["project_id"]
    else:
        project_id = settings["project_id"]
    pair = secret.split(":")
    if "role" in ARGS:
        role = ARGS["role"]
    elif "role" in details:
        role = details["role"]
    obj = {
      "databaseName" : "admin",
      "roles" : [
        {"databaseName" : "admin", "roleName" : role}
      ],
      "username" : pair[0],
      "password" : pair[1]
    }
    url = base_url + f'/groups/{project_id}/databaseUsers?pretty=true'
    result = rest_post(url, {"data" : obj})
    bb.message_box("Response")
    pprint.pprint(result)

def atlas_project_user_add(project_id="", dba_email=""):
    if "user" not in ARGS and dba_email=="":
        print("Send user=<useremail>")
        sys.exit(1)
    else:
        user=dba_email
    if project_id=="":
        project_id=settings["project_id"]
    role = "GROUP_OWNER"
    if "role" in ARGS:
        role = ARGS["role"]
    obj = {
      "roles" : [
        role
      ],
      "username" : user
    }
    url = base_url + f'/groups/{project_id}/invites?pretty=true'
    result = rest_post(url, {"data" : obj})
    bb.message_box("Response")
    pprint.pprint(result)

def atlas_create_full_project():
    result=atlas_create_project()
    project_id=result["id"]
    atlas_user_add({"user" : "mongodbadmin:Cvs" , "role" : "atlasAdmin" , "project_id" : project_id})
    atlas_user_add({"user" : "atlasappuser:W#lcome123" , "role" : "readWriteAnyDatabase" , "project_id" : project_id})
    for dba in settings["dba_email"]:
        atlas_project_user_add(project_id, dba)

def atlas_create_cluster():
    if "Atlas_Project_Name" in os.environ:
        project_name=os.environ.get("Atlas_Project_Name")
        answer=atlas_project_info_name({"project_name" : project_name})
        project_id=answer["id"]
    else:
        project_id = os.environ.get("Atlas_Project_Id")
    
    if "Atlas_Organization_Name" in os.environ:
        org_id = os.environ.get("Atlas_Organization_Name")
    else:
        org_id=settings["org_id"]
    
    if "template" in ARGS:
        template = ARGS["template"]
    else:
        template=os.environ.get("Template")
    tier = settings["templates"][template]["tier"]
    provider = settings["templates"][template]["provider"]
    region = settings["templates"][template]["region"]
    disk_size = settings["templates"][template]["disk_gb"]
    name=os.environ["Cluster_Name"]
    if os.environ["Disk_size"] != "":
        disk_size=int(os.environ["Disk_size"])
    cluster_config = {
        "name" : name,
        "numShards" : 1,
        "replicationFactor" : 3,
        "providerSettings" : {
            "providerName" : provider,
            "regionName" : region,
            "instanceSizeName" : tier
        },
        "diskSizeGB" : disk_size,
        "backupEnabled" : False
    }
    url = base_url + f'/groups/{project_id}/clusters?pretty=true'
    result = rest_post(url, {"data" : cluster_config, "org": org_id })
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

def atlas_pause_cluster():
    atlas_resume_cluster(True)

def atlas_resume_cluster(pause_state = False):
    data = {"paused" : pause_state}
    if "name" in ARGS:
        name = ARGS["name"]
    else:
        print("Send name=<cluster_name>")
        sys.exit(1)
    atlas_update_cluster({"name" : name, "data" : data})

def atlas_create_project():
    name = get_setting("project_name", {"arg" : "project_name", "env" : "Atlas_Project_Name"})
    if "project_name" not in ARGS:
        if "Atlas_Project_Name" in os.environ:
            name=os.environ.get("Atlas_Project_Name")
    else:
        name=ARGS["project_name"]
    if "Atlas_Organization_Name" in os.environ:
        org_id = settings["atlas_organization"][os.environ["Atlas_Organization_Name"]]["org_id"]
    else:
        org_id=settings["org_id"] 
    project_config={"name" : name, "orgId" : org_id, "withDefaultAlertsSettings" : True}
    url = base_url + f'/groups?pretty=true'
    result = rest_post(url, {"data" : project_config})
    bb.message_box("Response")
    pprint.pprint(result)
    return result

def atlas_search_indexes():
    #	/groups/{GROUP-ID}/clusters/{CLUSTER-NAME}/fts/indexes/{DATABASE-NAME}/{COLLECTION-NAME}
    cluster = ARGS["cluster"]
    database = ARGS["database"]
    collection = ARGS["collection"]
    url = f'{base_url}/groups/{settings["project_id"]}/clusters/{cluster}/fts/indexes/{database}/{collection}'
    result = rest_get(url, {"verbose" : True})
    bb.message_box("Atlas Search Index Info", "title")
    pprint.pprint(result)

def atlas_search_index_detail():
    #	GET /groups/{GROUP-ID}/clusters/{CLUSTER-NAME}/fts/indexes/{INDEX-ID}
    cluster = ARGS["cluster"]
    index_id = ARGS["id"]
    url = f'{base_url}/groups/{settings["project_id"]}/clusters/{cluster}/fts/indexes/{index_id}'
    result = rest_get(url, {"verbose" : True})
    bb.message_box("Atlas Search Index Info", "title")
    pprint.pprint(result)

def atlas_search_hw_metrics():
    #	/groups/{GROUP-ID}/hosts/{PROCESS-ID}/fts/metrics
    process_id = ARGS["process"]
    url = f'{base_url}/groups/{settings["project_id"]}/hosts/{process_id}/fts/metrics/measurements?granularity=PT1M&period=PT1M'
    result = rest_get(url, {"verbose" : True})
    bb.message_box("Atlas Search Index Info", "title")
    pprint.pprint(result)

def atlas_search_metrics():
    #	GET /groups/{GROUP-ID}/hosts/{PROCESS-ID}/fts/metrics/indexes/{DATABASE-NAME}/{COLLECTION-NAME}/measurements
    process_id = ARGS["process"]
    database = ARGS["database"]
    collection = ARGS["collection"]
    url = f'{base_url}/groups/{settings["project_id"]}/hosts/{process_id}/fts/metrics/indexes/{database}/{collection}/measurements?granularity=PT1M&period=PT1M'
    result = rest_get(url, {"verbose" : True})
    bb.message_box("Atlas Search Index Info", "title")
    pprint.pprint(result)


def atlas_log_files(details = {"verbose" : True}):
    '''
    Get log files every xx minutes and push to mongo
    '''
    cluster = "M10BasicAgain"
    log_dir = settings["log_path"]
    start_time = dt.datetime.now() - dt.timedelta(minutes=15)
    end_time = dt.datetime.now()
    bb.message_box(f'Fetching Atlas logs for {start_time.strftime("%m/%d/%Y")}, {cluster} between {start_time.strftime("%H:%M:%S")}-{end_time.strftime("%H:%M:%S")}', "title")
    path = pathlib.Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    result = atlas_cluster_info({"name" : cluster, "quiet" : True})
    c_string = result["connectionStrings"]["standard"]
    members = c_string.split(",")
    for node in members:
        host = node.replace("mongodb://","")
        host = re.sub("\:27017.*","",host)
        get_log_file(host, start_time, end_time, log_dir, details)


def get_log_file(cluster, start, end, log_path, details = {}):
    '''
    curl --user '{PUBLIC-KEY}:{PRIVATE-KEY}' --digest \
 --header 'Accept: application/gzip' \
 --request GET "https://protect-us.mimecast.com/s/li3WCXD2MOiqPAL2qIkE-by?domain=cloud.mongodb.com<unixepoch>" \
 --output "mongodb.gz
    '''
    details["headers"] = {"Content-Type" : "application/json", "Accept" : "application/gzip" }
    unixstart = dt.datetime(1970,1,1)
    #start_date = int((start - unixstart).total_seconds())
    #end_date = int((end - unixstart).total_seconds())
    start_date = int(start.timestamp())
    end_date = int(end.timestamp())
    fil = f'log_{cluster}_{end_date}.gz'
    file_path = os.path.join(log_path, fil)
    details["filename"] = file_path
    if not "quiet" in details:
        bb.logit(f'Node: {cluster}, Saving: {fil}')
    url = f'{base_url}/groups/{settings["project_id"]}/clusters/{cluster}/logs/mongodb.gz?startDate={start_date}&endDate={end_date}'
    result = rest_get_file(url, details)
    if not "quiet" in details:
        pprint.pprint(result)
    return result #result["results"]

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

#------------------------------------------------------------------#
#     REST METHODS
#------------------------------------------------------------------#

def get_api_key(details = {}):
    org=''
    if "org" in details:
        org=details["org"]
    if org=='':
        result=api_key
    else:
        result=settings['atlas_organization'][org]["api_key"]
    #bb.logit(f"api_key: {api_key}")
    return result

def rest_get(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
  if "headers" in details:
      headers = details["headers"]
  cur_api_key=get_api_key(details)
  api_pair = bb.desecret(cur_api_key).split(":")
  #api_pair = [os.environ["API_USER"],os.environ["API_SECRET"]]
  #print (f'key: {api_pair[0]}:{api_pair[1]}')
  response = requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers)
  result = response.content.decode('ascii')
  if "verbose" in details:
      bb.logit(f"Status: {response.status_code}")
      bb.logit(f"Headers: {response.headers}")
      bb.logit(f"URL: {url}")
      bb.logit(f"Response: {result}")
  return(json.loads(result))

def rest_get_file(url, details = {}):
  # https://protect-us.mimecast.com/s/V_7rCYENMPINWYyMNhMTkLH?domain=stackoverflow.com
  headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
  if "headers" in details:
      headers = details["headers"]
  cur_api_key=get_api_key(details)
  api_pair = bb.desecret(cur_api_key).split(":")
  local_filename = details["filename"]
  try:
      response = requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers, stream=True)
  except Exception as e:
      print(e)
  raw = response.raw
  with open(local_filename, 'wb') as out_file:
    cnt = 1
    while True:
        chunk = raw.read(1024, decode_content=True)
        if not chunk:
            break
        bb.logit(f'chunk-{cnt}')
        out_file.write(chunk)
        cnt += 1
  '''
  with requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers, stream=True) as r:

    r.raise_for_status()
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            # If you have chunk encoded response uncomment if
            # and set cperfhunk_size parameter to None.
            #if chunk:
            f.write(chunk)
  '''
  if "verbose" in details:
      bb.logit(f"URL: {url}")
  return(local_filename)

def rest_post(url, details = {}):
  headers = {"Content-Type" : "application/json", "Accept" : "application/json"}
  if "headers" in details:
      headers = details["headers"]
  cur_api_key=get_api_key(details)
  api_pair = bb.desecret(cur_api_key).split(":")
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
  cur_api_key=get_api_key(details)
  api_pair = bb.desecret(cur_api_key).split(":")
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
   
def rest_get_url():
    url = ARGS["url"]
    key = ARGS["key"]
    secret = ARGS["secret"]
    headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
    response = requests.get(url, auth=HTTPDigestAuth(key, secret), headers=headers)
    result = response.content.decode('ascii')
    bb.logit(f"Status: {response.status_code}")
    bb.logit(f"Headers: {response.headers}")
    bb.logit(f"URL: {url}")
    bb.logit(f"Response: {result}")
    return(json.loads(result))


def rest_get_ip():

    url="https://protect-us.mimecast.com/s/STFvCW6X8NfPL3nOPSKVMC2?domain=api.ipify.org"
    response = requests.get(url,headers={"User-Agent": "Test-Agent"})
    result = response.content.decode('ascii')
    bb.logit(f"URL: {url}")
    bb.logit(f"Response: {result}")
    pprint.pprint(result)

#------------------------------------------------------------------#
#     UTILITY METHODS
#------------------------------------------------------------------#

def shell_test():
    bb.run_shell(["pwd" , ""])
    bb.run_shell(["./azlogin.sh" , ""])
    #bb.run_shell(["az" , "--version"])
    #bb.run_shell(["gcloud" , "--version"])

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

def temp_settings(action="get", data={}):
    json_file = os.path.join(base_path, temp_settings_file)
    if action == "get":
        tempsettings = read_temp_settings()
    elif action == "set":
        tempsettings = read_temp_settings()
        for item in data:
            tempsettings[item] = data[item]
        with open(json_file, 'w') as outfile:
                json.dump(tempsettings, outfile)
    return tempsettings

def get_setting(setting, details = {}):
    # Cascade through this
    # details = {"env" : "Project_Name"}
    result = "none"
    if "arg" in details and details["arg"] in ARGS:
        result=ARGS[details["arg"]]
    elif "env" in details and details["env"] in os.env:
        result=os.environ.get(details["env"])
    else:
        if setting in tempsettings:
            result = tempsettings[setting]
        elif setting in settings:
            result = settings[setting]
    if "error" in details:
        bb.logit(f'ERROR: missing {setting}')
        sys.exit(1)
    return result

def read_temp_settings():
    tempsettings = bb.read_json(os.path.join(base_path, temp_settings_file))
    return tempsettings

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
    base_path = os.path.dirname(os.path.abspath(__file__))
    settings = bb.read_json(os.path.join(base_path, settings_file))
    tempsettings = {}
    if "Atlas_Organization_Name" in os.environ:
        api_key = settings["atlas_organization"][os.environ["Atlas_Organization_Name"]]["api_key"]
    else:
        api_key = settings["api_key"]
    bb.add_secret(bb.desecret(api_key))

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
    elif ARGS["action"] == "db_user_audit":
        atlas_db_user_audit()
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
    elif ARGS["action"] == "search_index":
        atlas_search_index_detail()
    elif ARGS["action"] == "search_hw_metrics":
        atlas_search_hw_metrics()
    elif ARGS["action"] == "search_metrics":
        atlas_search_metrics()
    elif ARGS["action"] == "logs":
        atlas_log_files()
    elif ARGS["action"] == "test":
        template_test()
    elif ARGS["action"] == "encrypt":
        res = bb.secret(ARGS["secret"])
        bb.logit(f'Encrypted: {res}')
    elif ARGS["action"] == "decrypt":
        res = bb.desecret(ARGS["secret"])
        bb.logit(f'Decrypted: {res}',"SECRET")
    elif ARGS["action"] == "get_url":
        rest_get_url()
    elif ARGS["action"] == "project_info":
        atlas_project_info()
    elif ARGS["action"] == "project_create":
        atlas_create_project()
    elif ARGS["action"] == "create_full_project":
        atlas_create_full_project()
    elif ARGS["action"] == "project_user_add":
        atlas_project_user_add()
    elif ARGS["action"] == "create_kms_encryption":
        gcp_create_kms_encryption()
    elif ARGS["action"] == "project_check":
        atlas_project_check()
    elif ARGS["action"] == "create_private_endpoint_service":
        azure_create_private_endpoint_service()
    elif ARGS["action"] == "azure_create_private_endpoint":
        azure_create_private_endpoint()
    elif ARGS["action"] == "kms_encryption_key_settings":
        kms_encryption_key_settings()
    elif ARGS["action"] == "shell_test":
        shell_test()
    else:
        print(f'{ARGS["action"]} not found')
