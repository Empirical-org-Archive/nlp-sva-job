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

# wait for ssh tunnels to be created, ready to go
sleep 10s

# test connection to api, attempt to establish one if it doesn't exist
#curl localhost:5000 || autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -N -L 5000:localhost:5000 root@206.81.5.140 &

# start the system monitor script
nohup /var/lib/jobs/$JOB_NAME/venv/bin/python3 /var/lib/jobs/$JOB_NAME/system_monitor.py &

# make sure requirements are fully installed
sleep 5m

# start pre-reduction publisher
nohup /var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/publisher.py &
prereduction_publisher_process=$!

# start reduction writer
nohup /var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/writer.py &
reduction_writer_process=$!

# Start x reducers
cpu_count=$(grep -c ^processor /proc/cpuinfo)
worker_count=$(( cpu_count / 1 ))
reducer_processes=()
for i in $(seq 1 $worker_count)
do
  nohup /var/lib/jobs/$JOB_NAME/reducer/venv/bin/python3 /var/lib/jobs/$JOB_NAME/reducer/reducer.py &
  reducer_processes+=($!)
done

# wait until reduction is complete
while [ true ]
do
    sleep 1m
    export r=$(curl --user $JM_USER:$JM_PASS $JOB_MANAGER/jobs/$JOB_ID/state) && [ $r == \"reduced\" ] && break || continue
done


# TODO: bad code, remove this - fix should be in reducers where job state is
# updated
# wait for all reducers in queue to finish
sleep 10m

# the droplet is no longer needed, droplet makes
# a DELETE request on itself.
# curl --user $JM_USER:$JM_PASS -X DELETE $JOB_MANAGER/droplets/$DROPLET_UID
