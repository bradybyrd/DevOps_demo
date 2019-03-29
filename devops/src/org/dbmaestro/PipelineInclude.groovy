/*
 Deployment Pipeline Include
This file is called by the stub and can be centralized for all pipelines
7/18/18 BJB - DBmaestro
*/
package org.dbmaestro;
import groovy.json.*

@NonCPS
def get_settings(content, landscape, flavor = 0) {
    def jsonSlurper = new JsonSlurper()
    def settings = [:]
    def pipe = [:]
    def credential = "-AuthType DBmaestroAccount -UserName _USER_ -Password \"_PASS_\""
    settings = jsonSlurper.parseText(content)
    pipe["server"] = settings["general"]["server"]
    pipe["java_cmd"] = settings["general"]["java_cmd"]
    pipe["staging_dir"] = settings["general"]["staging_path"]
    pipe["base_path"] = settings["general"]["base_path"]
    pipe["source_control"] = settings["general"]["source_control"]["type"]
	  pipe["remote_git"] = settings["general"]["source_control"]["remote"]
	  echo "Landscape: ${landscape}, flavor: ${flavor}"
    // note key off of landscape variable
    pipe["base_schema"] = settings["branch_map"][landscape][flavor]["base_schema"]
    pipe["base_env"] = settings["branch_map"][landscape][flavor]["base_env"]
    pipe["pipeline"] = settings["branch_map"][landscape][flavor]["pipeline"]
    pipe["file_strategy"] = "version"
    if(settings["branch_map"][landscape][flavor].containsKey("file_strategy")){
      pipe["file_strategy"] = settings["branch_map"][landscape][flavor]["file_strategy"]
    }
    pipe["environments"] = settings["branch_map"][landscape][flavor]["environments"]
    pipe["approvers"] = settings["branch_map"][landscape][flavor]["approvers"]
    pipe["source_dir"] = settings["branch_map"][landscape][flavor]["source_dir"]
    credential = credential.replaceFirst("_USER_", settings["general"]["username"])
    pipe["credential"] = credential.replaceFirst("_PASS_", settings["general"]["token"])
    if(settings["branch_map"][landscape][flavor].containsKey("schema_flags")){
      pipe["schema_flags"] = settings["branch_map"][landscape][flavor]["schema_flags"]
    }
    
	println "Pipe: ${pipe["environments"]}"
    return pipe
}
 
def prepare() {
    node {
        //checkout(scm)
        println "Checkout from git"
    }
}

def failTheBuild(String message) {

    currentBuild.result = "FAILURE"    
    def messageColor = "\u001B[32m" 
    def messageColorReset = "\u001B[0m"
    echo messageColor + message + messageColorReset
    error(message)
}

def run(Object step, pipe, env_num){
    try {
        step.execute(pipe, env_num)
    } catch (err) {
        // unfortunately, err.message is not whitelisted by script security
        //failTheBuild(err.message)
        failTheBuild("Build failed")
    }
}

def execute(settings = [:]) {
	def automationPath = "C:\\automation\\dbm_demo\\devops"
	def settingsFileName = "local_settings.json"
  def settingsFile = "${automationPath}${sep()}${settingsFileName}"
	def buildNumber = "$env.BUILD_NUMBER"
	def dbmNode = "master"
	def rootJobName = "$env.JOB_NAME";
	//def branchName = rootJobName.replaceFirst('.*/.*/', '')
	def fullBranchName = rootJobName.replaceFirst('.*/','')
	def branchName = fullBranchName.replaceFirst('%2F', '/')
	def landscape = branchName.replaceFirst('/.*', '')
  def pipeline = [:]
	def settings_content = ""
	echo "Inputs: ${rootJobName}, branch: ${landscape}, name: ${branchName}"
  if( settings.containsKey("settings_file")) { 
    settingsFile = settings["settings_file"] 
  }
	this.prepare()
	node(dbmNode) {
		println "JSON Settings Document: ${settingsFile}"
		println "Job: ${env.JOB_NAME}"
		def hnd = new File(settingsFile)
		settings_content = hnd.text
	}
	pipeline = this.get_settings(settings_content, landscape)
	pipeline["branch_name"] = branchName
	pipeline["branch_type"] = landscape
	pipeline["dbm_node"] = dbmNode
  pipeline["spool_path"] = "${pipeline["staging_dir"]}${sep()}${pipeline["pipeline"]}${sep()}reports"
  settings.each {k,v ->
    pipeline[k] = v
  }
  echo message_box("Pipeline Deployment Using ${landscape} Process", "title")
  echo "Working with: ${rootJobName}\n - Branch: ${landscape} V- ${branchName}\n - Pipe: ${pipeline["pipeline"]}\n - Env: ${pipeline["base_env"]}\n - Schema: ${pipeline["base_schema"]}"
	def tasks = this.get_tasks(pipeline)
  pipeline["tasks"] = tasks
	def version = this.get_version(pipeline)
  pipeline["version"] = version
  
  // Here we loop through the environments from the settings file to perform the deployment
  def env_num = 0
  pipeline["environments"].each { env ->
    echo "Executing Environment ${env}"
    this.run(new DeployOperation(), pipeline, env_num)
    if (landscape == "master") {
        println "Branch specific work"
    }
    env_num += 1
  }
}

def get_tasks(pipe_info){
	// message looks like this "Adding new tables [Version: V2.3.4] "
	def reg = ~/.*\[Tasks: (.*)\].*/
  def taskResult = this.git_commit_message(pipe_info, reg)
	return taskResult
}

