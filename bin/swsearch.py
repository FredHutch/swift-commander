#! /usr/bin/env python3

# Script for searching content in a list of objects (grep)
#

import swiftclient, sys, os, math, argparse, json

class KeyboardInterruptError(Exception): pass

def main():
    
    if args.container:

        c=create_sw_conn()

        storageurl=os.environ.get("OS_STORAGE_URL")
        if not storageurl:
            storageurl, authtoken = c.get_auth()
        
        swaccount=storageurl.split("/")[-1]

        print ("    checking swift folder /%s/%s ..." % (args.container,prefix))
        try:
            headers, objects = c.get_container(args.container,prefix=args.prefix,full_listing=True)
            c.close()
        except swiftclient.client.ClientException as ex:
            httperr=getattr(ex, 'http_status', None)
            if httperr == 404:
                print("    no objects found - error 404")
            else:
                print("    HTTP Error %s" % httperr)
            return False

        sbytes=0
        print("    checking size of /%s/%s ... " % (args.container,prefix))
        for obj in objects:
            easy_par(searchobj,objects)
    else:
        print('no container entered - aborting')
        return False


def searchobj(obj):
    print("    Searching /%s/%s ... " % (args.container,obj['name']))
    retcode=200
    c=create_sw_conn()
    try:
        headers = c.head_object(args.container, obj['name'])
    except:
        headers = []
    if 'x-static-large-object' in headers:
        #print(headers['x-static-large-object'])
        headers, body = c.get_object(args.container, obj['name'], query_string='multipart-manifest=get')
        manifest = json.loads(body.decode())
        for segment in manifest:
            print ("        searching segment %s" % segment['name'])
            segment_container, segment_object = parseSwiftUrl(segment['name'])
            try:
            	#c.search_the_object(................)
            except Exception as e:
                retcode=e.http_status
                print('Error %s deleting object segment %s: %r' % (e.http_status,obj['name'],e))
    else:
        #c.search_the_object(......)
    c.close()
    return retcode

def parseSwiftUrl(path):
    path = path.lstrip('/')
    components = path.split('/');
    container = components[0];
    obj = '/'.join(components[1:])
    return container, obj
    
def easy_par(f, sequence):    
    from multiprocessing import Pool
    pool = Pool(processes=args.maxproc)
    try:
        # f is given sequence. guaranteed to be in order
        cleaned=False
        result = pool.map(f, sequence)
        cleaned = [x for x in result if not x is None]
        #cleaned = asarray(cleaned)
        # not optimal but safe
    except KeyboardInterrupt:
        pool.terminate()
    except Exception as e:
        print('got exception: %r' % (e,))
        if not args.force:
            print("Terminating the pool")
            pool.terminate()
    finally:
        pool.close()
        pool.join()
        return cleaned

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


def parse_arguments():
    """
    Gather command-line arguments.
    """
    parser = argparse.ArgumentParser(prog='swsearch.py',
        description='Search objects for text ' + \
        ' in potentially many objects ' + \
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
        help='maximum number of processes to run',
        default=32 )
    parser.add_argument( '--authtoken', '-a', dest='authtoken',
        action='store',
        help='a swift authentication token (required when storage-url is used)',
        default=None)    
    parser.add_argument( '--storage-url', '-s', dest='storageurl',
        action='store',
        help='a swift storage url (required when authtoken is used)',
        default=None)
    parser.add_argument( '--find', '-f', dest='findstring',
        action='store',
        help='a search stringurl',
        default=None)

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    sys.exit(main())
