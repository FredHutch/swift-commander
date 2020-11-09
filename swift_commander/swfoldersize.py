#! /usr/bin/env python3

# Script for comparing the size of a posix folder with the size of a swift pseudo folder
#
# swfoldersize.py dirkpetersen / Jan 2015 
#

import swiftclient, sys, os, argparse, math, functools

class KeyboardInterruptError(Exception): pass

SizeError=False

def main():

    if args.container:
        c=create_sw_conn()
        sbytes=0
        print ("    checking swift folder %s/%s ..." % (args.container,args.prefix))
        try:
            headers, objects = c.get_container(args.container,prefix=args.prefix,full_listing=True)            
            for obj in objects:
                sbytes+=obj['bytes']
                #print(obj['name'],obj['bytes'])
            if sbytes > 0:
                print ("    %s bytes (%s) in %s/%s (swift)" % (intwithcommas(sbytes),convertByteSize(sbytes),args.container,args.prefix))
            else:
                print ("    ...Error: it seems swift folder %s/%s does not contain any data." % (args.container,args.prefix))
        except:
            print ("    ...Error: it seems swift folder %s/%s does not exist" % (args.container,args.prefix))

        if args.posixfolder:
            pbytes, exbytes, dupbytes = posixfolderprint(args.posixfolder)

            if sbytes == pbytes:
                print("OK! The size of %s and %s/%s is identical!" % \
                    (args.posixfolder,args.container,args.prefix))
                if SizeError:
                    print("********** WARNING !! ********** The size of at least one " + \
                        "file or folder could not be determined. Please check permissions, " + \
                        "the size comparison may not be valid")

            else:
                print("********** WARNING !! ********** The size of  %s and %s/%s is NOT identical!" % \
                    (args.posixfolder,args.container,args.prefix))

    else: 
        if args.posixfolder:
            pbytes, exbytes, dupbytes = posixfolderprint(args.posixfolder)
            realbytes=pbytes-(exbytes+dupbytes)

        if args.posixfolder2:
            pbytes2, exbytes2, dupbytes2 = posixfolderprint(args.posixfolder2)
            realbytes2=pbytes2-(exbytes2+dupbytes2)

        if args.posixfolder and args.posixfolder2:
            if pbytes2 == pbytes or realbytes == realbytes2:
                print("OK! The size of %s and %s is identical!" % \
                    (args.posixfolder,args.posixfolder2))
            else:
                print("********** WARNING !! ********** The size of  %s and %s is NOT identical!" % \
                    (args.posixfolder,args.posixfolder2))

def posixfolderprint(path):
    print ("    checking posix folder %s (following symlinks)..." % (path))
    pbytes, exbytes, dupbytes = getFolderSize(os.path.expanduser(path))
    print ("    %s bytes (%s) in %s" % (intwithcommas(pbytes),convertByteSize(pbytes),path))
    if exbytes > 0: print("    ...including %s bytes (%s) for links to outside of %s" % (intwithcommas(exbytes),convertByteSize(exbytes),path))
    if dupbytes > 0: print("    ...including %s bytes (%s) for duplicate inodes." % (intwithcommas(dupbytes),convertByteSize(dupbytes)))
    return pbytes, exbytes, dupbytes

def getFolderSize(path, externalLinks=True):  # skips duplicate inodes
    global SizeError
    total_size = 0
    external_size = 0
    duplicate_inodes_size = 0

    seen = set()

    for dirpath, dirnames, filenames in mywalk(path):

        #if dirpath != path:   # ignore sub directories
        #    break

        for f in filenames:
            fp = os.path.join(dirpath, f)

            if isExternalLink(path,fp):
                external_size += stat.st_size
                if not externalLinks:
                    if args.debug:
                        print('    ...ignoring external link %s to %s' % (fp, os.readlink(fp)))
                    continue
                else:
                    if args.debug:
                        print('    ...including external link %s to %s' % (fp, os.readlink(fp)))

            try:
                stat = os.stat(fp)
            except OSError as err:
                sys.stderr.write(str(err))
                sys.stderr.write('\n')
                SizeError=True
                continue

            if stat.st_ino in seen:
                if args.debug:
                    print('    ...Duplicate inode %s for %s' % (stat.st_ino, fp))
                duplicate_inodes_size += stat.st_size
                #continue

            seen.add(stat.st_ino)
            #print(stat.st_size,fp)

            total_size += stat.st_size

    return total_size, external_size, duplicate_inodes_size  # size in bytes

