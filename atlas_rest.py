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
import git
import urllib
import getopt
import copy
import bson
from bson.objectid import ObjectId
from bb_util import Util
import requests
from requests.auth import HTTPDigestAuth
from pymongo import MongoClient
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

'''
#------------------------------------------#
  Notes -
  Call v1 rest api for Atlas
#
'''

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

def atlas_project_detail(details = {}):
    project_id = settings["project_id"]
    if "project_id" in ARGS:
        project_id = ARGS["project_id"]
    url = f'{base_url}/groups/{project_id}'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Projects", "title")
        pprint.pprint(result)
    return result

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

def atlas_cluster_audit():
    #  Loops through orgs and projects to get details on each cluster and push to atlas
    orgs = settings["organizations"]
    bulk_docs = []
    icnt = 0
    bb.message_box("Atlas Cluster Audit","title")
    for org in orgs:
        bb.message_box(f'Organization: {org}')
        org_info = {"organization" : org, "id" : orgs[org]["org_id"], "api_key" : orgs[org]["api_key"]}
        result = atlas_project_info(org_info)
        if "name" not in result[0]:
            bb.logit('Failed to get info for org - check API key access')
            next
        for proj in result:
            bb.logit(f'Clusters: [{proj["clusterCount"]}]')
            doc = {"organization" : org, "org_id" : org_info["id"], "project" : proj["name"], "project_id" : proj["id"]}
            org_info["project_id"] = proj["id"]
            clust_info = atlas_cluster_info(org_info)
            clusters = []
            for cluster in clust_info:
                bb.logit(f'Cluster: {cluster["name"]} - {cluster["providerSettings"]["instanceSizeName"]}')
                clusters.append(cluster)
            doc["clusters"] = clusters
            bulk_docs.append(doc)
    bb.logit("# ------------- Complete ------------- #")
    #  Find the way here to push to ServiceNow
    pprint.pprint(bulk_docs)
        
def atlas_monitoring():
    #  Loops through orgs and projects to get details on each cluster and push to atlas
    orgs = settings["organizations"]
    bulk_docs = []
    bulk_projects = []
    project_updates = []
    cluster_updates = []
    o_contents = {}
    p_contents = {}
    base_path = settings["repo_path"]
    bb.message_box("Atlas Cluster Audit","title")
    repo = git.Repo(base_path)
    for org in orgs:
        bb.message_box(f'Organization: {org}')
        org_info = {"org" : org, "id" : orgs[org]["org_id"], "api_key" : orgs[org]["api_key"], "quiet" : "yes"}
        org_doc = {"name" : org, "org_id" : org_info["id"]}
        o_contents = {"name" : org, "org_id" : org_info["id"], "projects" : []}
        result = atlas_project_info(org_info)
        if "name" not in result[0]:
            bb.logit('Failed to get info for org - check API key access')
            next
        for proj in result:
            bb.logit(f'Clusters: [{proj["clusterCount"]}]')
            doc_type = "clusters"
            org_info["project_id"] = proj["id"]
            project_details = {"object_type": "Project", "org" : org_doc, "project_id" : proj["id"], "name" : proj["name"], "project" : proj}
            p_contents = {"org" : org_doc, "project_id" : proj["id"], "name" : proj["name"], "project" : proj, "clusters" : [], "version" : "1.0"}
            clust_info = atlas_cluster_info(org_info)
            cluster_mini = []
            for cluster in clust_info:
                bb.logit(f'Cluster: {cluster["name"]} - {cluster["providerSettings"]["instanceSizeName"]}')
                cluster_doc["object_type"] = "Cluster"
                cluster_doc = {"organization" : org_doc}
                cluster_doc["project_id"] = proj["id"]
                cluster_doc["project"] = proj["name"]
                cluster_doc["cluster_id"] = cluster["id"]
                cluster_doc["cluster_name"] = cluster["name"]
                #cluster_doc["timestamp"] = dt.datetime.now()
                cluster_doc["cluster_details"] = cluster
                cluster_doc["online_archive"] = atlas_online_archive_details({"project_id" : proj["id"], "org" : org, "cluster_name" : cluster["name"], "quiet": "yes"})
                cluster_doc["version"] = "1.0"
                #bulk_docs.append(cluster_doc)
                cluster_mini.append({"cluster_id" :cluster["id"], "cluster_name": cluster["name"], "size" : cluster["providerSettings"]["instanceSizeName"], "cloud" : cluster["providerSettings"]["providerName"]})
                cluster_updates.append(UpdateOne({"_id": cluster["id"]},{"$set": cluster_doc}, upsert=True))
            p_contents["clusters"] = cluster_mini
            create_repo_document(repo, org, p_contents, doc_type)
            project_details["clusters"] = cluster_mini
            o_contents["projects"].append(project_details)
            project_details["users"] = atlas_project_users({"project_id" : proj["id"], "org" : org, "quiet": "yes"})
            project_details["database_users"] = atlas_database_users({"project_id" : proj["id"], "org" : org, "quiet": "yes"})
            #bulk_projects.append(project_details)
            project_updates.append(UpdateOne({"project_id": proj["id"]},{"$set": project_details}, upsert=True))
        create_repo_document(repo, org, o_contents, "projects")
    bb.logit("# ------------- Complete ------------- #")
    bb.message_box("Checking git", "title")
    #git_check(repo)
    client = client_connection()
    db = client["cmdb"]
    bulk_writer(db["atlas_objects"], project_updates)
    bulk_writer(db["atlas_objects"], cluster_updates)
    client.close()
    #  Find the way here to push to ServiceNow
    #pprint.pprint(bulk_projects)
    #pprint.pprint(bulk_docs)

