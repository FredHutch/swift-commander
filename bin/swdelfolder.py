#! /usr/bin/env python3

# Script to mass delete swift objects in a pseudo folder
#
# swdelfolder.py dirkpetersen / Jul 2015 
#

import swiftclient, sys, os, math, argparse

class KeyboardInterruptError(Exception): pass

def main():

    if not args.prefix:
        print('no prefix / pseudo folder entered - aborting')
        return False
    
    if args.container:

        prefix=args.prefix
        if prefix and not prefix.endswith('/'):
            prefix=args.prefix+'/'
        
        c=create_sw_conn()
        print ("    checking swift folder %s/%s ..." % (args.container,prefix))
        headers, objects = c.get_container(args.container,prefix=prefix,full_listing=True)
        c.close()
        if objects:
            easy_par(delobj,objects)
        else:
            print("    no objects found !")
    else:
        print('no container entered - aborting')
        return False

#        sbytes=0
#        for obj in objects:
#            print("    deleting %s ... " % obj['name'])
#            sbytes+=obj['bytes']
#            c.delete_object(args.container,obj['name'])
#            #print(obj['name'],obj['bytes'])
#        if sbytes > 0:
#            print ("    deleted %s bytes (%s) in %s/%s" % (intwithcommas(sbytes),convertByteSize(sbytes),args.container,args.prefix))
#        else:
#            print ("    ...Error: it seems swift folder %s/%s does not exist" % (args.container,args.prefix))

def delobj(obj):
    print("    deleting %s ... " % obj['name'])
    c=create_sw_conn()
    c.delete_object(args.container,obj['name'])

def easy_par(f, sequence):
    try:
        # I didn't see gains with .dummy; you might
        from multiprocessing import Pool
        pool = Pool(processes=32)

        # f is given sequence. guaranteed to be in order
        result = pool.map(f, sequence)
        cleaned = [x for x in result if not x is None]
        #cleaned = asarray(cleaned)
        # not optimal but safe
    except KeyboardInterrupt:
        pool.terminate()
    except Exception as e:
        pool.terminate()
    finally:
        pool.close()
        pool.join()
        return cleaned

def create_sw_conn():
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
    parser = argparse.ArgumentParser(prog='swdelfolder.py',
        description='delete a pseudo folder in swift with ' + \
        'potentially many objects ' + \
        '()')
    parser.add_argument( '--container', '-c', dest='container',
        action='store',
        help='a container in the swift object store',
        default='' )
    parser.add_argument( '--prefix', '-p', dest='prefix',
        action='store',
        help='a swift object prefix',
        default=None)
    parser.add_argument( '--maxproc', '-m', dest='maxproc',
        action='store',
        type=int,
        help='maximum number of processes to run (not yet implemented)',
        default=0 )
    args = parser.parse_args()
    return args

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    sys.exit(main())

