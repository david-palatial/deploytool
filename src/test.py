import subprocess
import misc

host = 'david@palatial.tenant-palatial-platform.coreweave.cloud'

subprocess.run('ssh david@palatial.tenant-palatial-platform.coreweave.cloud sudo mkdir -p /usr/local/bin/cw-app-logs/dev/server')

print(misc.file_exists_on_remote(host, '/etc/systemd/system/server_demo.service'))