def create_repo_document(repo_obj,local_path, doc, doc_type):
    # take the info and push to a json document in a git repo
    base_path = repo_obj.working_tree_dir
    name = "newfile_39586.json"
    #pprint.pprint(doc)
    if "name" in doc:
        name = f'{doc["name"]}_{doc_type}.json'
    if local_path != "":
        full_path = f'{base_path}/{local_path}'
    else:
        full_path = f'{base_path}'
    if not os.path.isdir(full_path):
        pathlib.Path(full_path).mkdir(parents=True, exist_ok=True)
    bb.save_json(f'{full_path}/{name}', doc)

def git_check(repo = ""):
    if repo == "":
        base_path = settings["repo_path"]
        repo = git.Repo(base_path)
    if repo.is_dirty(untracked_files=True):
        bb.logit(f'Repository: {repo.working_tree_dir}')
        bb.logit("Changes to configuration")
        bb.logit(repo.git.status())
        repo.git.add(all=True)
        bb.logit("# -------------------- Changes ---------------------- #")
        bb.logit(repo.git.status())
        repo.index.commit("Update from automation")
        bb.logit("# -- committed -- #")
    else:
        bb.logit("Atlas config is stable")

def git_analyze_changes(repo = ""):
    if repo == "":
        base_path = settings["repo_path"]
        repo = git.Repo(base_path)
    # Compare the last two commits
    head_commit = repo.head.commit
    parent_commit = head_commit.parents[0]
    diff_index = parent_commit.diff(head_commit, create_patch=True)
    for diff in diff_index:
        bb.logit(f"File: {diff.a_path} -> {diff.b_path}")
        # Determine the change type (added, deleted, modified, etc.)
        if diff.change_type == 'A':
            bb.logit("Added:", diff.b_path)
        elif diff.change_type == 'D':
            bb.logit("Deleted:", diff.a_path)
        elif diff.change_type == 'M':
            bb.logit("Modified:", diff.a_path)
        elif diff.change_type == 'R':
            bb.logit(f"Renamed: {diff.a_path} -> {diff.b_path}")
        elif diff.change_type == 'T':
            bb.logit(f"Type Change: {diff.a_path} to {diff.b_path}")
        # Access diff details
        bb.logit("Diff details:")
        #pprint.pprint(diff.diff)
        pprint.pprint(diff.diff.decode())
        print("\n# " + "-" * 76 + " #\n")

