import sys
import subprocess
import os
import time
import queue
import threading
import docker
import json

# Get the full path of the executable file
exe_path = os.path.abspath(__file__)

# Construct the full path of the "options.json" file
options_path = os.path.join(os.path.dirname(exe_path), "options.json")
persistent_volume_path = os.path.join(os.path.dirname(exe_path), "pvc.json")
docker_dep_path = os.path.join(os.path.dirname(exe_path), "docker_dep.txt")
docker_sps_path = os.path.join(os.path.dirname(exe_path), "docker_sps.txt")

def try_get_application(name):
  command = f"sps-client application read --name {name}"
  try:
    output = subprocess.check_output(command, shell=True, stderr=subprocess.PIPE)

    data = json.loads(output.decode())

    return True, data
  except subprocess.CalledProcessError as e:
    return False, None

def does_image_tag_exist(client, image, tag):
    try:
        client.images.get(f"{image}:{tag}")
        return True
    except docker.errors.ImageNotFound:
        return False


def switch_active_version(branch, version):
    print("Setting active version...\n")
    subprocess.run(
        f"sps-client application update --name {branch} --activeVersion {version}"
    )

def set_new_version(branch, version, container_tag=None, resetting=False, path=options_path):
    if container_tag == None:
      container_tag = f"docker.io/dgodfrey206/{branch}:{version}"
    if resetting == True:
        print("Deleting version...")
        subprocess.run(f"sps-client version delete --name {version} --application {branch}")
    print("Creating new version...")
    subprocess.check_output("timeout 2")
    subprocess.run(
        ['sps-client', 'version', 'create', '--application', branch, '--name', version, '--buildOptions.input.containerTag', container_tag, '--buildOptions.credentials.registry', "https://index.docker.io/v1/", '-f', path ]
    )
    switch_active_version(branch, version)

def reset_app_version(branch, path=options_path):
    exists, data = try_get_application(branch)
    if exists:
      if data['response']['activeVersion']:
        version = data['response']['activeVersion']['name']
        set_new_version(branch, version, resetting=True, path=path)

def make_new_application(branch, version, tag=None):
    sys.stdout.write("Creating application")
    print_dots(25)
    subprocess.run(f"sps-client application create --name {branch}")
    set_new_version(branch, version, container_tag=tag)

def reset_application(branch, image_tag=None):
    exists, data = try_get_application(branch)
    ctag = None
    if exists:
        activeVersion = data["response"]["activeVersion"].lower().replace('_', '-')

        if image_tag == None:
            image_tag = f"{branch}:{activeVersion}"
            ctag = f"docker.io/dgodfrey206/{image_tag}"
            if not activeVersion:
                print(f"error: app '{branch}' has no set version. can't reset")
                sys.exit(1)
            else:
                versions = data["response"]["versions"]
                for v in range(0, len(versions)):
                    if versions[v]["name"] == activeVersion:
                        ctag = versions[v]["buildOptions"]["input"]["containerTag"]
                        break

        print(f"Delete {branch}...")
        subprocess.run(f"sps-client application delete --name {branch}")
    else:
        print(f"error: app '{branch}' does not exist")
        sys.exit(1)

    if image_tag == None:
        print(
            f"error: app '{branch}' does not exist. deploy a new build or provide an existing version to reset to (i.e sps-app reset {branch} --tag 23-03-14_build-A_CD_RelatedBanyan)"
        )
        sys.exit(1)
    version = image_tag.split(':')[1].lower().replace('_', '-')
    make_new_application(branch, version, ctag)

    sys.stdout.write("Finishing up")
    print_dots(6)
    print("FINISHED")

def show_help():
    print(
        "usage: sps-app deploy <dir> [-b or --branch] <branch> [options...]\n\
-A, --app-only            Only deploy the client\n\
-b, --branch              The application branch to deploy to (dev, demo, prophet, etc.)\n\
-h, --help                Get help for commands\n\
-S, --server-only         Only deploy the server\n\
    --add-volume-mount    Add a storage volume to the application\n\
    --remove-volume-mount Remove the existing storage volume\n\
    --firebase            Deploys it with the necessary dependencies for firebase\n\
    --config              Path to the JSON configuration file\n"
    )
    print("Example: sps-app deploy 22-11-23_build-A-CD --branch dev")


def print_periodic(interval):
    while True:
        sys.stdout.write(". ")
        sys.stdout.flush()
        time.sleep(interval)


def print_dots(duration):
    q = queue.Queue()

    def print_dots_thread():
        end_time = time.time() + duration
        while time.time() < end_time:
            q.put(". ")
            time.sleep(1)
        q.put(None)  # Signal end of dots

    thread = threading.Thread(target=print_dots_thread)
    thread.start()

    while True:
        item = q.get()
        if item is None:
            break
        print(item, end="")
        sys.stdout.flush()

