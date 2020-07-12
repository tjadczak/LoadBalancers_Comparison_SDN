#!/bin/bash
for x in `ls | grep params`
do
  for i in 1
  do
    date
    echo start $x $i
    /home/mininet/LoadBalancers_Comparison_SDN/sflow-rt/start.sh >> sflow.log 2>&1 &
    sflow_PID=$!
    sleep 2
    ryu-manager /home/mininet/LoadBalancers_Comparison_SDN/MainLoadBalancer.py --config-file /home/mininet/LoadBalancers_Comparison_SDN/$x >> ryu.log 2>&1 &
    ryu_PID=$!
    sleep 2
    /home/mininet/LoadBalancers_Comparison_SDN/topology.py $x >> mininet.log 2>&1 &
    mininet_PID=$!
    sleep 215
    kill $minined_PID $ryu_PID $sflow_PID
  done
done
