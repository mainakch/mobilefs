#!/usr/bin/env python2
'''
network_client.py - Sends remote requests, receives response and returns response
'''
#TODO: add automatic timeout
#TODO: add user control

from constants import *

log = logging.getLogger('network_client')
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(ch)

class Networkclient():
    def __init__(self, server_address, port):

        self.window = WINDOW #number of packets in flight
        self.lastsent = 0 #timestamp of last sent packet
        self.lastreceived = 0 #timestamp of last received packet

        self.unacknowledged_packets = {} #this stores the keys of packets in flight and timestamp when sent
        
        self.network_server_address = (server_address, port)
        self.client_address = LOCAL_UNIX_SOCKET

        #list of sockets
        self.unix_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.network_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        #initialize the sockets
        self.unix_server.bind(LOCAL_UNIX_SOCKET)
        self.unix_server.listen(1)

        self.inputs = [self.unix_server, self.network_server]

        self.outputs = [self.network_server]

        #queues

        self.query_response_queue = {} #for storing responses to quick queries
        #key = taskid, value = request
        self.transmit_queue = {}
        #key = original_taskid, value = response
        self.receive_queue = {}
        #key = (priority, taskid, original_taskid, chunknum, chunktotalnum, timestamp when added to queue), value = chunkof request
        self.chunk_queue = {}
        #key = (taskid, original_taskid, chunknum, chunktotalnum, timestamp when received), value=chunkofresponse
        self.receive_chunk_queue = {}
        #(received taskid, timestamp)
        self.completed_tasks = {}
        #timestamp of last transmission
        self.timestamp_transmission = 0

        #mapping from socket object to taskid
        self.sock_to_taskid = {}
        self.taskid_to_sock = {}
        self.sock_to_timestamp = {}
        self.order_of_keys_in_chunk_queue = []
        self.taskid = randint(0, 1002039) #not randomizing can lead to same taskid in case of client failure

    def split_task(self, taskid, taskstring):
        #this splits up the taskstring into a list of chunks
        startpt = range(0, len(taskstring), CHUNK_SIZE)
        chunks = [taskstring[pt:pt + CHUNK_SIZE] for pt in startpt[:-1]]
        chunks.append(taskstring[startpt[-1]:len(taskstring)])
        #smaller the task higher the priority
        ids = [(len(taskstring), taskid, -1, ctr, len(chunks), time.time()) for ctr in range(len(chunks))]
        return (ids, chunks)

    def remove_priority_timestamp_info_from_key(self, key):
        return (key[1], key[2], key[3], key[4])

    def augment_timestamp_info_key(self, key):
        return (key[0], key[1], key[2], key[3], time.time())

    def add_filesystem_request_to_transmit_queue(self, message, s):
        log.debug('adding request to transmit queue')
        self.taskid += 1
        #add message to the chunk_queue
        (keys, chunks) = self.split_task(self.taskid, message)
        #add keys to order_of_keys_in_chunk_queue
        self.order_of_keys_in_chunk_queue.extend(keys)
        #sort by priority
        self.order_of_keys_in_chunk_queue.sort(key = lambda x: x[0])
        #add entries to chunk_queue
        for (key, val) in zip(keys, chunks):
            self.chunk_queue[key] = val
        #add association between sock and taskid
        self.sock_to_taskid[s] = self.taskid
        self.taskid_to_sock[self.taskid] = s
        #remove from readables
        self.inputs.remove(s)
        #add to writables
        self.outputs.append(s)

        return s

    def receive_filesystem_request(self, s):
        log.debug('receive filesystem req')
        self.sock_to_timestamp[s] = time.time()
        data = recvall(s, 10)
        if data:
            msg = recvall(s, int(data))
            return msg

    def handle_remote_filesystem_response(self, s):
        log.debug('Received data from network server')
        data, self.network_server_address = s.recvfrom(DATAGRAM_SIZE)
        obj = pickle.loads(data)
        self.lastreceived = time.time()
        
        if obj[2] == 'ack':
            #find out key info
            candidate_list = [ctr for ctr in self.order_of_keys_in_chunk_queue if ctr[1] == obj[1][0] and ctr[3] == obj[1][2]]
            #remove from chunk_queue
            if len(candidate_list)>0:
                key = candidate_list[0]
                if key in self.unacknowledged_packets: del self.unacknowledged_packets[key]
                self.order_of_keys_in_chunk_queue.remove(key)
                del self.chunk_queue[key]

        if obj[2] == 'pac':# and obj[0][1] not in self.completed_tasks:
            #add to receive chunk queue queue
            log.debug('Received packet %s ' % repr(obj[0]))
            
            key = self.augment_timestamp_info_key(obj[0])
            val = obj[1]
            #add packet to receive chunk if not in completed task
            if obj[0][1] not in self.completed_tasks:
                self.receive_chunk_queue[key] = val
            #send ack
            s.sendto(pickle.dumps([0, obj[0], 'ack']), self.network_server_address)
            #check if all packets have been received for the same original_task_id
            #there's a more efficient way to do this
            list_of_recv_chunks = [ctr for ctr in self.receive_chunk_queue.keys() if ctr[1] == key[1]]
            if len(list_of_recv_chunks) == key[3]:
                list_of_recv_chunks.sort(key = lambda x: x[2])
                #all chunks have been received
                #transfer to receive_queue
                self.receive_queue[key[1]] = ''.join([self.receive_chunk_queue.pop(ctr) for ctr in list_of_recv_chunks])
                #mark timestamp in completed queue
                self.completed_tasks[key[1]] = time.time()

    def send_packets_to_remote_filesystem(self, s):
        #if possible send packets
        if len(self.order_of_keys_in_chunk_queue)>0:
            list_of_keys_with_timeout = [ctr for ctr in self.unacknowledged_packets.keys() if self.unacknowledged_packets[ctr]<time.time()-RETRANSMISSION_TIMEOUT]
            if len(list_of_keys_with_timeout)>0:
                log.debug('retransmission timeout event')
                #assume packet is lost
                for key in list_of_keys_with_timeout:
                    if key in self.unacknowledged_packets: del self.unacknowledged_packets[key]

            if len(self.unacknowledged_packets.keys())<self.window:
                log.debug('send packets to remote filesystem')
                numkeys = max(self.window - len(self.unacknowledged_packets.keys()), 0)
                #find out keys which are not in transit
                keys = []
                ctr = 0
                while len(keys)<numkeys and ctr < len(self.order_of_keys_in_chunk_queue):
                    if self.order_of_keys_in_chunk_queue[ctr] not in self.unacknowledged_packets:
                        keys.append(self.order_of_keys_in_chunk_queue[ctr])
                    ctr += 1

                for key in keys:
                    self.unacknowledged_packets[key] = time.time()
                    self.lastsent = time.time()
                    s.sendto(pickle.dumps([self.remove_priority_timestamp_info_from_key(key), self.chunk_queue[key], 'pac']), self.network_server_address)
                

    def send_response_to_local_filesystem(self, s):
        #TODO: add code to handle network error
        status = 1 #not completed
        try:
            if self.sock_to_timestamp[s] < time.time() - FILESYSTEM_TIMEOUT:
                #pass
                pass

            if s in self.query_response_queue:
                log.debug('sending query response')
                msg = self.query_response_queue.pop(s)
                log.debug('Sending query response of length %d to query' % len(msg))
                s.sendall(str(len(msg)).zfill(10))
                s.sendall(msg)
                self.outputs.remove(s)
                status = 0

            if s not in self.sock_to_taskid:
                return status

            if self.sock_to_taskid[s] in self.receive_queue:
                key = self.sock_to_taskid.pop(s)
                msg = self.receive_queue.pop(key)
                
                log.debug('Sending response of length %d to filesystem' % len(msg))
                s.sendall(str(len(msg)).zfill(10))
                s.sendall(msg)
                #sendmsg(s, str(len(msg)).zfill(10))
                #sendmsg(s, msg)

                #cleanup
                del self.taskid_to_sock[key]
                self.outputs.remove(s)
                status = 0
                #close this after writing is done
                #s.close()
                                 
        except Exception as exc:
            log.debug(repr(exc))
        finally:
            #s.close()
            pass
        return status

    def send_state(self):
        #function to compute string 
        return 'Not implemented' 
        
    def handle_special_request(self, msg, s):
        status = 1
        try:
            log.debug('Received %s' % msg)
            response = "default response"
            if msg == "chunks":
                #construct task list
                list_of_tasks = list(set([ctr[1] for ctr in self.order_of_keys_in_chunk_queue]))
                #count the number of outstanding chunks
                taskstring = ['Transmit:\n']
                for task in list_of_tasks:
                    a1 = [ctr for ctr in self.order_of_keys_in_chunk_queue if ctr[1]==task]
                    taskstring.append(str(task) + ' : ' + str(len(a1)) + ' left out of ' + str(a1[0][4]) + '\n')

                taskstring.append(repr(self.order_of_keys_in_chunk_queue))
                response = ''.join(taskstring)
                
                status = 0
                self.query_response_queue[s] = response
            # if len(msg) < 4:
            #     status = 0
            
        except:
            pass
        if status==0:
            #this is a special request, so takes care of transferring from input queue to
            #output queue
            log.debug('adding to output queue')
            self.inputs.remove(s)
            self.outputs.append(s)
        return status
          
    def main_loop(self):
        while self.inputs:
            try:
                readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)

                for s in readable:
                    if s is self.unix_server:
                        log.debug('Accepting filesystem connection')
                        connection, _ = s.accept()
                        connection.setblocking(1)
                        self.inputs.append(connection)
                        log.debug('Accepted filesystem connection')
                        log.debug('number of connections %d' % len(self.inputs))
                            
                    if s is not self.unix_server and s.family == socket.AF_UNIX:
                        log.debug('Listen to filesystem connection')
                        #s is a client connection from a local process
                        #read length of tcp message
                        message = self.receive_filesystem_request(s)
                        if self.handle_special_request(message, s) == 1: #this returns 1 if message is special
                            self.add_filesystem_request_to_transmit_queue(message, s)
                            
                    if s.family == socket.AF_INET:
                        log.debug('Receiving information from remote filesystem')
                        #s is a network client
                        self.handle_remote_filesystem_response(s)

                for s in writable:
                    if s is self.network_server:
                        self.send_packets_to_remote_filesystem(s)

                    if s is not self.unix_server and s.family == socket.AF_UNIX:
                        #log.debug('Inside output queue')
                        if self.send_response_to_local_filesystem(s)==0:
                            #close socket if response successfully written
                            log.debug(self.send_state())
                            s.close()

                for s in exceptional:
                    self.inputs.remove(s)
                    if s in self.outputs:
                        self.outputs.remove(s)
                #s.close()
            except Exception as exc:
                log.debug(self.inputs)
                log.debug(exc)
                log.debug('Error')

if __name__=='__main__':
    if len(sys.argv)<3:
        sys.stderr.write('Usage: ./network_client.py <hostname> <port>')
        sys.exit(1)
    
    try:
        if os.path.exists(LOCAL_UNIX_SOCKET): os.remove(LOCAL_UNIX_SOCKET)
        os.remove(LOCAL_UNIX_SOCKET_FOR_QUERY)
    except OSError:
        pass
    network_client = Networkclient(sys.argv[1], int(sys.argv[2]))
    network_client.main_loop()                
