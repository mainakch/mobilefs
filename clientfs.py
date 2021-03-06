#!/usr/bin/env python2
'''
clientfs.py - Example file system for python-llfuse
'''

import llfuse
from argparse import ArgumentParser
import stat
from llfuse import FUSEError
from constants import *

log = logging.getLogger('clientfs')
log.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log.addHandler(ch)

fse = sys.getfilesystemencoding()

def bytes2str(s):
    return s.decode(fse, 'surrogateescape')

def str2bytes(s):
    return s.encode(fse, 'surrogateescape')

class Operations(llfuse.Operations):
    
    def __init__(self, root, mountpoint):      
        super(Operations, self).__init__()
        self.root = bytes2str(root)
        self.mountpoint = mountpoint
        self.inode_path_map = dict() #these are maintained at the client 
        self.path_inode_map = dict() 
        self.root_lookup()
        self.server_address = LOCAL_UNIX_SOCKET
        self.listdir_buffer = {}
        self.listdir_last_access = {}
                    
    def _full_path(self, partial):
        """This function expands to the full path on the remote end."""
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def root_lookup(self):
        """This function updates the inode <-> path dicts with the root inode."""
        self.inode_path_map[1] = self.root
        self.path_inode_map[self.root] = 1
    def send_command_and_receive_response(self, command):
        """This function sends command to the network and returns response. If response
        is an error it raises an error. command is a tuple the first element of which
        is a string description of the command and the second to last elements are
         arguments to the command."""

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_address = self.server_address
        sock.connect(server_address)
        sock.setblocking(1)

        try:
            msg = pickle.dumps(command)
            sock.sendall(str(len(msg)).zfill(10))
            sock.sendall(msg)

            #sendmsg(sock, str(len(msg)).zfill(10))
            #sendmsg(sock, msg)

            length = recvall(sock, 10)
            #length = sock.recv(10)
            #log.debug(str(length))
            data = recvall(sock, int(length))
            try:
                response = pickle.loads(data)
            except:
                raise FUSEError(errno.EAGAIN)

            #log.debug(len(pickle.dumps(response)))
            if response[0] == "err":
                raise FUSEError(response[1])
            #raise FUSEError(errno.EMSGSIZE)

        finally:
            sock.close()
            pass
        return response[1]

        
            
    def lookup(self, inode_p, name):
        """Lookup the name file in inode_p and update inode <-> path dicts"""
        log.debug('lookup %s' % repr((inode_p, name)))
        name = bytes2str(name)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)

        stat = self.send_command_and_receive_response(("lstat", path))
        
        if name != b'.' and name != b'..':
            self.inode_path_map[stat.st_ino] = path
            self.path_inode_map[path] = stat.st_ino
        
        log.debug('lookup: ' + repr(self.inode_path_map))
        return self.getattr(stat.st_ino)

    def getattr(self, inode):
        """Get attributes for the inode"""
        log.debug('getattr %s' % repr(inode))
        path = self.inode_path_map[inode]

        stat = self.send_command_and_receive_response(("lstat", path))
        entry = Entryattributes(stat)
        
        return entry

    def readlink(self, inode):
        log.debug('readlink %s' % repr(inode))
        path = self.inode_path_map[inode]
        target = self.send_command_and_receive_response(("readlink", path))
        return str2bytes(target)
            
    def opendir(self, inode):
        log.debug('opendir %s' % repr(inode))
        return inode

    def readdir(self, inode, offset=0):
        log.debug('readdir %s' % repr(inode))
        path = self.inode_path_map[inode]
               
        if offset == 0 and ((path not in self.listdir_buffer) or (self.listdir_last_access[path] + LISTDIR_TIMEOUT<time.time())):
            #if offset == 0 and path not in self.listdir_buffer:
            self.listdir_buffer[path] = self.send_command_and_receive_response(("listdir", path))
            self.listdir_last_access[path] = time.time()
            
            
        #log.debug('readdir %s' % repr(list_of_entries))
        log.debug('readdir offset %d' % offset)

        if offset>0: return []
        # try:
        #     name = self.listdir_buffer[path][offset]
        # except:
        #     #if path in self.listdir_buffer: del self.listdir_buffer[path]
        #     return []

        final_response = []
        ctr = 0
        for entry in self.listdir_buffer[path]:
            nextctr = ctr+1
            if nextctr == len(self.listdir_buffer[path]):
                final_response.append((str2bytes(entry[0]), entry[1], nextctr))
            else:
                final_response.append((str2bytes(entry[0]), entry[1], nextctr))
            self.inode_path_map[entry[1].st_ino] = os.path.join(path, entry[0])
            self.path_inode_map[os.path.join(path, entry[0])] = entry[1].st_ino
            ctr += 1


            
        return final_response
    
    def unlink(self, inode_p, name):
        log.debug('unlink %s' % repr((inode_p, name)))
        name = bytes2str(name)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)
        self.send_command_and_receive_response(("unlink", path))
        
        # try:
        #     os.unlink(path)
        # except OSError as exc:
        #     raise FUSEError(exc.errno)

    def rmdir(self, inode_p, name):
        log.debug('rmdir %s' % repr((inode_p, name)))
        name = bytes2str(name)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)
        self.send_command_and_receive_response(("rmdir", path))
        # try:
        #     os.rmdir(path)
        # except OSError as exc:
        #     raise FUSEError(exc.errno)

    def symlink(self, inode_p, name, target, ctx):
        log.debug('symlink %s' % repr((inode_p, name, target)))
        name = bytes2str(name)
        target = bytes2str(target)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)
        self.send_command_and_receive_response(("symlink", target, path))
        
        # try:
        #     os.symlink(target, path)
        # except OSError as exc:
        #     raise FUSEError(exc.errno)
        
        stat = self.send_command_and_receive_response(("lstat", path))
        self.path_inode_map[path] = stat.st_ino
        self.inode_path_map[stat.st_ino] = path
        
        return self.getattr(stat.st_ino)
        
    def rename(self, inode_p_old, name_old, inode_p_new, name_new):     
        log.debug('rename')
        name_old = bytes2str(name_old)
        name_new = bytes2str(name_new)
        parent_old = self.inode_path_map[inode_p_old]
        parent_new = self.inode_path_map[inode_p_new]
        path_old = os.path.join(parent_old, name_old)
        path_new = os.path.join(parent_new, name_new)
        self.send_command_and_receive_response(("rename", path_old, path_new))
        
        # try:
        #     os.rename(path_old, path_new)
        # except OSError as exc:
        #     raise FUSEError(exc.errno)
        
        inode = self.path_inode_map[path_old]
        del self.path_inode_map[path_old]
        self.inode_path_map[inode] = path_new
        
    def link(self, inode, new_inode_p, new_name):
        log.debug('link')
        new_name = bytes2str(new_name)
        parent = self.inode_path_map[new_inode_p]
        path = os.path.join(parent, new_name)

        self.send_command_and_receive_response(("link", self.inode_path_map[inode], path))
        
        # try:
        #     os.link(self.inode_path_map[inode], path)
        # except OSError as exc:
        #     raise FUSEError(exc.errno)

        self.path_inode_map[path] = inode
        self.inode_path_map[inode] = path
        
        return self.getattr(inode)

    def setattr(self, inode, attr):
        '''Change attributes of *inode*
        
        *attr* is an `EntryAttributes` instance with the new
        attributes. Only the attributes `~EntryAttributes.st_size`,
        `~EntryAttributes.st_mode`, `~EntryAttributes.st_uid`,
        `~EntryAttributes.st_gid`, `~EntryAttributes.st_atime` and
        `~EntryAttributes.st_mtime` are relevant. Unchanged attributes
        will have a value `None`.
        
        The method should return a new `EntryAttributes` instance
        with the updated attributes (i.e., all attributes except for
        `~EntryAttributes.entry_timeout` should be set).
        '''

        log.debug('setattr %s' % repr((inode, attr)))
        log.debug(repr((attr.st_mode, self.inode_path_map[inode])))

        self.send_command_and_receive_response(("setattr", self.inode_path_map[inode], Entryattributes(attr)))

        return self.getattr(inode)

    def mknod(self, inode_p, name, mode, rdev, ctx):
        log.debug('mknod %s' % name)
        name = bytes2str(name)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)

        self.send_command_and_receive_response(("mknod", path, mode, rdev))
        #os.mknod(path, mode, rdev)
        return self.lookup(inode_p, name)

    def mkdir(self, inode_p, name, mode, ctx):
        log.debug('mkdir')
        name = bytes2str(name)
        parent = self.inode_path_map[inode_p]
        path = os.path.join(parent, name)

        self.send_command_and_receive_response(("mkdir", path, mode))
        #os.mkdir(path, mode)
        return self.lookup(inode_p, name)

    def statfs(self):
        log.debug('statfs')
        stat_ = llfuse.StatvfsData()
        stv = self.send_command_and_receive_response(("statvfs", self.root))
        #stv = os.statvfs(self.root)

        stat_.f_bsize = stv.f_bsize
        stat_.f_frsize = stv.f_frsize
        stat_.f_blocks = stv.f_blocks
        stat_.f_bfree = stv.f_bfree
        stat_.f_bavail = stv.f_bavail

        stat_.f_files = stv.f_files
        stat_.f_ffree = stv.f_ffree
        stat_.f_favail = stv.f_favail

        return stat_

    def open(self, inode, flags):
        log.debug('open %s, %s' % (inode, repr(flags)))
        # Yeah, unused arguments
        #pylint: disable=W0613
        #self.inode_open_count[inode] += 1
        return self.send_command_and_receive_response(("open", self.inode_path_map[inode], flags))
        #return os.open(self.inode_path_map[inode], flags)
        
    def access(self, inode, mode, ctx):
        log.debug('access')
        #pylint: disable=R0201,W0613
        return self.send_command_and_receive_response(("access", self.inode_path_map[inode], mode))

    def read(self, fh, offset, length):
        log.debug('read')

        return b64decode(self.send_command_and_receive_response(("lseekread", fh, offset, length)))
        #os.lseek(fh, offset, 0)
        #return os.read(fh, length)
                
    def write(self, fh, offset, buf):
        log.debug('write %s' % buf)

        return self.send_command_and_receive_response(("lseekwrite", fh, offset, b64encode(buf)))
   
    def release(self, fh):
        log.debug('release')
        self.send_command_and_receive_response(("close", fh))
        #os.close(fh)
        #raise FUSEError(errno.ENOSYS)
        #self.inode_open_count[fh] -= 1

        #if self.inode_open_count[fh] == 0:
        #    del self.inode_open_count[fh]
        #    if self.getattr(fh).st_nlink == 0:
        #        pass

def init_logging(debug=False):
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s: '
                                  '[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)            
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)    
    root_logger.addHandler(handler)    
        
        
def parse_args(args):
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('root', type=str,
                        help='Directory tree to mirror')
    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system')

    parser.add_argument('--single', type=bool, default=False,
                        help='Run single threaded')
    
    parser.add_argument('--debug', type=bool, default=False,
                        help='Enable debugging output')

    return parser.parse_args(args)
        
          
def main():    
    options = parse_args(sys.argv[1:])
    init_logging(options.debug)
    operations = Operations(options.root, options.mountpoint)
    
    log.debug('Mounting...')
    llfuse.init(operations, options.mountpoint, 
                [  b'fsname=clientfs', b"nonempty" ])
    
    try:
        log.debug('Entering main loop..')
        llfuse.main(options.single)
    except:
        llfuse.close(unmount=False)
        raise

    log.debug('Unmounting..')
    llfuse.close()
    

if __name__ == '__main__':
    main()
