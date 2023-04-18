import groovy.json.*

// proj Deployment Pipeline
sep = "/"
def base_path = "/Users/brady.byrd/Documents/mongodb/dev/devops_atlas/DevOps_demo"

rootJobName = "$env.JOB_NAME";
template = "$env.Template";
branchName = "master"
branchVersion = ""
def base_env = "Dev"
def dbmNode = ""
def base_schema = ""
def version = "3.11.2.1"
def buildNumber = "$env.BUILD_NUMBER"

// Add a properties for Platform and Skip_Packaging
properties([
	parameters([
		string(name: 'Template', description: "template file in the Templates directory", defaultValue: 'm30_standard')
	])
])
/*
parameters{ 
  string(name: 'Version', description: "Enter Version for the Deploy", defaultValue: "V0.0.0"),
  text(name: 'mytextparam', 
                 defaultValue: 'Default lines for the parameter', 
                 description: 'A description of this param')    
}
*/

/*
#-----------------------------------------------#
#  Stages
*/

stage("Environment Check") {
  node (dbmNode) {
    //Copy from source to version folder
    sh "env"
  }
}

stage("Key Creation") {
  node (dbmNode) {
    echo "Calling GCP keyfile creation"
    echo "Expecting keypath and service account key returned"
  }
}

stage("Deploy") {
	//input message: "Deploy to ${environment}?", submitter: approver
	node (dbmNode) {
    echo '#------------------- Performing Deploy on ${template} --------------#'
      //  Use shell script to call python
      sh """
        echo Running python command
        cd ${base_path}
        python3 atlas_rest.py action=create_cluster template=${template}"""
  }  
} 

stage("Create Private Endpoint") {
  node (dbmNode) {
    echo "create stub PSC"
    echo "get script"
    echo "call cloud automation to create endpoint"
  }
}

// #-------------------------- UTILITIES --------------------------------#
@NonCPS
def ensure_dir(pth){
  folder = new File(pth)
  if ( !folder.exists() ){
    if( folder.mkdirs()){
        return true
    }else{
        return false
    }
  }else{
    return true
  }
}

def get_settings(file_path) {
	def jsonSlurper = new JsonSlurper()
	def settings = [:]
	println "JSON Settings Document: ${file_path}"
	def json_file_obj = new File( file_path )
	if (json_file_obj.exists() ) {
	  settings = jsonSlurper.parseText(json_file_obj.text)  
	}
	return settings
}

def message_box(msg, def mtype = "sep") {
  def tot = 80
  def start = ""
  def res = ""
  msg = (msg.size() > 65) ? msg[0..64] : msg
  def ilen = tot - msg.size()
  if (mtype == "sep"){
    start = "#${"-" * (ilen/2).toInteger()} ${msg} "
    res = "${start}${"-" * (tot - start.size() + 1)}#"
  }else{
    res = "#${"-" * tot}#\n"
    start = "#${" " * (ilen/2).toInteger()} ${msg} "
    res += "${start}${" " * (tot - start.size() + 1)}#\n"
    res += "#${"-" * tot}#\n"   
  }
  //println res
  return res
}

def separator( def ilength = 82){
  def dashy = "-" * (ilength - 2)
  //println "#${dashy}#"
}
