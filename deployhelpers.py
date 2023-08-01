import sys
import subprocess
import os
import time
import queue
import threading
import docker
import json
import random
import string
import misc

# Get the full path of the executable file
exe_path = os.path.abspath(__file__)

# Construct the full path of the "options.json" file
options_path = os.path.join(os.path.dirname(exe_path), "options.json")
persistent_volume_path = os.path.join(os.path.dirname(exe_path), "pvc.json")
docker_dep_path = os.path.join(os.path.dirname(exe_path), "docker_dep.txt")
docker_sps_path = os.path.join(os.path.dirname(exe_path), "docker_sps.txt")

def generate_random_letters():
    letters = random.choices(string.ascii_lowercase, k=2)
    numbers = random.choices(string.digits, k=1)
    return ''.join(random.sample(letters + numbers, k=3))

def transform_string(input_string):
    # Split the input string into date and random text parts
    date_part, random_text_part = input_string.split("-build-")

    # Remove dashes from the date part
    date_part = date_part.replace("-", "")

    # Generate random letters and numbers
    random_chars = generate_random_letters()

    # Construct the output string
    output_string = f"{date_part}-{random_text_part}-{random_chars}"

    return output_string

def new_string_format(str):
  return str + "-" + generate_random_letters()

def make_application_name(dir_name):
  return transform_string(dir_name)

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
        ['sps-client', 'version', 'create', '--application', branch, '--name', version, '--buildOptions.input.containerTag', container_tag, '--buildOptions.credentials.registry', "https://index.docker.io/v1/", '--buildOptions.credentials.username', 'dgodfrey206', '--buildOptions.credentials.password', 'applesauce', '-f', path ]
    )
    switch_active_version(branch, version)

def reset_app_version(branch, path=options_path):
    exists, data = misc.try_get_application(branch)
    if exists:
      if data['response']['activeVersion']:
        version = data['response']['activeVersion']
        set_new_version(branch, version, resetting=True, path=path)

def make_new_application(branch, version, tag=None, wait=True):
    sys.stdout.write("Creating application")
    if wait == True:
      print_dots(25)
    else:
      print_dots(3)
    subprocess.run(f"sps-client application create --name {branch}")
    set_new_version(branch, version, container_tag=tag)

def reset_application(branch, image_tag=None):
    exists, data = misc.try_get_application(branch)
    ctag = None
    if exists:
        activeVersion = data["response"]["activeVersion"].lower().replace('_', '-').replace('.', '-')
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
        "Deploys a packaged UE client to the SPS server and/or a packaged UE server to the palatial VM\n\n\
usage: sps-app deploy <dir> [-b or --branch] <branch> [options...]\n\n\
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
Example: sps-app deploy . -b tankhouse --firebase -A --add-volume-mount --config ../settings.json")

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
    # Get the current working directory
    current_directory = os.getcwd()

    # Extract the name of the current directory from the path
    directory_name = os.path.basename(current_directory)

    # Check if the directory name is "Linux" (case-sensitive)
    if directory_name == "Linux":
        folder_type = ""
    else:
        folder_type = "Client"

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

    Dockerfile = f"""
FROM adamrehn/ue4-runtime:20.04-cudagl11.1.1

# Install our additional packages
USER root

RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1604/x86_64/3bf863cc.pub
RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get -y upgrade && \
    apt-get install -y --no-install-recommends \
        libsecret-1-0 \
        libgtk2.0-0:i386 \
        libsm6:i386

USER ue4

# Copy the packaged project files from the build context
COPY --chown=ue4:ue4 "./Linux{folder_type}" /home/ue4/project

# Ensure the project's startup script is executable
RUN chmod +x "/home/ue4/project/ThirdTurn_Template{folder_type}.sh"

RUN ln -s /usr/lib/x86_64-linux-gnu/libsecret-1.so.0 /home/ue4/project/Palatial_V01_UE51/Binaries/Linux/libsecret-1.so.0
RUN ls -al /home/ue4/project/

# Set the project's startup script as the container's entrypoint
ENTRYPOINT ["/usr/bin/entrypoint.sh", "/home/ue4/project/ThirdTurn_Template{folder_type}.sh"]
    """

    with open("../Dockerfile", "w") as f:
        f.write(Dockerfile)
    
    os.system(f"docker build -t dgodfrey206/{image_tag} ..")
    os.system(f"docker push dgodfrey206/{image_tag}")

def starts_with_single_hyphen(s):
    return s.startswith('-') and not s.startswith('--')