def change_details(file_name, change, line_num):
    print(f'In file: {repo_path}/{file_name}')
    contents = bb.read_json(f'{repo_path}/{file_name}')
    find_keys(contents, {"target" : line_num})

def find_keys(conts, details):
    """
    Recursively counts all the keys in a complex dictionary.
    :param d: The dictionary to count keys in.
    :return: The total count of keys.
    """
    key_count = 0
    start_count = 0
    if "key_count" in details:
        start_count = details["key_count"]
    jpath = []
    if "jpath" in details:
        jpath = details["jpath"]
            
    target = details["target"]
    # Ensure that the input is actually a dictionary
    if isinstance(conts, dict):
        # Count the keys at the current level
        for key, value in conts.items():
            key_count += 1
            # If the value is another dictionary, recurse into it
            if isinstance(value, dict):
                jpath.append(key)
                details["key_count"] = key_count
                details["jpath"] = jpath
                key_count += find_keys(value, details)
                if show_me(target, key_count + start_count, jpath):
                    break
                else:
                    if key in jpath:
                        jpath.remove(key)
            # If the value is a list, check each item in the list
            elif isinstance(value, list):
                jpath.append(key)
                for item in value:
                    details["key_count"] = key_count
                    if isinstance(item, dict):
                        details["key_count"] = key_count
                        details["jpath"] = jpath
                        key_count += find_keys(item, details) 
                        if show_me(target, key_count + start_count, jpath):
                            break
                        else:
                            if key in jpath:
                                jpath.remove(key)
                    else:
                        key_count += 1
                        if show_me(target, key_count + start_count, jpath):
                            break
                if key in jpath:
                    jpath.remove(key)
            else:
                if show_me(target, key_count + start_count, jpath):
                    break
    return key_count

def show_me(matcher, num, pth):
    #print(pth)
    result = False
    if matcher == num:
        print(f'HIT - [{num}] - {",".join(pth)}')
        result = True
    else:
        print(f'[{matcher}] != [{num}] - {",".join(pth)}')
    return result

def git_diff():
    # Choose the commits to compare. For example, compare the last two commits
    head_commit = repo.head.commit
    parent_commit = head_commit.parents[0]
    re_pattern = r"\+(\d+),"
    # Get the diff between the head commit and its first parent
    diff_index = parent_commit.diff(head_commit, create_patch=True)

    # Iterate over the diff
    for diff in diff_index:
        file_name = diff.a_path
        print(f"File: {diff.a_path} -> {diff.b_path}")

        # Determine the change type (added, deleted, modified, etc.)
        if diff.change_type == 'A':
            print("Added:", diff.b_path)
        elif diff.change_type == 'D':
            print("Deleted:", diff.a_path)
        elif diff.change_type == 'M':
            print("Modified:", diff.a_path)
        elif diff.change_type == 'R':
            print(f"Renamed: {diff.a_path} -> {diff.b_path}")
        elif diff.change_type == 'T':
            print(f"Type Change: {diff.a_path} to {diff.b_path}")

        # Access diff details
        print("Diff details:")
        #pprint.pprint(diff.diff)
        diff_out = diff.diff.decode()
        pprint.pprint(diff_out)
        print("# --- Change Analysis --- #")
        ipos = 0
        line_num = 0
        match_line = ""
        for ln in diff_out.split('\n'):
            if "@@" in ln:
                match = re.search(re_pattern, ln)
                line_num = int(match[0].replace("+","").replace(",",""))
            if "+    " in ln:
                match_line = ln.replace("+    ","")
                print(f'- added: {match_line}')                
            elif "-    " in ln:
                rmatch_line = ln.replace("-    ","")
                print(f'- removed: {rmatch_line}')
            ipos += 1
            if line_num > 0 and match_line != "":
                change_details(file_name, match_line, line_num)
            line_num = 0
            match_line = ""


        print("\n" + "=" * 80 + "\n")   

