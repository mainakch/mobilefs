#!/usr/bin/env python2
'''
network_server.py - Executes remote requests and send responses back
'''
from constants import *

log = logging.getLogger('network_server')
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(ch)
        
class Networkserver():
    def __init__(self, server_address, port):

        self.window = WINDOW
        self.lastsent = 0
        self.lastreceived = 0
        self.unacknowledged_packets = {} #this stores the keys of packets in flight and timestamp when sent
        self.time_sleep = 0.0000000000000000003
        
        #socket address
        self.public_address = (server_address, port)

        #list of sockets
        self.network_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #initialize the sockets
        try:
            self.network_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.network_server.bind(self.public_address)
            
        except Exception as ex:
            #pass
            log.debug(ex)
    
        self.inputs = [self.network_server]
        self.outputs = [self.network_server]

        #queues
        #key=remote taskid, value = list of chunks received so far
        self.recv_list_of_chunks = {}
        #key = taskid, value = request
        self.transmit_queue = {}
        #key = original_taskid, value = response
        self.receive_queue = {}
        #key = (priority, taskid, original_taskid, chunknum, chunktotalnum, timestamp when added to queue/transmitted), value = chunkof request
        self.chunk_queue = {}
        #key = (taskid, original_taskid, chunknum, chunktotalnum, timestamp when received), value=chunkofresponse
        self.receive_chunk_queue = {}
        #(received taskid, timestamp)
        self.completed_tasks = {}
        #timestamp of last transmission
        self.timestamp_transmission = 0

        #mapping from socket object to taskid
        self.order_of_keys_in_chunk_queue = []
        self.taskid = randint(0, 1002039)
        self.packets_in_flight = 0

    def execute_message(self, taskstring):
        log.debug('inside execute_message: %s' % taskstring)

        args = pickle.loads(taskstring)
        response = None
        try:
            if args[0] == 'chmod':
                os.chmod(args[1], args[2])

            if args[0] == 'setattr':
                pathname = args[1]
                attr = args[2]

                if attr.st_mode is not None:
                    os.chmod(pathname, attr.st_mode)
                if attr.st_size is not None:
                    try:
                        fd = os.open(pathname, os.O_RDWR)
                        os.ftruncate(fd, attr.st_size)
                        os.close(fd)
                    except Exception as exc:
                        log.debug('Error in truncate %s' % repr(exc))
                        pass
                if (attr.st_atime is not None) or (attr.st_mtime is not None):
                    os.utime(pathname, (attr.st_atime, attr.st_mtime))

                if (attr.st_gid is not None) or (attr.st_uid is not None):
                    os.lchown(pathname, attr.st_uid, attr.st_gid)
                    
            if args[0] == 'close':
                os.close(args[1])

            if args[0] == 'link':
                os.link(args[1], args[2])

            if args[0] == 'listdir':
                list_of_dirs = os.listdir(args[1])
                response = []
                for name in list_of_dirs:
                    fullname = os.path.join(args[1], name)
                    if not os.path.islink(fullname):
                        stat = os.lstat(fullname)
                        entry = Entryattributes(stat)
                        response.append((name, entry, fullname))
                
            if args[0] == 'lseekread':
                os.lseek(args[1], args[2], 0)
                response = b64encode(os.read(args[1], args[3]))

            if args[0] == 'lseekwrite':
                os.lseek(args[1], args[2], 0)
                response = os.write(args[1], b64decode(args[3]))

            if args[0] == 'lstat':
                response = os.lstat(args[1])

            if args[0] == 'mkdir':
                os.mkdir(args[1], args[2])

            if args[0] == 'mknod':
                os.mknod(args[1], args[2], args[3])

            if args[0] == 'open':
                response = os.open(args[1], args[2])

            if args[0] == 'readlink':
                response = os.readlink(args[1])

            if args[0] == 'rename':
                response = os.rename(args[1], args[2])

            if args[0] == 'rmdir':
                response = os.rmdir(args[1])

            if args[0] == 'statvfs':
                response = os.statvfs(args[1])

            if args[0] == 'symlink':
                response = os.symlink(args[1], args[2])

            if args[0] == 'unlink':
                response = os.unlink(args[1])

            if args[0] == 'access':
                response = os.access(args[1], args[2])

        except OSError as exc:
            response = exc

        if response is None:
            return pickle.dumps(('non', response))
        if isinstance(response, Exception):
            return pickle.dumps(('err', response.errno))
        else:
            return pickle.dumps(('res', response))

    def handle_remote_request(self, s):
        #log.debug('Received request from network_client')
        try:
            #s is a network client connection
            data, self.network_client_address = s.recvfrom(DATAGRAM_SIZE)
            obj = pickle.loads(data)
            self.lastreceived = time.time()
            if obj[2] == 'hrt':
                log.debug('Heartbeat received')
                log.debug('Client address: %s' % repr(self.network_client_address))
                
            if obj[2] == 'ack':
                log.debug('ack')
                #find out key info
                candidate_list = [ctr for ctr in self.order_of_keys_in_chunk_queue if ctr[1] == obj[1][0] and ctr[3] == obj[1][2]]
                #remove from chunk_queue
                if len(candidate_list)>0:
                    key = candidate_list[0]
                    if key in self.unacknowledged_packets: del self.unacknowledged_packets[key]
                    self.order_of_keys_in_chunk_queue.remove(key)
                    del self.chunk_queue[key]

            if obj[2] == 'pac':# and obj[0][0] not in self.completed_tasks:
                log.debug('pac')
                #add to receive chunk queue queue
                key = self.augment_timestamp_info_key(obj[0])
                val = obj[1]
                #add packet to receive chunk if not in self.completed_tasks
                if obj[0][1] not in self.completed_tasks:
                    if key[0] not in self.recv_list_of_chunks: self.recv_list_of_chunks[key[0]] = []
                    if key[2] not in self.recv_list_of_chunks[key[0]]:
                        self.recv_list_of_chunks[key[0]].append(key[2])
                        self.receive_chunk_queue[key] = val
                #send ack
                s.sendto(pickle.dumps([0, obj[0], 'ack']), self.network_client_address)
                #check if all packets have been received for the same taskid


                if key[0] in self.recv_list_of_chunks and len(self.recv_list_of_chunks[key[0]]) == key[3]:
                    
                    list_of_recv_chunks = [ctr for ctr in self.receive_chunk_queue.keys() if ctr[0] == key[0]]
                    list_of_recv_chunks.sort(key = lambda x: x[2])
                    #all chunks have been received
                    #transfer to receive_queue
                    self.receive_queue[key[0]] = ''.join([self.receive_chunk_queue.pop(ctr) for ctr in list_of_recv_chunks])
                    #mark timestamp in completed queue
                    self.completed_tasks[key[0]] = time.time()
                    #remove list of received chunk indices
                    del self.recv_list_of_chunks[key[0]]

                    #execute action
                    string_response = self.execute_message(self.receive_queue.pop(key[0]))
                    #log.debug(string_response)

                    #now send response
                    self.taskid += 1
                    #add message to the chunk_queue
                    (keys, chunks) = self.split_task(self.taskid, key[0], string_response)
                    #add keys to order_of_keys_in_chunk_queue
                    self.order_of_keys_in_chunk_queue.extend(keys)
                    #sort by priority
                    self.order_of_keys_in_chunk_queue.sort(key = lambda x: x[0])
                    #add entries to chunk_queue
                    for (key, val) in zip(keys, chunks):
                        self.chunk_queue[key] = val
        except Exception as exc:
            log.debug(repr(exc))

    def send_remote_response(self, s):
        if len(self.order_of_keys_in_chunk_queue)>0:
            self.window = next_window(self.window, False)
            list_of_keys_with_timeout = [ctr for ctr in self.unacknowledged_packets.keys() if self.unacknowledged_packets[ctr]<time.time()-RETRANSMISSION_TIMEOUT]
            if len(list_of_keys_with_timeout)>0:
                #assume packet is lost/network is congested
                self.window = next_window(self.window, True)
                for key in list_of_keys_with_timeout:
                    if key in self.unacknowledged_packets: del self.unacknowledged_packets[key]

            if len(self.unacknowledged_packets.keys())<self.window:
                #log.debug('send packets to remote filesystem')
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
                    string_to_be_sent = pickle.dumps([self.remove_priority_timestamp_info_from_key(key), self.chunk_queue[key], 'pac'])
                    log.debug('Length of datagram %d' % len(string_to_be_sent))
                    if len(string_to_be_sent)>DATAGRAM_SIZE: sys.exit(1)
                    s.sendto(string_to_be_sent, self.network_client_address)

    def split_task(self, taskid, original_taskid, taskstring):
        #this splits up the taskstring into a list of chunks
        startpt = range(0, len(taskstring), CHUNK_SIZE)
        chunks = [taskstring[pt:pt + CHUNK_SIZE] for pt in startpt[:-1]]
        chunks.append(taskstring[startpt[-1]:len(taskstring)])
        #smaller the task higher the priority
        ids = [(len(taskstring), taskid, original_taskid, ctr, len(chunks), time.time()) for ctr in range(len(chunks))]
        return (ids, chunks)

    def remove_priority_timestamp_info_from_key(self, key):
        return (key[1], key[2], key[3], key[4])

    def augment_timestamp_info_key(self, key):
        return (key[0], key[1], key[2], key[3], time.time())

    def main_loop(self):
        while self.inputs:
            readable, writable, exceptional = select.select(self.inputs, self.outputs, self.inputs)

            #prevent cpu burn
            if len(self.receive_chunk_queue.keys()) > 0 or len(self.chunk_queue.keys()) > 0:
                self.time_sleep = 0.0000000000000000000000003
            else:
                self.time_sleep = 0.003
                
            for s in readable:
                self.handle_remote_request(s)
            for s in writable:
                self.send_remote_response(s)

            for s in exceptional:
                self.inputs.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
            time.sleep(self.time_sleep)

if __name__=='__main__':
    if len(sys.argv)<3:
        sys.stderr.write('Usage: ./network_server.py <hostname> <port>')
        sys.exit(1)
    network_server = Networkserver(sys.argv[1], int(sys.argv[2]))
    network_server.main_loop()
