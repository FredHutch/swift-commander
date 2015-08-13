#!/usr/bin/env python3

# get multisegment swift files in parallel

import sys,os,getopt,json

import multiprocessing

import swiftclient

def create_sparse_file(filename,length):
   print("creating sparse file",filename)
   with open(filename, "wb") as f:
      f.truncate(length)

swift_auth=os.environ.get("ST_AUTH")

def create_sw_conn(auth_token="",storage_url=""):
   global swift_auth

   if auth_token and storage_url:
      return swiftclient.Connection(preauthtoken=auth_token,
         preauthurl=storage_url)

   swift_user=os.environ.get("ST_USER")
   swift_key=os.environ.get("ST_KEY")

   if swift_auth and swift_user and swift_key:
      return swiftclient.Connection(authurl=swift_auth,user=swift_user,
         key=swift_key)

   print("Error: Swift environment not configured!")

def parseSwiftUrl(path):
    path = path.lstrip('/')
    components = path.split('/');
    container = components[0];
    obj = '/'.join(components[1:])
    return container, obj

# conn, container, object, offset, dest
def assemble_ms_object(x):
   print("assembling",x) 
   headers,body=x[0].get_object(x[1],x[2])
   print("body len=",len(body))
   with open(x[4],"r+b") as f_out:
      if x[3]>0:
         f_out.seek(x[3])
      f_out.write(bytes(body))

def get_ms_object(sc,container,object,pool_size):
   print("multisegment object",object)
   segments=[]
   segment_total=0

   # build segment map for parallel download
   headers,body=sc.get_object(container,object,
      query_string='multipart-manifest=get')
   manifest=json.loads(body.decode())
   for segment in manifest:
      segment_container,segment_obj=parseSwiftUrl(segment['name'])
      # store segment container, object and offset
      segments.append([sc,segment_container,segment_obj,segment_total,object])
      segment_total=segment_total+segment['bytes']

   # create sparse file
   create_sparse_file(object,segment_total)

   # sequential assembly
   #for seg in segments:
   #   assemble_ms_object(seg)

   # parallel assembly
   print("parallel assembly with",pool_size,"workers")
   p=multiprocessing.Pool(pool_size)
   p.map(assemble_ms_object,segments)

def get_object(conn,container,object):
   headers,body=conn.get_object(container,object)
   with open(object,"w+b") as f_out:
      f_out.write(bytes(body))

def get_objects(sc,container,object_list,pool_size):
   print("getting",object_list,"from container",container)

   try:
      headers,objs=sc.get_container(container)
      for obj in objs:
         if obj['name'] in object_list:
            print("found",obj['name'])
            try:
               headers=sc.head_object(container, obj['name'])
            except:
               headers=[]
            if 'x-static-large-object' in headers:
               get_ms_object(sc,container,obj['name'],pool_size)
            else:
               get_object(sc,container,obj['name'])

   except swiftclient.ClientException:
      print("Error: cannot access Swift container '%s'!" % container)

   sc.close()

def validate_dir(path,param):
   if not os.path.isdir(path):
      print("Error: %s '%s' is not accessible!" % (param,path))
      sys.exit()

   if path[-1]=='/':
      path=path[:-1] 

   return(path)

def usage():
   print("spget [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")
   print("\t-p pool_size (default 5)")
   print("\t-a auth_token")
   print("\t-s storage_url")

def main(argv):
   container=""
   pool_size=5
   auth_token=""
   storage_url=""

   try:
      opts,args=getopt.getopt(argv,"l:c:p:a:s:h")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         container=""
         break
      elif opt in ("-l"): # override default local directory
         local_dir=validate_dir(arg,"local")
      elif opt in ("-c"): # set container
         container=arg
      elif opt in ("-p"): # parallel workers
         pool_size=int(arg)
      elif opt in ("-a"): # auth token
         auth_token=arg
      elif opt in ("-s"): # storage URL
         storage_url=arg

   if not container or not args:
      usage()
   else:
      sc=create_sw_conn(auth_token,storage_url)
      if sc:
         get_objects(sc,container,args,pool_size)

if __name__ == '__main__':
   main(sys.argv[1:])