def atlas_org_users(details = {}):
    org_id = settings["org_id"]
    if "org_id" in details:
        org_id = details["org_id"]
    url = base_url + f'/orgs/{org_id}/users?pretty=true'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Atlas User Info", "title")
        pprint.pprint(result)
    return result["results"]

def atlas_project_users(details = {}):
    project_id = settings["project_id"]
    if "project_id" in details:
        project_id = details["project_id"]
    url = base_url + f'/groups/{project_id}/users?pretty=true'
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
    org_users = atlas_org_users({"quiet" : True})
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
    url = base_url + f'/groups/{settings["project_id"]}/privateEndpoint/{provider}/endpointService/{svc_id}'
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
    if "provider" in ARGS:
        provider = ARGS["provider"]
    if "region" in ARGS:
        region = ARGS["region"]
    url = base_url + f'/groups/{settings["project_id"]}/privateEndpoint/endpointService'
    payload = {"providerName" : provider, "region" : region}
    result = rest_post(url, {"data" : payload})
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    for i in range(5):
        bb.logit("Waiting for endpoint creation...")
        time.sleep(30)
        result2 = atlas_private_endpoint_svc({"provider" : provider, "endpoint_svc_id" : result["id"]})
        if result2["status"] == "AVAILABLE":
            break
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLink Details", "title")
        pprint.pprint(result2)
    if provider == "AZURE":
        payload = result2
        # TODO - get the extras vnet etc into payload
        #azure_create_private_endpoint(payload)
    
    
def atlas_create_private_endpoint(details = {}):    
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/privateEndpoint/{cloudProvider}/endpointService/{endpointServiceId}/endpoint
    project_id = settings["project_id"]
    if "project_id" in details:
        project_id = details["project_id"]
    if "vpc_id" in ARGS:
        vpc_id = ARGS["vpce_id"]
    else:
        sys.exit(1)
    if provider == "AZURE" and "cidr" in ARGS:
        cidr = ARGS["cidr"]
    else:
        bb.logit("For azure - add cidr=<IPAddress>")
        sys.exit(1)
    url = base_url + f'/groups/{project_id}/privateEndpoint/{provider}/endpointService/{service_id}/endpoint'
    bb.logit(f"ServiceURL: {url}")
    payload = {"id" : vpc_id}
    if provider == "AZURE":
        payload["privateEndpointIPAddress"] = cidr
    result = rest_post(url, {"data" : payload})
    if not "quiet" in details:
        bb.message_box("Atlas PrivateLinks", "title")
        pprint.pprint(result)
    return result

