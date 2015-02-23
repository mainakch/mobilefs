import socket
import json
import sys
import select
import time

#socket address
public_address = ("corn29.stanford.edu", 60002)

#list of sockets
network_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#initialize the sockets

#listen to client processes
#socks[1].bind(client_address)
#socks[1].listen(1)
try:
    network_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    network_server.bind(public_address)

except Exception as ex:
    print ex
    

#inputs = [socks[0], socks[1]]
inputs = [network_server]

outputs = [network_server]
#outputs = []

#queues

#key = taskid, value = request
transmit_queue = {}
#key = original_taskid, value = response
receive_queue = {}
#key = (priority, taskid, original_taskid, chunknum, chunktotalnum, timestamp when added to queue), value = chunkof request
chunk_queue = {}
#key = (taskid, original_taskid, chunknum, chunktotalnum, timestamp when received), value=chunkofresponse
receive_chunk_queue = {}
#(received taskid, timestamp)
completed_tasks = {}
#timestamp of last transmission
timestamp_transmission = 0

#mapping from socket object to taskid
order_of_keys_in_chunk_queue = []
taskid = 0
packets_in_flight = 0

def execute_message(taskstring):
    args = taskstring.split()
    if args[0] == 'add':
        return str(int(args[1]) + int(args[2]))
    else:
        return ''.join([args[1], args[2]])

def split_task(taskid, original_taskid, taskstring):
    #this splits up the taskstring into a list of chunks
    startpt = range(0, len(taskstring), 100)
    chunks = [taskstring[pt:pt + 100] for pt in startpt[:-1]]
    chunks.append(taskstring[startpt[-1]:len(taskstring)])
    #smaller the task higher the priority
    ids = [(len(taskstring), taskid, original_taskid, ctr, len(chunks), time.time()) for ctr in range(len(chunks))]
    return (ids, chunks)

def remove_priority_timestamp_info_from_key(key):
    return (key[1], key[2], key[3], key[4])

def augment_timestamp_info_key(key):
    return (key[0], key[1], key[2], key[3], time.time())
    
while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    for s in readable:
        #s is a network client connection
        data, network_client_address = s.recvfrom(512)
        obj = json.loads(data)
        if obj[2] == 'ack':
            print 'ack %s' % repr(obj)
            #find out key info
            candidate_list = [ctr for ctr in order_of_keys_in_chunk_queue if ctr[1] == obj[1][0] and ctr[3] == obj[1][2]]
            #remove from chunk_queue
            key = candidate_list[0]
            order_of_keys_in_chunk_queue.remove(key)
            del chunk_queue[key]
            packets_in_flight -= 1
        if obj[2] == 'pac' and obj[0][0] not in completed_tasks:
            print 'pac %s' % repr(obj)
            #add to receive chunk queue queue
            key = augment_timestamp_info_key(obj[0])
            val = obj[1]
            #add packet to receive chunk
            receive_chunk_queue[key] = val
            #send ack
            s.sendto(json.dumps([0, obj[0], 'ack']), network_client_address)
            #check if all packets have been received for the same taskid
            #there's a more efficient way to do this
            list_of_recv_chunks = [ctr for ctr in receive_chunk_queue.keys() if ctr[0] == key[0]]
            if len(list_of_recv_chunks) == key[3]:
                list_of_recv_chunks.sort(key = lambda x: x[2])
                #all chunks have been received
                #transfer to receive_queue
                receive_queue[key[0]] = ''.join([receive_chunk_queue.pop(ctr) for ctr in list_of_recv_chunks])
                #mark timestamp in completed queue
                completed_tasks[key[0]] = time.time()

                #execute action
                string_response = execute_message(receive_queue.pop(key[0]))
                
                #now send response
                taskid += 1
                #add message to the chunk_queue
                (keys, chunks) = split_task(taskid, key[0], string_response)
                #add keys to order_of_keys_in_chunk_queue
                order_of_keys_in_chunk_queue.extend(keys)
                #sort by priority
                order_of_keys_in_chunk_queue.sort(key = lambda x: x[0])
                #add entries to chunk_queue
                for (key, val) in zip(keys, chunks):
                    chunk_queue[key] = val
    
    for s in writable:
        #send the topmost priority packet if number of packets in flight is <1
        if packets_in_flight < 1 and len(order_of_keys_in_chunk_queue)>0:
            key = order_of_keys_in_chunk_queue[0]
            s.sendto(json.dumps([remove_priority_timestamp_info_from_key(key), chunk_queue[key], 'pac']), network_client_address)
            packets_in_flight += 1
            
    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