def isExternalLink(root,path):
    if os.path.islink(path):
        real=os.readlink(path)
        if not real.startswith(root) and real.startswith('/'):
            return True
    return False

def mywalk(top, skipdirs=['.snapshot',]):
    """ returns subset of os.walk  """
    for root, dirs, files in os.walk(top,topdown=True,onerror=walkerr):
        for skipdir in skipdirs:
            if skipdir in dirs:
                dirs.remove(skipdir)  # don't visit this directory 
        yield root, dirs, files

def walkerr(oserr):
    sys.stderr.write(str(oserr))
    sys.stderr.write('\n')
    return 0

def getFolderSize2(path):
    # this is a legacy function that does not follow symlinks
    global SizeError
    if "/.snapshot/" in path:
        return 0
    if os.path.islink(path):
        return 0
    prepend = functools.partial(os.path.join, path)
    try:
        return sum([(os.path.getsize(f) if not os.path.islink(f) and os.path.isfile(f) else getFolderSize2(f)) for f in map(prepend, os.listdir(path))])
    except:
        print("    ...Error getting size of %s" % path)
        SizeError=True
        return 0


def create_sw_conn():
    if args.authtoken and args.storageurl:
        return swiftclient.Connection(preauthtoken=args.authtoken, preauthurl=args.storageurl)
    else:
        authtoken=os.environ.get("OS_AUTH_TOKEN")
        storageurl=os.environ.get("OS_STORAGE_URL")
        if authtoken and storageurl:
            return swiftclient.Connection(preauthtoken=authtoken, preauthurl=storageurl)
        else:
            swift_auth=os.environ.get("ST_AUTH")
            swift_user=os.environ.get("ST_USER")
            swift_key=os.environ.get("ST_KEY")
            if swift_auth and swift_user and swift_key:
                return swiftclient.Connection(authurl=swift_auth,user=swift_user,key=swift_key)

def convertByteSize(size):
   if size == 0:
   	return '0 B'
   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size,1024)))
   p = math.pow(1024,i)
   s = size/p
   if (s > 0):
       return '%0.3f %s' % (s,size_name[i])
   else:
       return '0 B'

def intwithcommas(x):
    result=''
    while x >= 1000:
        x,r = divmod(x, 1000)
        result = ",%03d%s" % (r, result)
    return "%d%s" % (x, result)

def parse_arguments():
    """
    Gather command-line arguments.
    """
    parser = argparse.ArgumentParser(prog='swfoldersize.py',
        description='compare the size of a posix folder with the size ' + \
        'of a swift (pseudo) folder after a data migration ' + \
        '()')
    parser.add_argument( '--debug', '-d', dest='debug',
        action='store_true',
        help='show addional information for debug',
        default=False )   
    parser.add_argument( '--info', '-i', dest='debug',
        action='store_true',
        help='show addional information for debug',
        default=False )  
    parser.add_argument( '--posixfolder', '-p', dest='posixfolder',
        action='store',
        help='a folder on a posix file system ',
        default='' )        
    parser.add_argument( '--posixfolder2', '-2', dest='posixfolder2',
        action='store',
        help='a 2nd folder on a posix file system ',
        default='' )        
    parser.add_argument( '--container', '-c', dest='container',
        action='store',
        help='a container in the swift object store',
        default='' )
    parser.add_argument( '--prefix', '-x', dest='prefix',
        action='store',
        help='a swift object prefix',
        default=None)
    parser.add_argument( '--proc', '-m', dest='maxproc',
        action='store',
        type=int,
        help='maximum number of processes to run (not yet implemented)',
        default=0 )
    parser.add_argument( '--authtoken', '-a', dest='authtoken',
        action='store',
        help='a swift authentication token (required when storage-url is used)',
        default=None)
    parser.add_argument( '--storage-url', '-s', dest='storageurl',
        action='store',
        help='a swift storage url (required when authtoken is used)',
        default=None)

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = parse_arguments()
    sys.exit(main())