def azure_create_private_endpoint(details = {}):
    # Use azure CLI to create PE
    '''
    python3 atlas_rest.py action azure_cli_command service_id=64505410cdbca3236596c2cd resource_name=BB-DEVOps_group vnet_name=BradyDevOps subnet=default
    resource_name
    vnet_name
    subnet_name
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
    if "service_id" in ARGS:
        service_id = ARGS["service_id"]
        resource_name = ARGS["resource_name"]
        vnet_name = ARGS["vnet_name"]
        subnet = ARGS["subnet"]    
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
        details = atlas_private_endpoint_svc({"provider" : provider, "endpoint_svc_id" : service_id})
        svc_id = details["privateLinkServiceName"]
        resource_id = details["privateLinkServiceResourceId"]
    endpoint_name = f"azure_pl_{subnet}"
                    
    disabler = f"az network vnet subnet update --resource-group {resource_name} --vnet-name {vnet_name} --name {subnet} --disable-private-endpoint-network-policies true"
    template = f"az network private-endpoint create --resource-group {resource_name} --name {endpoint_name} --vnet-name {vnet_name} --subnet {subnet} --private-connection-resource-id {resource_id} --connection-name {svc_id} --manual-request true"
    bb.logit("# ----------------------- Azure CLI Commands -------------------------- #")
    print(disabler)
    print(" -------------------------- ")
    print(template)
    return({"disabler" : disabler, "endpoint" : template})

def gcp_create_private_endpoint(details = {}):
    test = "true"

def gcp_create_kms_encryption(details = {}):
    # https://cloud.mongodb.com/api/atlas/v1.0/groups/{groupId}/encryptionAtRest
    key_resource_id = os.environ.get("Key_Resource_Id")
    #service_account_key = settings["gcp_service_account_key"]
    with open(ARGS["Secret_File"]) as secretfile:
        service_account_key = secretfile.read()
    payload = {"googleCloudKms" : {
        "enabled": True,
        "keyVersionResourceID": key_resource_id,
        "serviceAccountKey": service_account_key
    }}
    url = base_url + f'/groups/{settings["project_id"]}/encryptionAtRest'
    result = rest_update(url, {"data" : payload})
    if not "quiet" in details:
        bb.message_box("Atlas GCP-KMS Encryption Info", "title")
        print(payload)
        print("----------------------------------------------------")
        pprint.pprint(result)
    return result

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


def atlas_user_add(details = {}):
    role = "read"
    project_id = settings["project_id"]
    if "Project_Name" in os.environ:
        project_id = atlas_get_project_id()
    if "role" in ARGS:
        role = ARGS["role"]
    if "DB_User" in os.environ:
        # user:pass|role,user:pass|role
        secrets = os.environ["DB_User"].split(",")
    elif "user" in ARGS:
        secrets = [f'{ARGS["user"]}|{role}']    
    else:
        print("Send user=<user:password>")
        sys.exit(1)
    for secret in secrets:
        pair = secret.split("|")
        role = pair[1]
        pair = pair[0].split(":")
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

def get_project_id(details = {}):
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

def atlas_project_info_name(details = {}):
    name=details['project_name']
    #url = f'{base_url}/groups/{name}'
    url = f'{base_url}/groups/byName/{name}'
    result = rest_get(url, details) #, {"verbose" : True})
    if not "quiet" in details:
        bb.message_box("Atlas Projects", "title")
        pprint.pprint(result)
    return result

def atlas_project_check():
    if "Atlas_Project_Name" in os.environ:
        project_name=os.environ.get("Atlas_Project_Name")
        #answer=atlas_project_info({"project_name" : project_name})
        answer=atlas_project_info_name({"project_name" : project_name})
        if "id" in answer:
            p_status = answer["id"]
        else:
            p_status = "NEW"
        with open (f"{os.environ.get('WORKSPACE')}/p_status.txt" , "w") as fil:
            fil.write(p_status)
    
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

def atlas_create_cluster_new():
    if "template" not in ARGS:
        print("Send template=<template_name>")
        sys.exit(1)
    t_name = ARGS["template"]
    if not ".json" in t_name:
        t_name = f'{t_name}.json'
    obj = bb.read_json(os.path.join(base_path, "templates", t_name))
    url = base_url + f'/groups/{settings["project_id"]}/clusters?pretty=true'
    #result = rest_post(url, {"data" : obj})
    #bb.message_box("Response")
    pprint.pprint(obj)

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
        host = re.sub(':27017.*',"",host)
        get_log_file(host, start_time, end_time, log_dir, details)


def get_log_file(cluster, start, end, log_path, details = {}):
    '''
    curl --user '{PUBLIC-KEY}:{PRIVATE-KEY}' --digest \
 --header 'Accept: application/gzip' \
 --request GET "https://cloud.mongodb.com/api/atlas/v1.0/groups/{GROUP-ID}/clusters/{HOSTNAME}/logs/mongodb.gz?startDate=&endDate=<unixepoch>" \
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

def atlas_create_online_archive():
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

def atlas_online_archive_details(details = {}):
    # GET /groups/{GROUP-ID}/clusters/{CLUSTER-NAME}/onlineArchives
    project_id = settings["project_id"]
    cluster_name = settings["cluster_name"]
    if "project_id" in details:
        project_id = details["project_id"]
        cluster_name = details["cluster_name"]
    url = base_url + f'/groups/{project_id}/clusters/{cluster_name}/onlineArchives'
    result = rest_get(url, details)
    if not "quiet" in details:
        bb.message_box("Response")
        pprint.pprint(result)
    return result

