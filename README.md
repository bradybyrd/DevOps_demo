#-----------------------------------#
#  README for DevOps Scripts

M10BasicAgain Restart

Start a cluster:
  python3 atlas_rest.py action=update_cluster name=MigrateDemo2 data='{"paused" : false}'
Get cluster info:
  python3 atlas_rest.py action=cluster_info name=M10BasicAgain
Update Cluster info:
  python3 atlas_rest.py action=update_cluster name=M10BasicAgain data='{"labels" : [{"key": "department", "value" : "CodeWizards"},{"key": "owner", "value":"Brady Byrd"}]}'

Script Methods:
elif ARGS["action"] == "org_info":
    atlas_org_info()
elif ARGS["action"] == "org_projects":
    atlas_project_info()
elif ARGS["action"] == "alert_settings":
    atlas_project_alerts()
elif ARGS["action"] == "billing":
    atlas_billing()
elif ARGS["action"] == "billing_invoice":
    atlas_billing_invoice()
elif ARGS["action"] == "user_add":
    atlas_user_add()
elif ARGS["action"] == "users":
    atlas_users()
elif ARGS["action"] == "cluster_info":
    atlas_cluster_info()
elif ARGS["action"] == "create_cluster":
    atlas_create_cluster()
elif ARGS["action"] == "update_cluster":
    atlas_update_cluster()
elif ARGS["action"] == "online_archive":
    atlas_online_archive()
elif ARGS["action"] == "search_indexes":



'{"diskSizeGB": 320,"providerSettings": {"instanceSizeName": "M40"}'


{
  and : [
    {endDate : {$lte : ISODate("2021-11-02T00:00:00Z")}},
    {startDate : {$gte : ISODate("2021-10-01T00:00:00Z")}}
  ]
}

dat = datetime.datetime.strptime(sdat,"%Y-%m-%dT%H:%M:%SZ")


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
