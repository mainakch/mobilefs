import socket
import json
import sys
import select
import time
from random import randint

#socket address
network_server_address = ('corn29.stanford.edu', 60002)
client_address = '/tmp/socket_c_and_nc'

#list of sockets
#socks = [socket.socket(socket.AF_INET, socket.SOCK_DGRAM), socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)]
unix_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
network_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#initialize the sockets

#listen to client processes
#socks[1].bind(client_address)
#socks[1].listen(1)
unix_server.bind(client_address)
unix_server.listen(1)

#inputs = [socks[0], socks[1]]
inputs = [unix_server, network_server]

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
sock_to_taskid = {}
taskid_to_sock = {}
order_of_keys_in_chunk_queue = []
taskid = randint(0, 1002039)
packets_in_flight = 0

def split_task(taskid, taskstring):
    #this splits up the taskstring into a list of chunks
    startpt = range(0, len(taskstring), 100)
    chunks = [taskstring[pt:pt + 100] for pt in startpt[:-1]]
    chunks.append(taskstring[startpt[-1]:len(taskstring)])
    #smaller the task higher the priority
    ids = [(len(taskstring), taskid, -1, ctr, len(chunks), time.time()) for ctr in range(len(chunks))]
    return (ids, chunks)

def remove_priority_timestamp_info_from_key(key):
    return (key[1], key[2], key[3], key[4])

def augment_timestamp_info_key(key):
    return (key[0], key[1], key[2], key[3], time.time())
    
while inputs:
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
    for s in readable:
        if s is unix_server:
            print 'Inside 1'
            connection, client_address = unix_server.accept()
            connection.setblocking(0)
            inputs.append(connection)
        if s is not unix_server and s.family == socket.AF_UNIX:
            print 'Inside 2'
            #s is a client connection from a local process
            #read length of tcp message
            data = s.recv(10)
            if data:
                length = int(data)
                message = s.recv(length) #maybe change this to read a bounded number of bits at a time

                taskid += 1
                #add message to the chunk_queue
                (keys, chunks) = split_task(taskid, message)
                #add keys to order_of_keys_in_chunk_queue
                order_of_keys_in_chunk_queue.extend(keys)
                #sort by priority
                order_of_keys_in_chunk_queue.sort(key = lambda x: x[0])
                #add entries to chunk_queue
                for (key, val) in zip(keys, chunks):
                    chunk_queue[key] = val
                #add association between sock and taskid
                sock_to_taskid[s] = taskid
                taskid_to_sock[taskid] = s
                #remove from input
                inputs.remove(s)
                #add to output
                outputs.append(s)

        if s.family == socket.AF_INET:
            print 'Inside network'
            #s is a network client
            data, network_server_address = s.recvfrom(512)
            obj = json.loads(data)
            if obj[2] == 'ack':
                #find out key info
                print obj
                print order_of_keys_in_chunk_queue
                candidate_list = [ctr for ctr in order_of_keys_in_chunk_queue if ctr[1] == obj[1][0] and ctr[3] == obj[1][2]]
                #remove from chunk_queue
                key = candidate_list[0]
                order_of_keys_in_chunk_queue.remove(key)
                del chunk_queue[key]
                packets_in_flight -= 1
            if obj[2] == 'pac' and obj[0][1] not in completed_tasks:
                #add to receive chunk queue queue
                key = augment_timestamp_info_key(obj[0])
                val = obj[1]
                #add packet to receive chunk
                receive_chunk_queue[key] = val
                #send ack
                s.sendto(json.dumps([0, obj[0], 'ack']), network_server_address)
                #check if all packets have been received for the same original_task_id
                #there's a more efficient way to do this
                list_of_recv_chunks = [ctr for ctr in receive_chunk_queue.keys() if ctr[1] == key[1]]
                if len(list_of_recv_chunks) == key[3]:
                    list_of_recv_chunks.sort(key = lambda x: x[2])
                    #all chunks have been received
                    #transfer to receive_queue
                    receive_queue[key[1]] = ''.join([receive_chunk_queue.pop(ctr) for ctr in list_of_recv_chunks])
                    #mark timestamp in completed queue
                    completed_tasks[key[1]] = time.time()
        
    for s in writable:
        if s is network_server:
            #send the topmost priority packet if number of packets in flight is <1
            if packets_in_flight < 1 and len(order_of_keys_in_chunk_queue)>0:
                key = order_of_keys_in_chunk_queue[0]
                s.sendto(json.dumps([remove_priority_timestamp_info_from_key(key), chunk_queue[key], 'pac']), network_server_address)
                packets_in_flight += 1
        if s is not unix_server and s.family == socket.AF_UNIX:
            if sock_to_taskid[s] in receive_queue:
                print 'Sending'
                print receive_queue[sock_to_taskid[s]]
                s.sendall(str(len(receive_queue[sock_to_taskid[s]])).zfill(10))
                s.sendall(receive_queue[sock_to_taskid[s]])

                #cleanup
                del taskid_to_sock[sock_to_taskid[s]]
                del receive_queue[sock_to_taskid[s]]
                del sock_to_taskid[s]
                outputs.remove(s)
            
    for s in exceptional:
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
