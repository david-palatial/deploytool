def show_spsApp_help():
  print("usage: sps-app [command] [options]\n\
deploy          Deploy a new build\n\
reset, restart  Reset an application\n\
update          Change settings for an application\n\
create          Create an application\n\
delete          Delete an application\n\
shell           Open a shell to the VM\n\
config          Set the SPS server\n\
setup           Set up sps-app\n\
version-info    Display active version info\n\
restart-server  Restarts a dedicated server\n\
restart-webpage Restarts a webpage\n\
-h, --help      Show help menu\n\n\
\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app reset demo")

def show_Deploy_help():
    print(
        "Deploys a packaged UE client to the SPS server and/or a packaged UE server to the palatial VM\n\n\
usage: sps-app deploy <dir> [options...]\n\n\
-A, -C, --app-only, --client-only  Only deploy the client\n\
-S,     --server-only              Only deploy the server\n\
-I,     --image-only               Deploy the image to Docker Hub only\n\
-b,     --branch                   The application branch to deploy to (dev, demo, prophet, etc.)\n\
        --vn, --version-name       Name the version for the application\n\
        --add-volume-mount         Add a storage volume to the application\n\
-F,     --firebase                 Deploys it with the necessary dependencies for firebase\n\
        --config                   Path to the JSON configuration file\n\
-h,     --help                     Get help for commands\n\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app deploy 23-06-13_build-A_CD_OfficeStandalone -b officedemo --server-only\n\
Example: sps-app deploy . -FA --add-volume-mount --config ../settings.json")

def show_reset_help():
  print("Deletes and recreates the client application\n\n\
usage: sps-app [reset or restart] <branch> [options...]\n\n\
-t, --tag       The Docker image tag of the version to reset to\n\
-h, --help      Show help menu\n\n\
Example: sps-app reset demo\n\
Example: sps-app restart demo --tag 23-04-20_build-A_CD_PalatialTest")

def show_delete_help():
  print("Deletes the application\n\n\
usage: sps-app delete <branch>\n\n\
-h, --help,     Show help menu\n\n\
Example: sps-app delete prophet")

def show_create_help():
  print("Creates an application\n\n\
usage: sps-app create <branch> [options...]\n\n\
-t, --tag                  Create an application using an existing Docker image tag\n\
    --vn, --version-name   Optionally provide a name for the new version when creating from an image tag\n\
-h, --help                 Show help menu\n\n\
Example: sps-app create prophet\n\
Example: sps-app create prophet --tag 22-10-05_build-DG_Prophet")

def show_shell_help():
  print("Opens an SSH connection to the palatial VM\n\n\
usage: sps-app shell\n\n\
-h, --help   Show help menu\n\
\n\
Example: sps-app shell")

def show_config_help():
  print("Configuration for the SPS server\n\n\
usage: sps-app config [command]\n\n\
update   Configure sps-client with the new SPS REST API key (Uses LGA1 region by default)\n\
   -p, --key, --access-key, --password    Provide the API key manually\n\
       --auto                             Fetches the API key and updates sps-client automatically\n\
       --lga                              Uses the LGA1 region\n\
       --ord                              Uses the ORD1 region\n\
       --las                              Uses the LAS1 region\n\
get-key  Get the API key for the SPS server\n\
\n\
Example: sps-app config update --auto\n\
Example: sps-app config update --access-key ez2UroRWSJpEkahedev80neMGOGrDo6U\n\
Example: sps-app config get-key\n\
output: ez2UroRWSJpEkahedev80neMGOGrDo6U")

def show_Restart_Webpage_help():
  print("Restarts the webserver for the specified branch\n\n\
usage: sps-app restart-webpage <branch>\n\n\
-h, --help    Show help menu\n\
\n\
Example: sps-app restart-webpage tankhouse")

def show_update_help():
  print("Modify the application's settings\n\n\
usage: sps-app update <branch> [options...]\n\n\
    --add-volume-mount    Adds a storage volume to the application mounted at /home/ue4/\n\
    --remove-volume-mount Removes the storage volume\n\
-h, --help                Show help menu\n\
\n\
To see more options, run \"sps-client application update -h\"\n\
\n\
Example: sps-app update prophet --overProvisioning.instances 3")

def show_resetServer_help():
  print("Restarts the dedicated server for the specified branch\n\n\
usage: sps-app restart-server <branch>\n\n\
-h, --help      Show help menu\n\n\
Example: sps-app restart-server banyan")

def show_setup_help():
  print("Sets up Scalable Pixel Streaming command tools, installs kubectl, generates an SSH key and installs the Coreweave Access Token onto the system.\n\n\
usage: sps-app setup\n\n\
-h, --help   Show help menu\n\n\
Example: sps-app setup");

def show_Version_Info_help():
  print("Displays information for the currently active version of the application\n\n\
usage: sps-app version-info <branch>\n\n\
-h, --help      Show help menu\n\n\
Example: sps-app version-info oslodemo")