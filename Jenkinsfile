/*
#---------- Jenkinsfile Stub ------------------#
This file will call the central PipelineInclude module which contains the pipeline logic.  In this file you can
put things specific to the branch that drives this work. Use the settings map to pass any variables into the
master include.
*/
// Set this library variable in Jenkins settings Global Pipeline Libraries section
@Library('DBmGlobal') _

println "#----------- Remote Pipeline Execution ------------#"
// The keys and values in settings will be added to (or overwrite) the settings in the local_settings.json file
def settings = [
	"pipeline" : "MultiBranch",
  "settings_file" : "C:\\Automation\\jenkinspipe\\local_settings_include.json"  
]
// Add a properties for Platform and Skip_Packaging more
properties([
        parameters([
          string(name: 'Version', description: "Enter Version for the Deploy", defaultValue: "V0.0.0"),
          choice(name: 'Skip_Packaging', description: "Yes/No to skip packaging step", choices: 'No\nYes')
        ])
])

def pipe = new org.dbmaestro.PipelineInclude()
pipe.execute(settings)
println "Finished"