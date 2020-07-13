#!/bin/bash
for x in `ls | grep params`
do
  for i in {1..40}
  do
    date
    echo start $x $i
    /home/mininet/LoadBalancers_Comparison_SDN/sflow-rt/start.sh > /dev/null 2>&1 &
    sflow_PID=$!
    sleep 2
    ryu-manager /home/mininet/LoadBalancers_Comparison_SDN/MainLoadBalancer.py --config-file /home/mininet/LoadBalancers_Comparison_SDN/$x > /dev/null 2>&1 &
    ryu_PID=$!
    sleep 2
    /home/mininet/LoadBalancers_Comparison_SDN/topology.py $x $i > /dev/null 2>&1 &
    mininet_PID=$!
    sleep 30
    kill $minined_PID $ryu_PID $sflow_PID
    rm *csv wget*
  done
done