# ------------------------------------------------------------ #
#    UTILITY
# ------------------------------------------------------------ #
def get_api_key(details = {}):
    if "org" in details:
        org = details["org"]
        result = settings["organizations"][org]["api_key"]
    else:
        result = api_key
    return result

def rest_get(url, details = {}):
    headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
    if "headers" in details:
        headers = details["headers"]
    api_pair = bb.desecret(get_api_key(details)).split(":")
    response = requests.get(url, auth=HTTPDigestAuth(api_pair[0], api_pair[1]), headers=headers)
    result = response.content.decode('utf-8')
    if "verbose" in details:
        bb.logit(f"Status: {response.status_code}")
        bb.logit(f"Headers: {response.headers}")
        bb.logit(f"URL: {url}")
        bb.logit(f"Response: {result}")
    return(json.loads(result))

def rest_get_url():
    url = ARGS["url"]
    key = ARGS["key"]
    secret = ARGS["secret"]
    headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
    response = requests.get(url, auth=HTTPDigestAuth(key, secret), headers=headers)
    result = response.content.decode('utf-8')
    bb.logit(f"Status: {response.status_code}")
    bb.logit(f"Headers: {response.headers}")
    bb.logit(f"URL: {url}")
    bb.logit(f"Response: {result}")
    return(json.loads(result))
   
def rest_get_ip():
  url="http://api.ipify.org"
  response = requests.get(url)
  result = response.content.decode('utf-8')
  bb.logit(f"URL: {url}")
  bb.logit(f"Response: {result}")
  pprint.pprint(result)

def rest_get_file(url, details = {}):
  # https://stackoverflow.com/questions/36292437/requests-gzip-http-download-and-write-to-disk
  headers = {"Content-Type" : "application/json", "Accept" : "application/json" }
  if "headers" in details:
      headers = details["headers"]
  api_pair = bb.desecret(get_api_key(details)).split(":")
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
  api_pair = bb.desecret(get_api_key(details)).split(":")
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
  api_pair = bb.desecret(get_api_key(details)).split(":")
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

def bulk_writer(collection, bulk_arr, msg = ""):
    try:
        result = collection.bulk_write(bulk_arr, ordered=False)
        ## result = db.test.bulk_write(bulkArr, ordered=False)
        # Opt for above if you want to proceed on all dictionaries to be updated, even though an error occured in between for one dict
        #pprint.pprint(result.bulk_api_result)
        note = f'BulkWrite - mod: {result.bulk_api_result["nModified"]} {msg}'
        #file_log(note,locker,hfile)
        print(note)
    except BulkWriteError as bwe:
        print("An exception occurred ::", bwe.details)

def test_shell():
  cmd = ["which", "curl"]
  result = bb.run_shell(cmd)

def test_driver():
    conn = client_connection("turi")
    db = conn["test"]
    db.test.insert_one({"name" : "testitem"})

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

def json_template(temp_type):
    if not temp_type.endsWith(".json"):
        temp_type = temp_type + ".json"
    ppath = f'{base_path}/{temp_type}'
    result = bb.read_json(ppath)
    return(copy.deepcopy(result))

def get_setting(setting, details = {}):
    # Cascade through this
    # details = {"env" : "Project_Name"}
    result = "none"
    if "env" in details:
        result=os.environ.get(details["env"])
    else:
        if setting in temp_settings:
            result = temp_settings[setting]
        elif setting in settings:
            result = settings[setting]
    return result
    
def temp_settings(action="get", data={}):
    fpath = os.path.join(base_path, temp_settings_file)
    if action == "get":
        tempsettings = read_temp_settings()
    elif action == "set":
        tempsettings = read_temp_settings()
        for item in data:
            tempsettings[item] = data[item]
        with open(json_file, 'w') as outfile:
                json.dump(tempsettings, fpath)
    return tempsettings