def deploy(argv):
    branch = None
    build = None
    app_only = False
    server_only = False
    use_firebase = False
    image_only = False
    version = None
    self_selected_version = False

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
        "-C",
        "-I",
        "-F",
        "--vn",
        "--image-only",
        "--server-only",
        "--app-only",
        "--client-only",
        "--config",
        "--avm",
        "--add-volume-mount",
        "--firebase",
        "--version-name"
    ]

    single_options = ["-F", "-A", "-C", "-I", "-S"]

    reset_version = False
    argv = argv.split()

    if len(argv) < 1:
        show_help()
        sys.exit(1)

    dir_name = os.path.abspath(argv[0])

    for i in range(0, len(argv)):
      if starts_with_single_hyphen(argv[i]):
        for j in range(1, len(argv[i])):
          opt = argv[i][j]
          match opt:
            case 'A':
              app_only = True
            case 'S':
              server_only = True
            case 'I':
              image_only = True
            case 'F':
              use_firebase = True

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
        if opt == "--app-only" or opt == "--client-only":
            app_only = True
        if opt == "--server-only":
            server_only = True
        if opt == "--image-only":
            image_only = True
            app_only = True
        if opt == "--vn" or opt == "--version-name":
            if i + 1 >= len(argv):
              print("error: --version-name provided without an argument")
              sys.exit(1)
            version = argv[i + 1]
            self_selected_version = True
        if opt == "--config":
            if i + 1 >= len(argv):
                print("error: --config provided without a path")
                sys.exit(1)
            options_path = argv[i + 1]
            reset_version = True
        if opt == "--add-volume-mount":
            options_path = persistent_volume_path
            reset_version = True
        if opt == "--firebase":
            use_firebase = True

    if not os.path.exists(dir_name):
        print(f"error: directory {dir_name} does not exist.")
        sys.exit(1)

    if app_only and not os.path.exists(os.path.join(dir_name, "LinuxClient")) and not os.path.exists(os.path.join(dir_name, "Linux")):
        print(f"error: directory Linux or LinuxClient does not exist in {dir_name}")
        sys.exit(1)

    if server_only and not os.path.exists(os.path.join(dir_name, "LinuxServer")):
        print(f"error: directory LinuxServer does not exist in {dir_name}")
        sys.exit(1)

    if branch == None:
        print("error: -b or --branch is required (one of dev, prophet, demo, etc.)")
        print("Example: sps-app deploy 22-11-23_build-A-CD --branch dev")
        sys.exit(1)

    os.chdir(dir_name)
    if version == None:
      version = new_string_format(os.path.basename(dir_name).replace('_', '-')).lower()
    image_tag = f"{branch}:{version}"

    if not server_only:
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxClient")) and not os.path.exists(os.path.join(os.getcwd(), "Linux")):
            print(f"error: directory Linux or LinuxClient does not exist in {os.path.abspath(os.getcwd())}")
            sys.exit(1)

        if os.path.exists(os.path.join(os.getcwd(), "Linux")):
          os.chdir("Linux")
        elif os.path.exists(os.path.join(os.getcwd(), "LinuxClient")):
          os.chdir("LinuxClient")

        exists, data = misc.try_get_application(branch)
        if exists:
          d = data['response']
          if not self_selected_version:
            version = misc.increment_version(d['activeVersion'])
          image_tag = f"{branch}:{version}"

        if use_firebase:
            build_docker_image(branch, image_tag)
        else:
            subprocess.run(f'image-builder create --package . --tag "docker.io/dgodfrey206/{image_tag}"')

        if image_only:
          print("FINISHED")
          sys.exit(0)

        # Set a new version if this version doesn't already exist
        if exists:
            print(f'making version: {version}')
            set_new_version(branch, version, resetting=reset_version, path=os.path.join("..", options_path))
        else:
            make_new_application(branch, version, wait=False)
            if app_only:
              sys.stdout.write("Finishing up")
              print_dots(6)
        os.chdir("..")

    if not app_only:
        print("\nUploading server...")
        if not os.path.exists(os.path.join(os.getcwd(), "LinuxServer")):
            print(f"error: directory LinuxServer does not exist in {os.path.abspath(os.getcwd())}")
            sys.exit(1)

        host = 'david@new-0878.tenant-palatial-platform.coreweave.cloud'

        exists = misc.file_exists_on_remote(host, f'/etc/systemd/system/server_{branch}.service')
 
        if exists:
          subprocess.run(f'ssh {host} "sudo systemctl stop server_{branch}.service"')
        else:
          subprocess.run(f'ssh {host} mkdir -p ~/servers/{branch}/LinuxServer')

        subprocess.check_output(f'scp -r LinuxServer/* {host}:~/servers/{branch}/LinuxServer/')

        if exists:
          subprocess.run(f'ssh {host} "sudo systemctl start server_{branch}.service"')

        subprocess.run(
          f'ssh {host} "echo "{dir_name if version == None else version}" > ~/servers/{branch}/version.log"'
        )

    print("FINISHED")
