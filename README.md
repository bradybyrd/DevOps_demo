#-----------------------------------#
#  Devops API examples for Atlas    #

#### Python script modules for interacting with the Atlas API. ####

Basic Operation:

- First modify the rest_settings.json to include your information
The first 5 items are only used if you need to write information back to a MongoDB database.
```
  "uri" : "mongodb+srv://m10basicagain-vmwqj.mongodb.net",
  "cluster_name" : "MigrateDemo2",
  "database" : "billing",
  "collection" : "paths",
  "username" : "main_admin",
  "password" : "*********",  
```
Right now, only the billing invoices methods need to write back

- The next few settings specify API access
```
"project_id" : "5d4d7ed3f2a30b18f4f88946",
"org_id" : "5e384d3179358e03d842ead1",
"api_key" : "------------------------------------------",
"api_public_key" : "FMLUMLCQ",
"base_url" : "https://cloud.mongodb.com/api/atlas/v1.0",
```
Your project and org ids can be picked out of any atlas URL, like this:
https://cloud.mongodb.com/v2/5d4d7ed3f2a30b18f4f88946#clusters
The project ID is the 5d4d... string.  From an org level url, you can get the org ID:
https://cloud.mongodb.com/v2#/org/5e384d3179358e03d842ead1/projects

At the project level (or org level if you need project creation, priavteLinks etc), create an API key pair.  This will give you a public and private key.  The settings file uses a hashed version of this for security (weak, but something).  
- To hash your API keys:
  from the command line, run the encrypt method, like this:
```
  python3 atlas_rest.py action=encrypt secret="<publickey>:<privatekey>"
```
This will give you the hashed string to put in the api_key field.

- Now you should be able to test it:
```
  python3 atlas_rest.py action=project_info
```
If that fails, first thing to check is the network access which is specific to the api key pair.

#### API Methods ####

- Organization Info (uses the organization id from the settings file)
  python3 atlas_rest.py action=org_info

- Project Info (uses the project id from the settings file)
  python3 atlas_rest.py action=project_info

- Cluster Info (uses the project id from the settings file)
  Returns information on all clusters in the project
  python3 atlas_rest.py action=cluster_info

  To get detailed information on a single cluster:
  python3 atlas_rest.py action=cluster_info name=M10BasicAgain

- [Start or pause a cluster](https://docs.atlas.mongodb.com/pause-terminate-cluster/):
  python3 atlas_rest.py action=update_cluster name=MigrateDemo2 data='{"paused" : false}'

- [Reconfigure a cluster](https://docs.atlas.mongodb.com/scale-cluster/):
  python3 atlas_rest.py action=update_cluster name=M10BasicAgain data='{"labels" : [{"key": "department", "value" : "CodeWizards"},{"key": "owner", "value":"Brady Byrd"}]}'

#### Raw API ####
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
elif ARGS["action"] == "logs":
    atlas_log_files()













#--- Invoice Queries

[{$match: {
  endDate: "2021-11-01T00:00:00Z"
}}, {$unwind: {
  path: "$lineItems"
}}, {$match: {
  "lineItems.sku" : /^REALM.*/
}}]

[{$match: {
  endDate: "2021-11-01T00:00:00Z"
}}, {$unwind: {
  path: "$lineItems"
}}, {$project: {
  "SKU" : "$lineItems.sku", "_id" : 0
}}]


# ------------------------------------------------- #
#  Jenkins Install
#  3/4/22

/usr/local/opt/openjdk@11/bin/java -Dmail.smtp.starttls.enable=true -jar /usr/local/opt/jenkins-lts/libexec/jenkins.war --httpListenAddress=127.0.0.1 --httpPort=4005

http://localhost:4005
bbadmin

# ------------------------------------------------- #
#  PrivateEndpoint creation
#  5/1/23

Tst: 
subscriptions/22cf268b-6d60-4014-b553-7ef12e3f67a6
BB-DEVOps_group
BradyDevOps
default - 10.0.0.0/24
AZURE
US_EAST_2

/subscriptions/52f0a73e-87fd-4b87-bc73-b76cbda361ee/resourceGroups/rg_64503bf4f695331ad04754fa_epc7hkvk/providers/Microsoft.Network/privateLinkServices/pls_64503bf4f695331ad04754f9

# ------------------------------------------------------ #
#  KMS Encryption Test
bb-hsm-key
resourceID: projects/bradybyrd-poc/locations/us-central1/keyRings/bb-ringworld/cryptoKeys/bb-hsm-key/cryptoKeyVersions/1