def read_temp_settings():
    tempsettings = bb.read_json(os.path.join(base_path, temp_settings_file))
    return tempsettings

def client_connection(type = "uri", details = {}):
    mdb_conn = settings[type]
    username = settings["username"]
    password = settings["password"]
    if "username" in details:
        username = details["username"]
        password = details["password"]
    if "secret" in password:
        password = os.environ.get("_PWD_")
    if "%" not in password:
        password = urllib.parse.quote_plus(password)
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
    settings_file = "rest_secret_settings.json"
    bb = Util()
    ARGS = bb.process_args(sys.argv)
    base_path = os.path.dirname(os.path.abspath(__file__))
    settings = bb.read_json(os.path.join(base_path, settings_file))
    temp_settings_file = "temp_settings.json"
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
    elif ARGS["action"] == "project_detail":
        atlas_project_detail()
    elif ARGS["action"] == "project_users":
        atlas_project_users()
    elif ARGS["action"] == "alert_settings":
        atlas_project_alerts()
    elif ARGS["action"] == "private_links":
        atlas_private_endpoints()
    elif ARGS["action"] == "private_link_svc_detail":
        atlas_private_endpoint_svc()
    elif ARGS["action"] == "private_link":
        atlas_private_endpoint_detail()
    elif ARGS["action"] == "create_private_link_svc":
        atlas_create_private_endpoint_svc()
    elif ARGS["action"] == "create_private_link":
        atlas_create_private_endpoint()
    elif ARGS["action"] == "azure_cli_command":
        azure_create_private_endpoint()
    elif ARGS["action"] == "gcp_cli_command":
        gcp_create_private_endpoint()
    elif ARGS["action"] == "create_kms_encryption":
        gcp_create_kms_encryption()
    elif ARGS["action"] == "kms_encryption":
        atlas_kms_encryption()
    elif ARGS["action"] == "billing":
        atlas_billing()
    elif ARGS["action"] == "billing_invoice":
        atlas_billing_invoice()
    elif ARGS["action"] == "department_accounting":
        atlas_department_accounting()
    elif ARGS["action"] == "user_add":
        atlas_user_add()
    elif ARGS["action"] == "org_users":
        atlas_org_users()
    elif ARGS["action"] == "database_users":
        atlas_database_users()
    elif ARGS["action"] == "db_user_audit":
        atlas_db_user_audit()
    elif ARGS["action"] == "user_audit":
        atlas_user_audit()
    elif ARGS["action"] == "cluster_audit":
        atlas_cluster_audit()
    elif ARGS["action"] == "atlas_monitoring":
        atlas_monitoring()
    elif ARGS["action"] == "cluster_info":
        atlas_cluster_info()
    elif ARGS["action"] == "create_cluster":
        atlas_create_cluster_new()
    elif ARGS["action"] == "update_cluster":
        atlas_update_cluster()
    elif ARGS["action"] == "resume":
        atlas_resume_cluster()
    elif ARGS["action"] == "update_cluster_labels":
        updateClusterLabels()
    elif ARGS["action"] == "create_online_archive":
        atlas_create_online_archive()
    elif ARGS["action"] == "online_archives":
        atlas_online_archive_details()
    elif ARGS["action"] == "search_indexes":
        # cluster, database, collection
        atlas_search_indexes()
    elif ARGS["action"] == "search_index":
        # id
        atlas_search_index_detail()
    elif ARGS["action"] == "search_hw_metrics":
        # process=820acde8445dc943b6d28e986798ee02
        atlas_search_hw_metrics()
    elif ARGS["action"] == "search_metrics":
        # process=820acde8445dc943b6d28e986798ee02, database, collection
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
        print(f'Decrypted: {res}',"SECRET")
    elif ARGS["action"] == "get_ip":
        rest_get_ip()
    elif ARGS["action"] == "test_driver":
        test_driver()
    elif ARGS["action"] == "test_git":
        git_check()
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
