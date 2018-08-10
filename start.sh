#!/usr/bin/env bash

# ensure envars are loaded
source /root/.bash_profile

# set droplet ID
export DROPLET_UID=$(curl -s http://169.254.169.254/metadata/v1/id)
export DROPLET_NAME=$(curl -s http://169.254.169.254/metadata/v1/hostname)

# create ssh tunnels for connection to rabbitmq, the database, and the api
autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -L 5672:localhost:5672 root@206.81.5.140 &
autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -L 5432:localhost:5432 root@206.81.5.140 &
#autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -L 5000:localhost:5000 root@206.81.5.140 &


#### FUNCTIONS

function monitor()
{
  while true; do
    executable_line=$1 # /var/lib/jobs/$JOB_NAME/sentencer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/sentencer/sentencer.py
    process_count=$2 # 4
    short_name=$3 # sentencer.py 
    echo $executable_line $process_count $short_name
    if [[ "$(ps aux | grep $short_name | awk '{print $2}' | wc -l)" < $process_count ]]; then
      nohup $executable_line &
      echo 'restarted dead process' >> /var/log/jobrunnerlogs/monitor.log
    fi
    sleep 5s
  done
}


#### END FUNCTIONS

# wait for ssh tunnels to be created, ready to go
sleep 10s

# test connection to api, attempt to establish one if it doesn't exist
#curl localhost:5000 || autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -L 5000:localhost:5000 root@206.81.5.140 &

# start the system monitor script
nohup /var/lib/jobs/$JOB_NAME/venv/bin/python3 /var/lib/jobs/$JOB_NAME/system_monitor.py &

## start link publisher
#nohup /var/lib/jobs/$JOB_NAME/sentencer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/sentencer/publisher.py &
#link_publisher_process=$!
#
### start sentence writer
#nohup /var/lib/jobs/$JOB_NAME/sentencer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/sentencer/writer.py &
#sentence_writer_process=$!
#
## start sentence extractor (1 per box, memory overhead)
## Start x reducers
#cpu_count=$(grep -c ^processor /proc/cpuinfo)
#monitor "/var/lib/jobs/$JOB_NAME/sentencer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/sentencer/sentencer.py" $cpu_count sentencer.py &

## start pre-reduction (sentence) publisher
nohup /var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/publisher.py &
prereduction_publisher_process=$!
#
## start reduction writer
nohup /var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/writer.py &
reduction_writer_process=$!
#
## Start x reducers
cpu_count=$(grep -c ^processor /proc/cpuinfo)
monitor "/var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/reducer.py" $cpu_count reducer.py &

## the droplet is no longer needed, droplet makes
## a DELETE request on itself.
#curl --user $JM_USER:$JM_PASS -X DELETE $JOB_MANAGER/droplets/$DROPLET_UID
