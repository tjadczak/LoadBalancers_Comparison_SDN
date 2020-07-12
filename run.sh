#!/bin/bash
for x in {1..30}
do
  date
  echo start $x
  /home/mininet/LoadBalancers_Comparison_SDN/sflow-rt/start.sh > /dev/null 2>&1 &
  sflow_PID=$!
  sleep 2
  ryu-manager /home/mininet/LoadBalancers_Comparison_SDN/MainLoadBalancer.py --config-file /home/mininet/LoadBalancers_Comparison_SDN/params_false_3_random.conf > /dev/null 2>&1 &
  ryu_PID=$!
  sleep 2
  /home/mininet/LoadBalancers_Comparison_SDN/topology.py false 3 random $x > /dev/null 2>&1 &
  mininet_PID=$!
  sleep 215
  kill $minined_PID $ryu_PID $sflow_PID
done
