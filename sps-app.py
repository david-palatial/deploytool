import sys
import subprocess
import os
from deployhelpers import print_dots, deploy, reset_application

def show_spsApp_help():
  print("usage: sps-app [command]\n\
deploy      Deploys a new build\n\
reset       Reset an application\n\
update      Update options for an application\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app reset demo")

def show_reset_help():
  print("Resets the client application\n\
usage: sps-app reset <branch> [options...]\n\
-t, --tag       The existing application version to reset to\n\
Example: sps-app reset demo\n\
Example: sps-app reset demo --tag 23-04-20_build-A_CD_PalatialTest")

if len(sys.argv) < 2 or sys.argv[1] != "deploy" and sys.argv[1] != "reset" and sys.argv[1] != "update":
  show_spsApp_help()
  sys.exit(1)

command = sys.argv[1];

for i in range(1, len(sys.argv)):
  opt = sys.argv[i]
  if opt == "--help" or opt == "-h" or opt == "help":
    show_spsApp_help()
    sys.exit(0)

if command == "deploy":
  # Retrieve values from sys.argv starting from index 3 onward
  values = sys.argv[2:]
  
  # Convert the list of values into a string
  values_str = ' '.join(values)

  deploy(values_str)
  sys.exit(0)

if command == "reset":
  if len(sys.argv) < 3:
    show_reset_help()
    sys.exit(1)
  branch = sys.argv[2]
  image_tag = None
  if len(sys.argv) == 5 and (sys.argv[3] == "-t" or sys.argv[3] == "--tag"):
    image_tag = f"{branch}:{sys.argv[4]}"
  reset_application(branch, image_tag)
  sys.exit(0)
if command == "update":
  if len(sys.argv) < 4:
    show_spsApp_help()
    sys.exit(1)
  branch = sys.argv[2]
  subprocess.run(f"sps-client application update --name {branch} " + " ".join(sys.argv[3:]))