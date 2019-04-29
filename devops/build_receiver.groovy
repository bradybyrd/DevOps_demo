sep = "\\"

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
	separator()
	println "Running: ${command}"
	println "out> " + result["stdout"]
	println "err> " + result["stderr"]
}

println "#=> Running Build Hook"
def cmd = "cd C:\\Automation\\MultiBranch && @git log -1 HEAD --pretty=format:%s"
def res = shell_execute(cmd)
display_result(cmd,res)