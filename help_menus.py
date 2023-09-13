def show_spsApp_help():
  print("usage: sps-app [command] [options]\n\
deploy          Deploy a new build\n\
reset, restart  Reset an application\n\
update          Change application settings\n\
create          Create an application\n\
delete          Delete an application\n\
shell           Open a shell to the VM\n\
config          Configure sps-app\n\
setup           Set up sps-app\n\
version-info    Display active version info\n\
restart-server  Restarts a dedicated server\n\
restart-webpage Restarts the webserver\n\
enable          Activates an application with the latest version\n\
disable         Removes the active version from an application\n\
create-link     Add a frontend for the application\n\
-h, --help      Show help menu\n\n\
\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app reset demo")

def show_Deploy_help():
    print(
        "Deploys a packaged UE client to the SPS server and/or a packaged UE server to the palatial VM\n\n\
usage: sps-app deploy <dir> [options...]\n\n\
-A, -C, --app-only, --client-only          Only deploy the client\n\
-S,     --server-only                      Only deploy the server\n\
-I,     --image-only                       Deploy only the image to Docker Hub\n\
-b,     --branch                           The application branch to deploy to (dev, demo, prophet, etc.)\n\
        --owner                            The subdomain the application belongs to\n\
        --vn, --version-name               Name the version for the application\n\
        --add-volume-mount                 Add a storage volume to the application\n\
-F,     --custom-docker-build, --firebase  Deploys with custom dependencies\n\
        --create-link                      Include a frontend that runs the application\n\
        --config                           Path to the JSON configuration file\n\
-h,     --help                             Get help for commands\n\n\
Example: sps-app deploy 22-11-23_build-A-CD --branch dev\n\
Example: sps-app deploy 23-06-13_build-A_CD_OfficeStandalone -b officedemo --server-only\n\
Example: sps-app deploy . -FA --add-volume-mount --config ../settings.json")

def show_reset_help():
  print("Deletes and recreates the client application\n\n\
usage: sps-app [reset or restart] <branch> [options...]\n\n\
-t, --tag                  The Docker image tag of the version to reset to\n\
    --vn, --version-name   Optionally provide a name for the new version\n\
-h, --help      Show help menu\n\n\
Example: sps-app reset demo\n\
Example: sps-app restart demo --tag v0-0-4 --version-name version4")

def show_enable_help():
  print("Sets the active version to the latest version\n\n\
usage: sps-app enable <branch>\n\n\
-h, --help      Show help menu\n\n\
Example: sps-app enable oslodemo")

def show_disable_help():
  print("Removes the active version\n\n\
usage: sps-app disable <branch> [options...]\n\n\
-h, --help      Show help menu\n\n\
Example: sps-app disable oslodemo")

def show_delete_help():
  print("Deletes the application(s) and their associated web servers and dedicated servers\n\n\
usage: sps-app delete <branch>...\n\n\
        --full  Delete the SPS application and its backend servers\n\
-h,     --help  Show help menu\n\n\
Example: sps-app delete prophet demo dev")

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
  print("Configuration options for sps-app\n\n\
usage: sps-app config [options...]\n\n\
--api-key                  Get/set the API key for the SPS REST API server\n\
--registry-endpoint        Get/set the image registry API endpoint (i.e https://index.docker.io/v2/)\n\
--registry-username        Get/set the image registry username\n\
--registry-password        Get/set the image registry password\n\
--registry-password-stdin  Set the image registry password privately\n\
--repository-url           Get/set the base domain for the image repository (i.e docker.io/dgodfrey206/)\n\
--coreweave-namespace      Get/set your coreweave namespace\n\
--server-name              Get/set the name of the REST API server\n\
--region                   Get/set the region (i.e lga1, ord1, las1)\n\
--fetch-api-key            Fetches and updates sps-app with the latest API key\n\
--list                     Prints out all configurable settings\n\
\
\n\
Example: sps-app config --fetch-api-key\n\
Example: sps-app config --registry-username dgodfrey206 --registry-password thepassword --server-name palatial-sps-server\n\
Example: sps-app config --api-key\n\
Example output: ez2UroRWSJpEkahedev80neMGOGrDo6U")

def show_Restart_Webpage_help():
  print("Restarts the webserver\n\n\
usage: sps-app restart-webpage\n\n\
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
  print("Sets up Scalable Pixel Streaming CLI tools and generates an SSH key pair.\n\n\
usage: sps-app setup\n\n\
    --stdin  Enter all config values manually\n\
-h, --help   Show help menu\n\n\
Example: sps-app setup");

def show_Version_Info_help():
  print("Displays information for the currently active version of the application\n\n\
usage: sps-app version-info <branch>\n\n\
-h, --help      Show help menu\n\n\
Example: sps-app version-info oslodemo")

def show_createLink_help():
  print("Adds a frontend that runs the given application\n\n\
usage: sps-app create-link <branch>\n\n\
    --owner     The subdomain that the application belongs to (i.e test)\n\
-h, --help      Show help menu\n\n\
Example: sps-app create-link oslodemo")