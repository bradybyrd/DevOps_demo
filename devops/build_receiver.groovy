sep = "\\" //FIXME Reset for unix
base_path = new File(getClass().protectionDomain.codeSource.location.path).parent
// Local Variables
def pipeline = "HR_Tasks"
def staging_path = "C:\\Automation\\MP\\${pipeline}"

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

println "#=> Running Build Hook"
def cmd = "cd C:\\Automation\\MultiBranch && @git log -1 HEAD --pretty=format:%s"
def res = shell_execute(cmd)
display_result(cmd,res)

def dir_list = new File("${staging_path}${sep}REPORTS").listFiles()?.sort { -it.lastModified() }
println "Reports: ${dir_list}"
def picked = dir_list.head()
println "Dir: ${picked}"
def cur_report = new File(picked.toString()).listFiles()?.head()
println "Picked: ${cur_report}"
cmd = "cd C:\\Automation\\MultiBranch && @git log -1 HEAD --pretty=format:%s"
res = shell_execute(cmd)
display_result(cmd,res)