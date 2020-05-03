#!/usr/bin/env python
import requests
import json

rt = 'http://127.0.0.1:8008'

flowUdp = {'keys':'link:inputifindex,ipsource,ipdestination,ipprotocol,udpsourceport,udpdestinationport','value':'bytes'}
# flowTcp = {'keys':'link:inputifindex,ipsource,ipdestination,ipprotocol,tcpsourceport,tcpdestinationport','value':'bytes'}
requests.put(rt+'/flow/pair/json',data=json.dumps(flowUdp))
# requests.put(rt+'/flow/pair/json',data=json.dumps(flowTcp))

threshold = {'metric':'pair','value':1,'byFlow':True,'timeout':1}
requests.put(rt+'/threshold/elephant/json',data=json.dumps(threshold))

eventurl = rt+'/events/json?thresholdID=elephant&maxEvents=10&timeout=60'
eventID = -1
while 1 == 1:
  r = requests.get(eventurl + "&eventID=" + str(eventID))
  if r.status_code != 200: break
  events = r.json()
  if len(events) == 0:
      print("Length of events = 0, continuing")
      continue

  eventID = events[0]["eventID"]
  events.reverse()
  for e in events:
    print(e['flowKey'])