def build_docker_image(branch, image_tag):
    # Add dependencies if image tag does not exist
    client = None
    try:
        client = docker.from_env()
        client.ping()
    except docker.errors.DockerException:
        print("error: Docker Desktop is not running.")
        sys.exit(1)

    client.login(
        username="dgodfrey206",
        password="applesauce",
        registry="https://index.docker.io/v1/",
    )

    Dockerfile = """
	FROM adamrehn/ue4-runtime:20.04-cudagl11.1.1

	USER root
	RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub
	RUN apt-get update && apt-get -y upgrade
	RUN apt-get install -y libsecret-1-0

        # Copy the packaged project files from the build context
        COPY --chown=ue4:ue4 LinuxClient /home/ue4/project

        # Ensure the project's startup script is executable
        RUN chmod +x "/home/ue4/project/ThirdTurn_TemplateClient.sh"

	USER ue4

        # Set the project's startup script as the container's entrypoint
        ENTRYPOINT ["/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_TemplateClient.sh"]
    """

    with open("../Dockerfile", "w") as f:
        f.write(Dockerfile)
    
    os.system(f"docker build -t dgodfrey206/{image_tag} ..")
    #os.system(f"docker tag {image_tag} dgodfrey206/{image_tag}")
    os.system(f"docker push dgodfrey206/{image_tag}")



def deploy(argv):
    branch = None
    build = None
    app_only = False
    server_only = False
    use_firebase = False

    global options_path

    options = [
        "-h",
        "--help",
        "-A",
        "-b",
        "--branch",
        "-h",
        "--help",
        "-S",
        "--server-only",
        "--app-only",
        "--config",
        "--add-volume-mount",
        "--remove-volume-mount",
        "--firebase"
    ]

    reset_version = False
    argv = argv.split()

    if len(argv) < 1:
        show_help()
        sys.exit(1)

    dir_name = os.path.abspath(argv[0])

    for i in range(0, len(argv)):
        opt = argv[i]
        if opt[0] == "-" and opt not in options:
            print(f"Invalid option {opt}")
            show_help()
            sys.exit(1)
        if opt == "--help" or opt == "-h":
            show_help()
            sys.exit(0)
        if opt == "--branch" or opt == "-b":
            if i + 1 >= len(argv):
                print("error: --branch provided without an argument")
                sys.exit(1)
            branch = argv[i + 1]
        if opt == "-A" or opt == "--app-only":
            app_only = True
        if opt == "-S" or opt == "--server-only":
            server_only = True
        if opt == "--config":
            if i + 1 >= len(argv):
                print("error: --config provided without a path")
                sys.exit(1)
            options_path = argv[i + 1]
            reset_version = True
        if opt == "--add-volume-mount":
            options_path = persistent_volume_path
            reset_version = True
        if opt == "--remove-volume-mount":
            reset_version = True
        if opt == "--firebase":
            use_firebase = True

    if not os.path.exists(dir_name):
        print(f"error: directory {dir_name} does not exist.")
        sys.exit(1)

    if app_only and not os.path.exists(os.path.join(dir_name, "LinuxClient")):
        print("error: file LinuxClient does not exist in {}".format(dir_name))
        sys.exit(1)

    if server_only and not os.path.exists(os.path.join(dir_name, "LinuxServer")):
        print("error: file LinuxServer does not exist in {}".format(dir_name))
        sys.exit(1)

    if branch == None:
        print("error: -b or --branch is required (one of dev, prophet, demo, etc.)")
        print("Example: sps-app deploy 22-11-23_build-A-CD --branch dev")
        sys.exit(1)

    os.chdir(dir_name)
    dir_name = os.path.basename(dir_name).lower().replace('_', '-')
    image_tag = f"{branch}:{dir_name}"

    if not server_only:
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxClient")):
            print("error: file LinuxClient does not exist in {}".format(os.path.abspath(os.getcwd())))
            sys.exit(1)

        os.chdir("LinuxClient")

        if use_firebase == False:
            subprocess.run(f'image-builder create --package . --tag "docker.io/dgodfrey206/{image_tag}"')
        else:
            build_docker_image(branch, image_tag)

        exists, data = try_get_application(branch)

        version = image_tag.split(":")[1]

        # Set a new version if this version doesn't already exist
        if exists:
            set_new_version(branch, version, resetting=reset_version, path=os.path.join("..", options_path))
        else:
            make_new_application(branch, version)
            sys.stdout.write("Finishing up")
            print_dots(6)
        os.chdir("..")

    if not app_only:
        print("Uploading server...")
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxServer")):
            print("error: file LinuxServer does not exist in {}".format(os.path.abspath(os.getcwd())))
            sys.exit(1)

        subprocess.run(
          f'ssh david@prophet.palatialxr.com "sudo systemctl stop server_{branch}.service"'
        )
        subprocess.check_output(
          "scp -r LinuxServer david@prophet.palatialxr.com:~/servers/" + branch
        )
        subprocess.run(
          f'ssh david@prophet.palatialxr.com "sudo systemctl start server_{branch}.service"'
        )
        subprocess.run(
          f'ssh david@prophet.palatialxr.com "echo "{dir_name}" >> ~/servers/{branch}/version.log"'
        )

    print("FINISHED")