def get_version(pipe_info){
	// message looks like this "Adding new tables [Version: V2.3.4] "
  if ( env.Version != null && env.Version.length() > 1 && env.Version != "V0.0.0"){
    echo "#------- Version environment variable set: ${env.Version} - using that ---------#\r\n#-------- Ignoring git version ----"
    return env.Version
  }
	def reg = ~/.*\[Version: (.*)\].*/
  def versionResult = this.git_commit_message(pipe_info, reg)
	return versionResult
}

def git_commit_message(pipe_info, reg){
	// message looks like this "Adding new tables [Version: V2.3.4] "
	def gitMessage = ""
  def result = ""
  def branch_name = pipe_info["branch_name"]
  def base_path = pipe_info["base_path"]
  def dbm_node = pipe_info["dbm_node"]
  def remote = pipe_info["remote_git"] != "false"
  def scm = pipe_info["source_control"]
  def pull_stg = remote ? " && git pull origin ${branch_name}" : ""
  
  // ------------- Update Local Git -----------------------
  stage('GitParams') {
  	node (dbm_node) {
  			echo "# Read latest commit..."
  			dir([path:"${base_path}"]){
  				bat "git --version"
				bat ([script: "git remote update && git checkout ${branch_name}${pull_stg}"])
  				gitMessage = bat(
  				  script: "@cd ${base_path} && @git log -1 HEAD --pretty=format:%%s",
  				  returnStdout: true
  				).trim()
  		}
  		echo "# From Git: ${gitMessage}"
  		result = gitMessage.replaceFirst(reg, '$1')
  	}
  }
  // Both branch version and git version git wins as override!
  if (gitMessage.length() != result.length()){
  	echo "# Parsed message from git:" + result
  }else{
    echo "# Commit message not fomatted properly"
    currentBuild.result = "UNSTABLE"
    return
  }
	return result
}

@NonCPS
def message_box(msg, def mtype = "sep") {
    def tot = 100
    def start = ""
    def res = ""
    res = "#--------------------------- ${msg} ---------------------------#"
    return res
    msg = (msg.size() > 85) ? msg[0..84] : msg
    def ilen = tot - msg.size()
    if (mtype == "sep") {
        start = "#${"-" * (ilen / 2).toInteger()} ${msg} "
        res = "${start}${"-" * (tot - start.size() + 1)}#"
    } else {
        res = "#${"-" * tot}#\r\n"
        start = "#${" " * (ilen / 2).toInteger()} ${msg} "
        res += "${start}${" " * (tot - start.size() + 1)}#\r\n"
        res += "#${"-" * tot}#\r\n"
    }
    //println res
    return res
}

def callPreProcess(cur_env) {
    try {
        echo "Running pre processing"
        bat "${pipeline["javaCmd"]} -Upgrade -ProjectName ${pipeline["pipeline"]} -EnvName ${cur_env} -PackageName ${preProcess} -Server ${pipeline["server"]} ${pipeline["credential"]}"
    } catch (Exception e) {
        echo e.getMessage();
    }
}

def callPostProcess(cur_env) {
    try {
        echo "Running post processing"
        bat "${pipeline["javaCmd"]} -Upgrade -ProjectName ${pipeline["pipeline"]} -EnvName ${cur_env} -PackageName ${postProcess} -Server ${pipeline["server"]} ${pipeline["credential"]}"
    } catch (Exception e) {
        echo e.getMessage();
    }
}

@NonCPS
def shouldDeploy(cur_env) {
    if (cur_env.contains("FIT")) {
        echo env.Optional_Environment_Deploy
        echo cur_env
        if (cur_env.contains(env.Optional_Environment_Deploy) || env.Optional_Environment_Deploy == "BOTH") {
            do_it = true
        } else {
            do_it = false
        }
    } else if (cur_env == "DryRun") {
        if (env.Optional_DryRun_Deploy == "Yes") {
            do_it = true
        } else {
            do_it = false
        }
    } else {
        do_it = true;
    }
    return do_it
}

@NonCPS
def getNextVersion(optionType){
  //Get version from currentVersion.txt file D:\\repo\\N8
  // looks like this:
  // develop=1.10.01
  // release=1.9.03
  def newVersion = ""
  def curVersion = [:]
  def versionFile = "D:\\n8dml\\N8\\currentVersion.txt"
  def contents = readFile(versionFile)
  contents.split("\r\n").each{ -> cur
    def pair = cur.split("=")
    curVersion[pair[0].trim()] = pair[1].trim()
  }
  
  switch (optionType.toLowerCase()) {
    case "develop":
      curVersion["develop"] = newVersion = incrementVersion(curVersion["develop"])
      break
    case "hotfix":
      curVersion["develop"] = newVersion = incrementVersion(curVersion["develop"], "other")
      break
    case "cross_over":
      curVersion["release"] = newVersion = incrementVersion(curVersion["release"])
      break
    case "dml":
      curVersion["release"] = newVersion = incrementVersion(curVersion["release"], "other")
      break
  }
  stg = "develop=${curVersion["develop"]}\r\n"
  stg += "release=${curVersion["release"]}"
  fil.write(stg)
  fil.close()
  return newVersion
}

@NonCPS
def incrementVersion(ver, process = "normal"){
  // ver = 1.9.04
  def new_ver = ver
  def parts = ver.split('\\.')
  if(process == "normal"){
      parts[2] = (parts[2].toInteger() + 1).toString()
      new_ver = parts[0..2].join(".")
  }else{
      if(parts.size() > 3){
          parts[3] = (parts[3].toInteger() + 1).toString()
      }else{
          parts = parts + '1'
      }
      new_ver = parts[0..3].join(".")
  }
  return "V" + new_ver
}


return this;
