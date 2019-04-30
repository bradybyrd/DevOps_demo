sep = "\\" //FIXME Reset for unix
base_path = new File(getClass().protectionDomain.codeSource.location.path).parent
// Local Variables
pipeline = "HR_Tasks"
base_schema = "MP_DEV2"
staging_path = "C:\\Automation\\MP\\${pipeline}"
base_version = "V3.6."
arg_map = [:]

for (arg in this.args) {
  //logit arg
  pair = arg.split("=")
  if(pair.size() == 2) {
    arg_map[pair[0].trim()] = pair[1].trim()
  }else{
    arg_map[arg] = ""
  }
}

if (arg_map.containsKey("action")) {
  switch (arg_map["action"].toLowerCase()) {
    case "roll_forward":
      roll_forward()
      break
    case "git_trigger":
      git_trigger()
      break
    case "stage_files":
      stage_files()
      break
    default:
      println "Action does not exist"
	  System.exit(1)
      break
  }
}else{
	println "Error: specify action=<action> as argument"
	System.exit(1)
}
def shell_execute(cmd, path = "none"){
  def pth = ""
  def command = sep == "/" ? ["/bin/bash", "-c"] : ["cmd", "/c"]
  if(path != "none") { 
	pth = "cd ${path} && "
	command << pth
  }
	command << cmd
  def sout = new StringBuffer(), serr = new StringBuffer()
  //println "Running: ${command}"
	def proc = command.execute()
	proc.consumeProcessOutput(sout, serr)
	proc.waitForOrKill(1000)
  def outtxt = ["stdout" : sout, "stderr" : serr]
  return outtxt
}

def display_result(command, result){
	println "#------------------------------------------------------#"
	println "Running: ${command}"
	println "out> " + result["stdout"]
	println "err> " + result["stderr"]
}

def message_box(msg, def mtype = "sep") {
  def tot = 100
  def start = ""
  def res = ""
  msg = (msg.size() > 85) ? msg[0..84] : msg
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
  println res
  return res
}

def separator( def ilength = 82){
  def dashy = "-" * (ilength - 2)
  println "#${dashy}#"
}

// #---------------------- MAIN ----------------------------------#

def git_trigger() {
	def reg = ~/.*\[DBCR: (.*)\].*/
	def cmd = "git log -1 HEAD --pretty=format:%s"
	def res = shell_execute(cmd)
	def msg = res["stdout"]
	def commit = System.getenv("GIT_COMMIT").trim()
	message_box("Git Trigger")
	println "# Commit: ${msg}"
	println "# Revision: ${commit}"
	//display_result(cmd,res)
	def result = msg.replaceFirst(reg, '$1')
	println "Version: ${result}"
	//Pick new files in commit
	/// git diff-tree --no-commit-id --name-only -r 32b0f0dd6e4bd810f3edc4bcd8a114f8f98a65ea
	cmd = "git diff-tree --no-commit-id --name-only -r ${commit}"
	res = shell_execute(cmd)
	display_result(cmd,res)
	def files = res["stdout"].split("\n")
	println "Files: ${files}"
	// copy to packaging
	// upgrade
}

def roll_forward() {
	// Build has been run in dbmaestro step first
	def do_deploy = System.getenv("Package_and_Deploy").trim()
	def workspace = System.getenv("WORKSPACE").trim()
	def cur_version = "${base_version}${System.getenv("BUILD_NUMBER").trim()}"
	def dir_list = new File("${staging_path}${sep}REPORTS").listFiles()?.sort { -it.lastModified() }
	//println "Reports: ${dir_list}"
	def picked = dir_list.head()
	//println "Dir: ${picked}"
	def cur_report = new File(picked.toString()).listFiles()?.head().toString()
	println "Picked: ${cur_report}"
	def cmd = "copy ${cur_report} ${base_schema}\\"
	def res = shell_execute(cmd)
	display_result(cmd,res)
	if(do_deploy == "Yes"){
		cmd = "mkdir ${staging_path}${sep}${base_schema}${sep}${cur_version}"
		res = shell_execute(cmd)
		display_result(cmd,res)
		dir_list = new File("${workspace}${sep}${base_schema}").listFiles()?.sort { -it.lastModified() }
		picked = dir_list.head().toString()
		message_box("Version Created - ${cur_version}")
		println "# In path: ${staging_path}${sep}${base_schema}${sep}${cur_version}"
		cmd = "copy \"${picked}\" ${staging_path}${sep}${base_schema}${sep}${cur_version}${sep}"
		res = shell_execute(cmd)
		display_result(cmd,res)
	}	
}

def stage_files(){
	// optional copy files step in package and deploy
	def do_staging = System.getenv("STAGE_FILES").trim()
	def workspace = System.getenv("WORKSPACE").trim()
	def cur_version = System.getenv("VERSION").trim()
	def strip_version = cur_version
	if(cur_version.startsWith("V")){
		strip_version = cur_version[1..-1]
	}else{
		cur_version = "V${cur_version}"
	}
	message_box("Package and Deploy - ${cur_version}")
	println "# In path: ${staging_path}${sep}${base_schema}${sep}${cur_version}"
		
	if(do_staging == "Yes"){
		println "# Copying scripts from: ${workspace}${sep}Deploy${sep}${strip_version}"
		def cmd = "mkdir ${staging_path}${sep}${base_schema}${sep}${cur_version}"
		def res = shell_execute(cmd)
		display_result(cmd,res)
		cmd = "copy \"${workspace}${sep}Deploy${sep}${strip_version}\\*\" ${staging_path}${sep}${base_schema}${sep}${cur_version}${sep}"
		res = shell_execute(cmd)
		display_result(cmd,res)
	}	
	
}
